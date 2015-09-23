#!/usr/bin/env python
from operator import mul
import cv2
import numpy as np
import colorific
import sys
import json
try:
    import Image
except ImportError:
    from PIL import Image
import pytesseract

def split_array(seq, num):
    avg = len(seq) / float(num)
    out = []
    last = 0.0

    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg

    return out

def get_total_face_coords(faces):
    tl = [99999999,99999999]
    br = [0, 0]
    for (x,y,w,h) in faces:
        tl = [min(tl[0],x),min(tl[1],y)]
        br = [max(br[0],x+w),max(br[1],y+h)]
    
    coords = [tl, br]
    return coords

def find_faces(gray, img):
    # Face
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    return faces
    
def find_smiles(gray, img):
    # Smile
    smile_cascade = cv2.CascadeClassifier('haarcascade_mouth.xml')
    smiles = smile_cascade.detectMultiScale(gray, 1.3, 5)
    
    return smiles
    

# ---------------------
# STEPS
# ---------------------
# Find Faces and return back a container of 
# the most area that doesn't overlap the faces
def step1(gray, multiplerScale, img):
    
    faces = find_faces(gray, img)
    
    if len(faces) > 0:
        
        totalAreaCoords = get_total_face_coords(faces)
        biggestAreaCords = []
        biggestArea = 0
        imageHeight, imageWidth = img.shape[:2]
        #North
        north = (imageWidth*(totalAreaCoords[0][1]))
        if north > biggestArea:
            biggestArea = north
            biggestAreaCords = {"direction":"north","x":0,"y":0,"areaWidth":int(imageWidth*multiplerScale), "areaHeight":int(totalAreaCoords[0][1]*multiplerScale)}
        #East
        east = (imageHeight*(imageWidth-totalAreaCoords[1][0]))
        if east > biggestArea:
            biggestArea = east
            biggestAreaCords = {"direction":"east","x":int(totalAreaCoords[1][0]*multiplerScale), "y":0,"areaWidth":int((imageWidth-totalAreaCoords[1][0])*multiplerScale), "areaHeight":int(imageHeight*multiplerScale)}

        #South
        south = (imageWidth*(imageHeight-totalAreaCoords[1][1]))
        if south > biggestArea:
            biggestArea = south
            biggestAreaCords = {"direction":"south","x":0,"y":int(totalAreaCoords[1][1]*multiplerScale),"areaWidth":int(imageWidth*multiplerScale), "areaHeight":int((imageHeight-totalAreaCoords[1][1])*multiplerScale)}

        #West
        west = (imageHeight*(totalAreaCoords[0][0]))
        if west > biggestArea:
            biggestArea = west
            biggestAreaCords = {"direction":"west","x":0,"y":0,"areaWidth":int(totalAreaCoords[0][0]*multiplerScale), "areaHeight":int(imageHeight*multiplerScale)}

        # DEBUG: Draw retangles of detected faces on the image.
        #cv2.rectangle(img,(totalAreaCoords[0][0],totalAreaCoords[0][1]),(totalAreaCoords[0][0]+totalAreaCoords[1][0],totalAreaCoords[0][1]+totalAreaCoords[1][1]),(0,0,255),2)

        return biggestAreaCords
    else:
        return False

def step2(binaryGray, multiplerScale):

    # Turn image into an array of 1/0 for processing
    imageArrayProcess = np.array(binaryGray)

    # Work out if the image is more dark or light
    # Also work out the darkest row
    totalBytes = 0
    totalLightness = 0
    darkestRowLoopCount = 0
    darkestRow = 0
    darkestRowBytes = 9999999999 #set really high!
    for row in imageArrayProcess:
        totalLightness = totalLightness + sum(row)
        totalBytes = totalBytes + len(row)
        if sum(row) < darkestRowBytes:
            darkestRowBytes = sum(row)
            darkestRow = darkestRowLoopCount
        darkestRowLoopCount = darkestRowLoopCount + 1

    return {"totalLightness": int(totalLightness * multiplerScale), "totalBytes": int(totalBytes * multiplerScale),"darkestRow": int(darkestRow * multiplerScale), "darkestRowBytes": int(darkestRowBytes * multiplerScale)}

