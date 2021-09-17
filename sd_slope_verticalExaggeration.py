"""
Tool:               sd slope vertical exaggeration
Source Name:        
Version:            ArcGIS Pro 2.8
Author:             Jack Gonzales
Usage:              <Command syntax>
Required Arguments: Input DEM
                    output destination
                    exaggeration factor
Optional Arguments: Neighborhood size
                    q factor
Description:        Vertically exaggerates a DEM based on roughness derived
                    from sd slope. The idea is to exaggerate smooth areas more 
                    than rough areas
                    https://github.com/jackjgo/dynamic_exaggeration
"""
import arcpy
import numpy as np
from scipy import ndimage


def slope_stdev(dem, neighborhood):
    # DEM is a 2D array of elevation values, neighborhood indicates the size of 
    # the square neighborhood surrounding each pixelfor slope variance calculations 

    gradX, gradY = np.gradient(dem)
    slope = np.sqrt(gradX ** 2 + gradY ** 2)
    slopeMean = ndimage.uniform_filter(slope,neighborhood)
    slopeSqrMean = ndimage.uniform_filter(slope**2,neighborhood)
    slopeVar = slopeSqrMean - slopeMean**2
    slopeStdev = np.sqrt(np.absolute(slopeVar)) #I n perfectly flat areas where
    # variance is ideally zero, float precision can result in a number slightly
    # below zero. Using the absolute value of variance prevents nonreal results
    return slopeStdev



def dynamicExaggeration_sdSlope(dem, exaggFactor, neighborhood, q, blur):
    """
    scalingFactor = how much you want the modified terrain to be exaggerated 
    (e.g. 2x,3x, etc.).
    neighborhood = neighborhood used to calculate sd slope
    blur = neighborhood that blurs the sd slope image to mitigate noise
    q = The weight given to sd slope roughness in generating the modified DEM    
    """
   
    #------------Generate roughness image------------
    roughness = slope_stdev(dem,neighborhood) # Change the second parameter to adjust neighborhood used for sdSlope
    roughnessFiltered = ndimage.uniform_filter(roughness,blur)
    
    # Calculate z-score of roughness, then use tanh to recast z-scores from 2-3
    # and invert, so that low values indicate rough areas
    roughnessZ = ((roughnessFiltered - np.mean(roughnessFiltered))) / np.std(roughnessFiltered)
    roughnessZTanh = (np.tanh(roughnessZ) - 1) * (-1) + 2 # The 2 added at the end moves the tanh from 0-1 to 2-3, which I found to work OK. It's worth experimenting with the exaggeration range and stretch
    # It's also worth expirmenting with functions other than tanh
    
    #-------------------Exaggerate-------------------
    elevExagg = ((dem * 1) * (roughnessZTanh))
    q = 6
    elevExagg = (dem + ((elevExagg - dem) / q)) * exaggFactor # In certain
    # situations, smooth mountain peaks surrounded by rough areas can get squashed.
    # A larger q value will reduce the impact of the dynamic par of the exaggeration
    # The scaling factor is used similarly to standard exaggeration

    return elevExagg

def ScriptTool(DEM_layer, Output_destination, Exaggeration_factor, Neighborhood=15, q = 6, blur = 30):
    #-----------------Load input DEM-----------------
    DEM_layer = arcpy.Raster(DEM_layer)
    dem = arcpy.RasterToNumPyArray(DEM_layer)
    # mark lower left corner and cell size
    lowerLeft = arcpy.Point(DEM_layer.extent.XMin,DEM_layer.extent.YMin)
    cellSize = DEM_layer.meanCellWidth
    
    #-------------------Exaggerate-------------------
    exaggerated_elevation = dynamicExaggeration_sdSlope(dem, Exaggeration_factor, Neighborhood, q, blur)
    
    #-----------Create and save new image------------
    newRaster = arcpy.NumPyArrayToRaster(exaggerated_elevation, lowerLeft, cellSize)
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
    
    print(Exaggeration_factor)
    
    ScriptTool(DEM_layer, Output_destination, Exaggeration_factor, Neighborhood, q)
    #ScriptTool('./srtm_15_04.tif', './out.tif', 2, 15, 6)

