<?php

include "Imagenie.php";

$imagenie = new Imagenie();
$imagenieData = $imagenie->run('python', 'imagenie.py', 'charlie.jpg');
$imagenie->generateDesignData($imagenieData);
$returnValues = $imagenie->toArray();

print_r($returnValues);