def step4(thresholdGray):
    # Find Harris corners. We use this to work
    # out where the detail in the images are.
    binaryGray = np.float32(thresholdGray)
    dst = cv2.cornerHarris(binaryGray,2,3,0.2)

    # Result is dilated for marking the corners, not important
    dst = cv2.dilate(dst,None)

    # Work out the busiest quadrant, rule of thirds
    tl = 0
    tc = 0
    tr = 0
    ml = 0
    mc = 0
    mr = 0
    bl = 0
    bc = 0
    br = 0
    rowLength = 0
    numberOfRows = len(dst)
    quadrantCount = 0
    busiestQuadrant = 0
    for row in dst>0.1*dst.max():
        rowLength = len(row)
        quads = split_array(row, 3)
        aQuad = sum(quads[0])
        bQuad = sum(quads[1])
        cQuad = sum(quads[2])
        if quadrantCount < numberOfRows/3:
            tl = tl + aQuad
            tc = tc + bQuad
            tr = tr + cQuad
        elif quadrantCount < numberOfRows/3*2:
            ml = ml + aQuad
            mc = mc + bQuad
            mr = mr + cQuad
        else:
            bl = bl + aQuad
            bc = bc + bQuad
            br = br + cQuad
        quadrantCount = quadrantCount + 1    
    quadrantResults = {tl:'tl', tc:'tc', tr:'tr', ml:'ml', mc:'mc', mr:'mr', bl:'bl', bc:'bc', br:'br'}
    busiestQuadrant = max(tl, tc, tr, ml, mc, mr, bl, bc, br)
    quietestQuadrant = min(tl, tc, tr, ml, mc, mr, bl, bc, br)

    return {"detailInQuadrant": quadrantResults,"busiestQuadrant": busiestQuadrant, "quietestQuadrant":quietestQuadrant}

def step5(fileName):
    palette = colorific.palette.extract_colors(fileName, min_prominence=0.1)
    
    return palette

# Find Smiles
def step6(gray, img):
    
    smiles = find_smiles(gray, img)
    
    if len(smiles) > 0:
        return True
    elif len(smiles) == 0:
        return False

def step7(fileName):
    result = detectText(fileName)
    if len(result) > 0:
        return result
    else:
        return False

def detectText(fileName):

    ocrResult = pytesseract.image_to_string(Image.open(fileName), lang=None, boxes=None, config='-psm=7')

    return ocrResult

def suggestFaceTextCSS(step1Results):

    if step1Results['direction'] == 'west':
        css = {'text-align':'left','right':'auto','left':'0','top':'0','bottom':'0','maxWidth':str(step1Results['areaWidth']) + 'px'}
    elif step1Results['direction'] == 'north':
        css = {'text-align':'center','top':'auto','left':'0','top':'0','right':'0','maxHeight':str(step1Results['areaHeight']) + 'px'}
    elif step1Results['direction'] == 'east':
        css = {'text-align':'right','left':'auto','bottom':'0','top':'0','right':'0','maxWidth':str(step1Results['areaWidth']) + 'px'}
    elif step1Results['direction'] == 'south':
        css = {'text-align':'center','top':'auto','left':'0','bottom':'0','right':'0','maxHeight':str(step1Results['areaHeight']) + 'px'}

    return css

