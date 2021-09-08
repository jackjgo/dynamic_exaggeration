"""
Calculates surface rougness based on slope standard deviation

Many rougness metrics are based on elevation differences. This could lead to a 
flat, sloped area being considered rough, while a surface with many small 
elevation changes (like very coarse sandpaper) woul be smooth. Is this really
what roughness means. Instead I'm interested in deriving roughness from
slope standard deviation

"""

import rasterio as rs
import numpy as np
from scipy import ndimage


def slope_stdev(dem, neighborhood=3):
    # DEM is a 2D array of elevation values, neighborhood indicates the size of 
    # the square neighborhood for slope variance calculations 
    # i.e. neighborhood = 3 means a 3x3 neighborhood
    gradX, gradY = np.gradient(dem)
    slope = np.sqrt(gradX ** 2 + gradY ** 2)
    slopeMean = ndimage.uniform_filter(slope,(neighborhood, neighborhood))
    slopeSqrMean = ndimage.uniform_filter(slope**2,(neighborhood,neighborhood))
    slopeVar = slopeSqrMean - slopeMean**2
    slopeStdev = np.sqrt(np.absolute(slopeVar)) #In perfectly flat areas where
    #variance is ideally zero, float precision can result in a number slightly
    #below zero. Using the absolute value of variance prevents nonreal results
    return slopeStdev

def slope_roughness(input_path, output_path, neighborhood=3, interpMethod='linear'):
    dataset = rs.open(input_path)
    band1 = dataset.read(1)
    kwds = dataset.profile
    slopeStdev = slope_stdev(band1,neighborhood)

    kwds['dtype'] = slopeStdev.dtype
    with rs.open(output_path, 'w', **kwds) as dst:
        dst.write(slopeStdev, indexes=1)
    return
    