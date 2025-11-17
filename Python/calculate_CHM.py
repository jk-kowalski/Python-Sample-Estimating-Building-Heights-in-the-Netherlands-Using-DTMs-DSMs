from utils import *

import glob
import json

import os
import shutil

from rasterstats import zonal_stats
import rasterio

# Read the list of names from the text file
with open('data/nl_records.txt', 'r') as file:
    names = file.read().splitlines()

# Create 'data/CHM_nl' directory if it doesn't exist
if not os.path.exists('data/CHM_nl'):
    os.makedirs('data/CHM_nl')
if not os.path.exists('data/DTM_filtered'):
    os.makedirs('data/DTM_filtered')

# Loop through each name and perform the CHM operations
for name in names:
    # Generate file paths based on the name
    DSM_raster_path = f'data/DSM/{name}_dsm_05m.tif'  # DSM file path

    DTM_unfilled_raster_path = f'data/DTM/{name}_dtm_05m.tif'  # DTM file path
    DTM_raster_path = f'data/DTM_filtered/{name}_dtm_05m.tif'  # Output filtered raster file path
    output_CHM_raster_path = f'data/CHM_nl/{name}.tif'   # Output CHM file path

    fill_raster_gaps(DTM_unfilled_raster_path, DTM_raster_path)  # Execute the gap-filling process

    # Check if both DSM and DTM files exist
    if os.path.exists(DSM_raster_path) and os.path.exists(DTM_raster_path):
        # Perform the subtraction and save CHM
        subtract_rasters(DSM_raster_path, DTM_raster_path, output_CHM_raster_path)
        print(f"CHM created for {name}: {output_CHM_raster_path}")
    else:
        print(f"Missing DSM or DTM file for {name}")


# Create 'output/estimated_building_height' directory if it doesn't exist
if not os.path.exists('output/estimated_building_height'):
    os.makedirs('output/estimated_building_height')

""" cut nl CHM to building level """
for name in names:
    # Generate file paths based on the name
    nl_CHM_raster_path = f'data/CHM_nl/{name}.tif'  # 
    boundary_nl_path = f'data/boundary_nl/{name}.geojson'  # 
    output_building_vector_path = f'data/boundary_building/{name}_vector.shp'

    if not os.path.exists(output_building_vector_path):
        buildings_boundary_gpkg_files = glob.glob(os.path.join(f'data//boundary_building/{name}/', "*.gpkg"))
        nl_gdf =  gpd.read_file(boundary_nl_path)
        buildings_boundary_gdf = gpd.read_file(buildings_boundary_gpkg_files[0])

        if buildings_boundary_gdf.crs != nl_gdf.crs:
            buildings_boundary_gdf = buildings_boundary_gdf.to_crs(nl_gdf.crs)
        
        clipped_buildings = gpd.clip(buildings_boundary_gdf, nl_gdf)

        clipped_buildings.to_file(output_building_vector_path, driver="ESRI Shapefile")
        print(f"Clipped buildings dataset saved as '{output_building_vector_path}'.")

    else:
        print(f"File '{output_building_vector_path}' already exists. Skipping clipping operation.")

    """ read new shapefile clipped_buildings """
    nl_building_boundary_gdf = gpd.read_file(output_building_vector_path)

    # read CHM tif 
    with rasterio.open(nl_CHM_raster_path) as nl_CHM_raster:
        stats = zonal_stats(nl_building_boundary_gdf, nl_CHM_raster_path, stats=["mean"])

    nl_bh_gdf = gpd.GeoDataFrame({
        'geometry': nl_building_boundary_gdf['geometry'].copy().to_crs(epsg=4326),  # 
        'mean_value': [stat['mean'] for stat in stats]  # 
    })

    # save to json
    output_json_file = f"output/estimated_building_height/{name}.json"
    # print(nl_bh_gdf.head())

    features = []
    for _, row in nl_bh_gdf.iterrows():
        feature = {
            "type": "Feature",
            "geometry": row['geometry'].__geo_interface__,
            "properties": {
                "MeanValue": row['mean_value']  # 
            }
        }
        features.append(feature)

    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_json_file, 'w') as f:
        json.dump(geojson_data, f, indent=2)

    print(f"{name} nlbh_gdf dataset saved as '{output_json_file}' in GeoJSON format.")


    boundary_building_folder = f'data//boundary_building//{name}//'
    if os.path.exists(boundary_building_folder):
        # 
        shutil.rmtree(boundary_building_folder)
        print(f"Folder '{boundary_building_folder}' and its contents have been deleted.")
    else:
        print(f"The folder '{boundary_building_folder}' does not exist.")