def suggestQuadrantCSS(quietestQuadrant):
    if quietestQuadrant == 'tl':
        css = {'text-align':'left','bottom':'auto','right':'auto','left':'0','top':'0','maxWidth':'66%','maxHeight':'66%'}
    elif quietestQuadrant == 'tc':
        css = {'text-align':'center','bottom':'auto','left':'16.5%','top':'0','right':'16.5%','maxHeight':'66%'}
    elif quietestQuadrant == 'tr':
        css = {'text-align':'right','bottom':'auto','left':'auto','right':'0','top':'0','maxWidth':'66%','maxHeight':'66%'}
    elif quietestQuadrant == 'ml':
        css = {'text-align':'left','right':'auto','left':'0','top':'33%','bottom':'33%','maxWidth':'66%'}
    elif quietestQuadrant == 'mc':
        css = {'text-align':'center','width':'100%','height':'100%','display':'flex','align-items':'center','justify-content': 'center', 'top':'0', 'bottom':'0', 'right':'0', 'left':'0'}
    elif quietestQuadrant == 'mr':
        css = {'text-align':'right','left':'auto','right':'0','top':'33%','bottom':'33%','maxWidth':'66%'}
    elif quietestQuadrant == 'bl':
        css = {'text-align':'left','top':'auto','right':'auto','left':'0','bottom':'0','maxWidth':'66%','maxHeight':'66%'}
    elif quietestQuadrant == 'bc':
        css = {'text-align':'center','top':'auto','left':'16.5%','bottom':'0','right':'16.5%','maxWidth':'66%'}
    elif quietestQuadrant == 'br':
        css = {'text-align':'right','top':'auto','left':'auto','right':'0','bottom':'0','maxWidth':'66%','maxHeight':'66%'}

    return css

# ---------------------
# EXECUTION
# ---------------------

fileName = sys.argv[1]

# Read file
img = cv2.imread(fileName)

# inital scale ratio
imageHeight, imageWidth = img.shape[:2]
if imageWidth > 1000 and imageWidth < 2000:
    multiplerScale = 2
    img = cv2.resize(img, (0,0), fx=0.5, fy=0.5) 
elif imageWidth > 2000:
    multiplerScale = 4
    img = cv2.resize(img, (0,0), fx=0.25, fy=0.25) 
else: 
    multiplerScale = 1

# Blur image
blurred = cv2.medianBlur(img, 5)
delta = 127. * -255 / 100
a = 255. / (255. - delta * 2)
b = a * (-100 - delta)

# Increase contrast
contrast = cv2.convertScaleAbs(img, blurred, a, b)

# Gray scale the image
gray = cv2.cvtColor(contrast,cv2.COLOR_BGR2GRAY)

# Turn the image into an array
ret,thresholdGray = cv2.threshold(gray,127,255,cv2.THRESH_BINARY | cv2.THRESH_OTSU)

# Turn thresholdGray into 1's and 0's array representation
ret,binaryGray = cv2.threshold(thresholdGray,0,1,cv2.THRESH_BINARY | cv2.THRESH_OTSU)

# Step 1 -  Find faces, if any!
step1Results = step1(gray, multiplerScale, img)

# Step 2 -  Get lightness info about image
step2Results = step2(binaryGray, multiplerScale)

# Step 3 (no function) - Inverse Image if more dark than light
# Flip the image if more light than dark
if (step2Results["totalBytes"] / 2) < step2Results["totalLightness"]:
    thresholdGray = abs(255-thresholdGray)
    binaryGray = abs(255-thresholdGray)
# Step 3 End

# Step 4 - Work out the busiest parts of the image
step4Results = step4(binaryGray)

# Step 5 - Get color palette of the image
step5Results = step5(fileName)

# Step 6 - Get mood
step6Result = step6(gray, img)

# Step 7 - Detect text!
step7Result = step7(fileName)

avoidFacesCSS = False
# If there are faces
if step1Results != False:
   avoidFacesCSS = suggestFaceTextCSS(step1Results)

quietestQuadrantCSS = suggestQuadrantCSS(step4Results['detailInQuadrant'][step4Results['quietestQuadrant']])

css = {'avoidFaces':avoidFacesCSS, 'quietestQuadrant':quietestQuadrantCSS}

# Don't include step 3 as it just flips the binarys based on lightness results
finalResults = json.dumps({"width":imageWidth, "height":imageHeight, "css":css,"faces":step1Results,"smiles":step6Result,"lightness":step2Results,"detail":step4Results,"palette":step5Results,"text":step7Result}) 

print finalResults

# DEBUG - If image has changed, write to it to show results
# cv2.imwrite( "result.jpg", img)
