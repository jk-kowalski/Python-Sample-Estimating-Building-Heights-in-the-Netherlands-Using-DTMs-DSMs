import glob
import geopandas as gpd
import os

import rasterio

from utils import *

# Make sure directories exist
if not os.path.exists('data'):
    os.makedirs('data')
if not os.path.exists('output'):
    os.makedirs('output')

# Define the Buurten.csv path
buurten_path = "assets/Buurten.csv"

# Check if Buurten.dbf exists & read file
if not os.path.exists(buurten_path):
    print(f"The file '{buurten_path}' does not exist.")
    print("Please download the 'Buurten.dbf' file from Teams and place it in the 'data' folder.")
else:
    # Load the file into a GeoDataFrame if it exists
    buurten_gdf = gpd.read_file(buurten_path)
    print("Buurten.dbf file loaded successfully.")

# Filter buurten_gdf
filtered_nl_gdf, neighborhood_name = filter_neighborhoods_by_municipality(buurten_gdf)

# Make sure directories exist
if not os.path.exists('data/boundary_nl'):
    os.makedirs('data/boundary_nl')

# Download neighborhood boundary data to geojson
nl_boundary_gdf = download_neighborhood_data(filtered_nl_gdf, neighborhood_name)

# Define the kaartbladindex.json path
kaartbladindex_path = "assets/kaartbladindex.json"

# Check if kaartbladindex.json exists & read file
if not os.path.exists(kaartbladindex_path):
    print(f"The file '{kaartbladindex_path}' does not exist.")
    print("Please download the 'kaartbladindex.json' file from Teams and place it in the 'data' folder.")
else:
    # Load the file into a GeoDataFrame if it exists
    kaartbladindex_gdf = gpd.read_file(kaartbladindex_path)
    print("kaartbladindex.json file loaded successfully.")


"""
Important: 
This may sometime not converted succesfully! 
Please choose another neighborhood then!
"""

# Convert to Input neighborhood to existing kaartbladindex
matching_kaartbladindex_gdf, matching_kaartbladindex_kaartbladNr_suffix  = find_matching_index(nl_boundary_gdf, kaartbladindex_gdf)
print('matching_kaartbladindex_kaartbladNr_suffix: ', matching_kaartbladindex_kaartbladNr_suffix)

# Downloading neighborhood-level building boundary vector dataset
nl_building_boundary_extract_dir = download_and_extract_building_boundaries(matching_kaartbladindex_kaartbladNr_suffix, neighborhood_name)

# Load the neighborhood-level building boundary dataset
gpkg_files = glob.glob(os.path.join(nl_building_boundary_extract_dir, "*.gpkg"))

# Check if any .gpkg file exists
if len(gpkg_files) > 0:
    # If the file exists, load the first one (if there are multiple, you may want to load all or specify one)
    nl_building_boundary_gdf = gpd.read_file(gpkg_files[0])  # You can load the first .gpkg file found
    print("Neighborhood-level " + neighborhood_name + " building boundary dataset loaded successfully.")
else:
    print("No .gpkg file found in the directory.")

# Get the bounding box of neighborhood-level boundary dataset
# buurt_gdf = gpd.read_file("data/buurt.geojson")

# if nl_boundary_gdf.crs != buurt_gdf.crs:
#     nl_boundary_gdf = nl_boundary_gdf.to_crs(buurt_gdf.crs)

nl_boundary_gdf = nl_boundary_gdf.to_crs(epsg=28992)

xmin, ymin, xmax, ymax = nl_boundary_gdf.total_bounds
bounds = [xmin, ymin, xmax, ymax]
bbox = (float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3]))

# Make sure directories exist
if not os.path.exists('data/DSM'):
    os.makedirs('data/DSM')
if not os.path.exists('data/DTM'):
    os.makedirs('data/DTM')

# Define download file names
dsm_filename = "data/DSM/" + neighborhood_name + "_dsm_05m.tif"
dtm_filename = "data/DTM/" + neighborhood_name + "_dtm_05m.tif"

# #Download both DSM and DTM using the bounding box
ahn_05m_for_study_area(bbox, dsm_filename, coverage_id='dsm_05m')
ahn_05m_for_study_area(bbox, dtm_filename, coverage_id='dtm_05m')

try:
    # Load and inspect the downloaded DSM file
    with rasterio.open(dsm_filename) as dsm:
        print("DSM metadata:", dsm.meta)
    
    # Load and inspect the downloaded DTM file
    with rasterio.open(dtm_filename) as dtm:
        print("DTM metadata:", dtm.meta)

except Exception as e:
    print("Please use another neighborhood. Due to objective reasons, we cannot obtain the DTM & DSM data here.")
    raise e  # throw errow and end program

# Record neighborhood_name
with open('data/nl_records.txt', 'a') as file:
    file.write(neighborhood_name + '\n')
