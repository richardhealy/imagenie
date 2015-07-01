<?php 
class Imagenie
{
    private $imagePosition = '';
    private $layoutScheme = '';
    private $imageContrast = 'ig-unknown';
    private $textFillPercent = 100;
    private $themePalette = array();
    private $mood = 'ig-unknown';
    private $generatedCss = '';

    public function run($pythonLocation, $imagenieLocation, $filePath) {

        $command = escapeshellcmd($pythonLocation.' '.$imagenieLocation.' '.$filePath);
        $imagenieJsonString = shell_exec($command);

        // Image Data
        if (strlen($imagenieJsonString) > 0) {
            $imagenieOutput = json_decode($imagenieJsonString);
        } else {
            $imagenieOutput = false;
        }

        return $imagenieOutput;
    }

    public function generateDesignData($imagenieData) {

        if (gettype($imagenieData) !== 'object') {
            return false;
        }

        $this->generatePalette($imagenieData);
        $this->generateContrast($imagenieData);
        $this->generateMood($imagenieData);
        $this->generateLayout($imagenieData);
    }

    private function generateLayout($imagenieData) {
        if (gettype($imagenieData) !== 'object') {
            return false;
        }

        if (    $imagenieData->css && 
                $imagenieData->css->avoidFaces && 
                $imagenieData->css->avoidFaces !== false
            ) {

            // Quietst Quadrant
            $this->layoutScheme = 'ig-avoid-faces';
            $this->imagePosition = 'ig-' . $imagenieData->faces->direction;


            $attribute = 'max-width';
            $this->textFillPercent = 100;

            if (isset($imagenieData->css->avoidFaces->maxWidth) && intval($imagenieData->css->avoidFaces->maxWidth) > 0) {
                $this->textFillPercent = max(intval((100 / intval($imagenieData->width)) * intval($imagenieData->css->avoidFaces->maxWidth)), 33);
                $attribute = 'max-width';
            } elseif (isset($imagenieData->css->avoidFaces->maxHeight) && intval($imagenieData->css->avoidFaces->maxHeight) > 0) {
                $this->textFillPercent = max(intval((100 / intval($imagenieData->height)) * intval($imagenieData->css->avoidFaces->maxHeight)), 33);
                $attribute = 'max-height';
            }

            $this->generatedCss = '.ig-avoid-faces .ig-overlay {'.PHP_EOL;
            $this->generatedCss .= $attribute.':'.$this->textFillPercent.'%;'.PHP_EOL;
            $this->generatedCss .= '}'.PHP_EOL;

        } else {

            // Quietst Quadrant
            $this->layoutScheme = 'ig-quietest-quadrant';
            $quietestQuadrantKey = $imagenieData->detail->quietestQuadrant;
            $this->imagePosition = 'ig-qq-'.$imagenieData->detail->detailInQuadrant->$quietestQuadrantKey;

            // Clears down css
            $this->generatedCss = '';
        }
    }

    private function generateContrast($imagenieData) {

        $this->imageContrast = 'ig-unknown';

        // If the image light, contrasting or dark
        if ($imagenieData !== null && 
            $imagenieData->lightness && 
            $imagenieData->lightness->totalLightness && 
            $imagenieData->lightness->totalBytes
        ) {
            // Lightness scale between 1 and $imagenieData->lightness->totalBytes (inclusive).
            // The nearer to 1, the lighter the image.
            $scale = floatval($imagenieData->lightness->totalBytes / $imagenieData->lightness->totalLightness);

            // 1 >= 1.5 = light image
            if ($scale > 1 && $scale <= 1.5) {
                $this->imageContrast = 'ig-light';
            // 1.5 >= 2.5 = contrasting image
            } elseif ($scale > 1.5 && $scale <= 2.5) {
                $this->imageContrast = 'ig-contrasting';
            // 2.5 > totalBtyes = dark image
            } elseif ($scale > 2.5 && $scale <= 1.5) {
                $this->imageContrast = 'ig-dark';
            }
        }
    }

    private function generateMood($imagenieData) {
        
        $temperature = 0;
        $this->mood = 'ig-unknown';

        if(!empty($imagenieData)) {
            foreach ($imagenieData->palette[0] as $rgb) {
                $red = $rgb[0][0];
                $blue = $rgb[0][2];

                if ($blue < $red) { 
                    $temperature += 10;
                } else {
                    $temperature -= 10;
                }
            }

            // warm 
            if ($temperature > 0) {
                if ($imagenieData->faces !== false && $imagenieData->smiles === true) {
                    $this->mood = 'ig-happy-warm';
                } elseif ($imagenieData->faces !== false && $imagenieData->smiles === false) {
                    $this->mood = 'ig-serious-warm';
                } elseif ($imagenieData->faces === false) {
                    $this->mood = 'ig-warm';
                }
            // cold
            } elseif ($temperature <= 0) {
                if ($imagenieData->faces !== false && $imagenieData->smiles === true) {
                    $this->mood = 'ig-happy-cold';
                } elseif ($imagenieData->faces !== false && $imagenieData->smiles === false) {
                    $this->mood = 'ig-serious-cold';
                } elseif ($imagenieData->faces === false) {
                    $this->mood = 'ig-cold';
                }
            }
        }
    }

    private function generatePalette($imagenieData) {

        $this->themePalette = array();
        $count = 0;

        if(!empty($imagenieData)) {
            foreach ($imagenieData->palette[0] as $rgb) {
                $count = $count + 1;

                if ($count == 1) {
                    $this->themePalette['primaryColor'] = $this->rgb2hex($rgb[0]);
                }

                if ($count == 2) {
                    $this->themePalette['secondaryColor'] = $this->rgb2hex($rgb[0]);
                }

                $this->themePalette['color'.$count] = $this->rgb2hex($rgb[0]);
            }
        }
    }

    private function rgb2hex($rgb) {
        $hex = "#";
        $hex .= str_pad(dechex($rgb[0]), 2, "0", STR_PAD_LEFT);
        $hex .= str_pad(dechex($rgb[1]), 2, "0", STR_PAD_LEFT);
        $hex .= str_pad(dechex($rgb[2]), 2, "0", STR_PAD_LEFT);

        return $hex;
    }

    public function toArray() {
        return array(
            "imagePosition"     => $this->imagePosition,
            "imageContrast"     => $this->imageContrast,
            "layoutScheme"      => $this->layoutScheme,
            "textFillPercent"   => $this->textFillPercent,
            "themePalette"      => $this->themePalette,
            "mood"              => $this->mood,
            "generatedCss"      => $this->generatedCss,
        );
    }
}