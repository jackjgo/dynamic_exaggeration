# -*- coding: utf-8 -*-
"""
Dynamic vertical exaggeration, based on standard deviation of slope
The idea is to ex aggerate smooth areas (e.g. plains) more than rough areas
(e.g. mountains). This allows both high and low relief features to be shown
well in the same 3D map, rather than one being exaggerated too much and the
other too little.

v1.0
"""

from sd_slope import sd_slope
import rasterio as rs
import numpy as np
from scipy import ndimage
import os

def dynamicExaggeration_sdSlope(inputPath, outputPath, scalingFactor = 2, neighborhood = 15, q = 6):
    """
    scalingFactor = how much you want the modified terrain to be exaggerated 
    (e.g. 2x,3x, etc.).
    neighborhood = neighborhood that blurs sdSlope roughness to mitigate noise
    q = The weight given to sd slope roughness in generating the modified DEM    
    """
    # load file
    dataset = rs.open(inputPath)
    band1 = dataset.read(1)
    kwds = dataset.profile
    
    # Generate roughness image
    sd_slope(inputPath, './temp_roughness.tif',30) # Change the third parameter to adjust neighborhood used for sdSlope
    roughnessData = rs.open('./temp_roughness.tif')
    roughness = roughnessData.read(1)
    roughnessFiltered = ndimage.uniform_filter(roughness,neighborhood)
    
    # Calculate z-score of roughness, then use tanh to recast z-scores from 2-3
    # and invert, so that low values indicate rough areas
    roughnessZ = ((roughnessFiltered - np.mean(roughnessFiltered))) / np.std(roughnessFiltered)
    roughnessZTanh = (np.tanh(roughnessZ) - 1) * (-1) + 2 # The 2 added at the end moves the tanh from 0-1 to 2-3, which I found to work OK. It's worth experimenting with the exaggeration range and stretch
    # It's also worth expirmenting with functions other than tanh
    
    # Exaggerate
    scalingFactor = 2
    exaggeration = (roughnessZTanh )
    elevExagg = ((band1 * 1) * (exaggeration))
    q = 6
    elevExagg = (band1 + ((elevExagg - band1) / q)) * scalingFactor # In certain
    # situations, smooth mountain peaks surrounded by rough areas can get squashed.
    # A larger q value will reduce the impact of the dynamic par of the exaggeration
    # The scaling factor is used similarly to standard exaggeration

    # Remove roughness temp file
    del roughnessData
    os.remove('./temp_roughness.tif')
    # Output file
    kwds['dtype'] = elevExagg.dtype
    with rs.open(outputPath, 'w', **kwds) as dst:
        dst.write(elevExagg, indexes=1)

    return

dynamicExaggeration_sdSlope('./data/srtm_15_04.tif','./data/elevExagg.tif')