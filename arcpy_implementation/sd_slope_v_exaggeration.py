"""
Tool:               sdSlopeVExagg
Source Name:        sd_slope_v_exaggeration.py
Version:            ArGIS Pro 2.8
Author:             Jack Gonzales
Usage:              
Required Arguments: Input DEM layer
                    Output file path
                    Exaggeration factor
                    Q factor
                    Neighborhood
                    Roughness blur window
Description:        A tool for applying vertical exaggeration based on terrain 
                    roughness. Smooth areas will be exaggerated more than 
                    rough areas.
"""
import arcpy
from scipy import ndimage
import numpy as np

def slope_stdev(dem, neighborhood=15):
    # DEM is a 2D array of elevation values, neighborhood indicates the size of 
    # the square neighborhood for slope variance calculations 
    # i.e. neighborhood = 3 means a 3x3 neighborhood
    gradX, gradY = np.gradient(dem)
    slope = np.sqrt(gradX ** 2 + gradY ** 2)
#    slopeMean = ndimage.uniform_filter(slope,size=15)
#    slopeSqrMean = ndimage.uniform_filter(slope**2,size=neighborhood)
#    slopeVar = slopeSqrMean - slopeMean**2
#    slopeStdev = np.sqrt(np.absolute(slopeVar)) 
    # Unfortunately, the original sd slope implementation seems not to work
    # in Arc, while it works perfectly outside of Arc. The mean of squares and 
    # squared mean turn out to be (incorrectly) identical, resulting in zero 
    # variance. To get around this, we can use the generic_filter instead, 
    # which produces the correct result, albeit slower.
    hood = (neighborhood,neighborhood)
    slopeStdev = ndimage.generic_filter(slope, 
                                        np.std, 
                                        size=hood, 
                                        mode='reflect')
    # In perfectly flat areas where variance is ideally zero, float precision 
    # can result in a number slightly below zero. Using the absolute value of 
    # variance prevents nonreal results
    return slopeStdev

def dynamicExaggeration_sdSlope(dem, 
                                exaggFactor, 
                                neighborhood=15, 
                                q=6, 
                                blur=30):
    """
    scalingFactor = how much you want the modified terrain to be exaggerated 
    (e.g. 2x,3x, etc.).
    neighborhood = neighborhood used to calculate sd slope
    blur = neighborhood that blurs the sd slope image to mitigate noise
    q = The weight given to sd slope roughness in generating the modified DEM    
    """
   
    #------------Generate roughness image------------
    roughness = slope_stdev(dem,neighborhood) 
    roughnessFiltered = ndimage.uniform_filter(roughness,blur)
    
    # Calculate z-score of roughness, then use tanh to recast z-scores from 2-3
    # and invert, so that low values indicate rough areas
    roughnessZ = ((roughnessFiltered - np.mean(roughnessFiltered))) /\
                 np.std(roughnessFiltered)
    # The 2 added at the end moves the tanh from 0-1 to 2-3, which I found to 
    # work OK. It's worth experimenting with the exaggeration range and stretch
    roughnessZTanh = (np.tanh(roughnessZ) - 1) * (-1) + 2 
    
    #-------------------Exaggerate-------------------
    elevExagg = ((dem * 1) * (roughnessZTanh))
    # In certain situations, smooth mountain peaks surrounded by rough areas 
    # can get squashed. A larger q value will reduce the impact of the dynamic
    # par of the exaggeration. The exaggFactor factor is used similarly to 
    # standard uniform vertical exaggeration.
    elevExagg = (dem + ((elevExagg - dem) / q)) * exaggFactor 
    return elevExagg

def ScriptTool(DEM_layer, 
               Output_destination, 
               Exaggeration_factor, 
               Neighborhood=15, 
               q=6, 
               blur=30):
    #-----------------Load input DEM-----------------
    DEM_layer = arcpy.Raster(DEM_layer)
    dem = arcpy.RasterToNumPyArray(DEM_layer)
    
    #-----------Copy spatial reference info----------
    lowerLeft = arcpy.Point(DEM_layer.extent.XMin,DEM_layer.extent.YMin)
    cellWidth = DEM_layer.meanCellWidth
    cellHeight = DEM_layer.meanCellHeight
    desc = arcpy.Describe(DEM_layer)
    sr = desc.spatialReference
    
    #-------------------Exaggerate-------------------
    exaggerated_elevation = dynamicExaggeration_sdSlope(dem, 
                                                        Exaggeration_factor, 
                                                        Neighborhood, 
                                                        q, 
                                                        blur)
    
    #-----------Create and save new image------------
    newRaster = arcpy.NumPyArrayToRaster(exaggerated_elevation, 
                                         lowerLeft, 
                                         cellWidth, 
                                         cellHeight)
    arcpy.DefineProjection_management(newRaster, sr)
    newRaster.save(Output_destination)
    
    #--------------Add new image to map--------------
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    aprxMap = aprx.activeMap
    aprxMap.addDataFromPath(Output_destination)
    return



if __name__ == '__main__':
    # ScriptTool parameters
    DEM_layer = arcpy.GetParameterAsText(0)
    Output_destination = arcpy.GetParameterAsText(1)
    Exaggeration_factor = arcpy.GetParameter(2)
    q = arcpy.GetParameter(3)
    Neighborhood = arcpy.GetParameter(4)
    blur = arcpy.GetParameter(5)
    
    ScriptTool(DEM_layer, 
               Output_destination, 
               Exaggeration_factor, 
               Neighborhood, q)