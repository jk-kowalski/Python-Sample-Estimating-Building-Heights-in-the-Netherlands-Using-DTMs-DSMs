import numpy as np
from osgeo import gdal
gdal.UseExceptions()  # This silences the FutureWarning

from scipy.interpolate import griddata

# Function to read a raster file using GDAL
def read_raster(raster_path):
    ds = gdal.Open(raster_path)  # Open the raster file
    band = ds.GetRasterBand(1)  # Get the first band (assuming single band raster)
    array = band.ReadAsArray()  # Read the raster data into a NumPy array
    transform = ds.GetGeoTransform()  # Get the geotransformation of the raster (spatial reference info)
    projection = ds.GetProjection()  # Get the projection information
    return array, transform, projection

# Function to save a raster file using GDAL
def save_raster(output_path, data, transform, projection):
    driver = gdal.GetDriverByName('GTiff')  # Use the GeoTIFF format
    rows, cols = data.shape  # Get the number of rows and columns from the data array
    out_raster = driver.Create(output_path, cols, rows, 1, gdal.GDT_Float32)  # Create a new raster file
    out_raster.SetGeoTransform(transform)  # Set the spatial reference of the output raster
    out_raster.SetProjection(projection)  # Set the projection of the output raster
    out_band = out_raster.GetRasterBand(1)  # Get the first band of the output raster
    out_band.WriteArray(data)  # Write the data array to the raster band
    out_raster.FlushCache()  # Flush the cache to ensure the file is written to disk
    out_band.SetNoDataValue(0)  # Set the no-data value if required (optional)

# Function to subtract the values of two rasters and handle negative values
def subtract_rasters(raster1_path, raster2_path, output_raster_path):
    # Step 1: Read the first raster
    raster1_data, transform1, projection1 = read_raster(raster1_path)
    
    # Step 2: Read the second raster
    raster2_data, transform2, projection2 = read_raster(raster2_path)
    
    # Step 3: Check if the dimensions of both rasters match
    if raster1_data.shape != raster2_data.shape:
        raise ValueError("The two raster files must have the same dimensions.")
    
    # Step 4: Perform the subtraction (raster1 - raster2)
    result_data = raster1_data - raster2_data
    
    # Step 5: Replace negative values with 0 and set any values above 1000 to 0
    result_data[result_data < 0] = 0
    result_data[result_data > 1000] = 0
    
    # Step 6: Save the result as a new raster file
    save_raster(output_raster_path, result_data, transform1, projection1)


# Function to interpolate missing values (only for no-data areas)
def fill_interpolate_raster_only_missing(data):
    # Create a mask to identify the no-data areas (assuming np.nan represents no-data)
    mask = np.isnan(data)
    x, y = np.indices(data.shape)  # Create index grids for the raster data

    # Identify the known (non-nan) and missing (nan) points
    known_points = np.where(~mask)  # Non-nan values are known data points
    missing_points = np.where(mask)  # Nan values are missing data points
    
    known_values = data[known_points]  # Extract the known values from the data array
    grid_x, grid_y = missing_points  # Get the coordinates of the missing points

    # Perform interpolation only on the missing points
    interpolated_values = griddata(known_points, known_values, (grid_x, grid_y), method='nearest')
    
    # Create a copy of the original data array to hold the interpolated results
    result = np.copy(data)
    
    # Fill the interpolated values into the missing (nan) areas
    result[missing_points] = interpolated_values
    
    return result

# Function to read a raster file using GDAL
def fill_read_raster(raster_path):
    ds = gdal.Open(raster_path)  # Open the raster file
    band = ds.GetRasterBand(1)  # Get the first band (assuming single band raster)
    array = band.ReadAsArray().astype(np.float32)  # Read the raster data into a NumPy array
    transform = ds.GetGeoTransform()  # Get the geotransformation of the raster (spatial reference info)
    # Replace the no-data value (assumed to be 0) with np.nan
    no_data_value = band.GetNoDataValue()
    if no_data_value is not None:
        array[array == no_data_value] = np.nan
    return array, transform

# Function to save a raster file using GDAL
def fill_save_raster(output_path, data, transform, reference_raster):
    driver = gdal.GetDriverByName('GTiff')  # Use the GeoTIFF format
    rows, cols = data.shape  # Get the number of rows and columns from the data array
    out_raster = driver.Create(output_path, cols, rows, 1, gdal.GDT_Float32)  # Create a new raster file
    out_raster.SetGeoTransform(transform)  # Set the spatial reference of the output raster
    out_band = out_raster.GetRasterBand(1)  # Get the first band of the output raster
    # Set NoData to np.nan and replace np.nan with 0 for saving
    out_band.WriteArray(np.nan_to_num(data, nan=0))  
    out_raster.FlushCache()  # Flush the cache to ensure the file is written to disk
    out_band.SetNoDataValue(0)  # Set the no-data value to 0


# Main function to fill the gaps in the raster by interpolating missing values
def fill_raster_gaps(input_raster, output_raster):
    # Step 1: Read the original raster data
    original_data, transform = fill_read_raster(input_raster)
    
    # Step 2: Perform interpolation only for the missing areas
    filled_data = fill_interpolate_raster_only_missing(original_data)
    
    # Step 3: Save the final result as a new raster file
    fill_save_raster(output_raster, filled_data, transform, input_raster)
    
