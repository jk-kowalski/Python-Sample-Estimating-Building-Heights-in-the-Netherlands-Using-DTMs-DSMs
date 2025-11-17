import os
import sys

import zipfile

import geopandas as gpd
import pandas as pd
import numpy as np

import requests

from owslib.wcs import WebCoverageService


def filter_neighborhoods_by_municipality(buurten_gdf):
    """
    This function prompts the user to input a municipality and then displays
    the available neighborhoods. The user can then select neighborhoods by 
    their indices, and the function will return the filtered GeoDataFrame.

    Parameters:
    buurten_gdf (GeoDataFrame): GeoDataFrame containing municipality and neighborhood data.

    Returns:
    GeoDataFrame: Filtered GeoDataFrame based on selected municipality and neighborhoods.
    """

    # Ask for municipality input
    municipality = input("Please enter the name of the municipality (case sensitive): ")
    print(" your input for municipality: ", municipality)

    # Filter based on the municipality
    filtered_buurten_gdf = buurten_gdf[buurten_gdf["gm_naam"] == municipality]

    # Check if the municipality exists
    if filtered_buurten_gdf.empty:
        print(f"No data found for Municipality: {municipality}")

        # Display available municipalities
        available_municipalities = buurten_gdf['gm_naam'].unique()
        sorted_municipalities = np.sort(available_municipalities)
        print("Available municipalities:")

        for i, m_name in enumerate(sorted_municipalities, 1):
            print(f"{i}. {m_name}")
        print("Please check the list above for available municipalities and try again.")

        return None  # Exit the function

    # Display available neighborhoods in the municipality
    available_neighborhoods = filtered_buurten_gdf['bu_naam'].unique()
    sorted_neighborhoods = np.sort(available_neighborhoods)
    print(f"Available neighborhoods in {municipality}:")

    for i, neighborhood in enumerate(sorted_neighborhoods, 1):
        print(f"{i}. {neighborhood}")

    # Ask for neighborhoods
    neighborhood_input = input("Please enter the number of the neighborhood you want: ")
    print(" your input for neighborhood: ", neighborhood_input)

    try:
        # Convert the input to a list of integers
        neighborhood_indices = list(map(int, neighborhood_input.split()))

        # Check if input indices are within the valid range
        if any(i > len(sorted_neighborhoods) or i < 1 for i in neighborhood_indices):
            print("Invalid input. Please select a valid neighborhood number within the displayed range.")
            return None  # Exit the function

    except ValueError:
        # Catch non-integer input
        print("Invalid input. Please enter only numeric values.")
        return None  # Exit the function

    # Get the selected neighborhoods
    neighborhoods = [sorted_neighborhoods[i - 1] for i in neighborhood_indices]

    # Filter based on selected neighborhoods
    filtered_nl_gdf = filtered_buurten_gdf[filtered_buurten_gdf['bu_naam'].isin(neighborhoods)]

    if filtered_nl_gdf.empty:
        print(f"No data found for Municipality: {municipality} and Neighborhood(s): {neighborhoods}")
        return None  # Exit the function

    neighborhoods_str = "_".join([neighborhood.replace(" ", "_") for neighborhood in neighborhoods])
    
    return filtered_nl_gdf, neighborhoods_str  # Return the filtered GeoDataFrame


def download_neighborhood_data(filtered_nl_gdf, neighborhood_name):
    """
    This function generates a WFS request URL based on the provided GeoDataFrame and downloads
    the corresponding neighborhood data as a GeoJSON file.
    
    Parameters:
    filtered_nl_gdf (GeoDataFrame): The filtered GeoDataFrame containing the selected neighborhoods.
    neighborhood_name (str): The name of the neighborhood(s), which will be used for naming the output file.

    Returns:
    GeoDataFrame or None: Returns the downloaded data as a GeoDataFrame if successful, otherwise returns None.
    """
    
    # Extract all matching bu_codes
    buurtcodes = filtered_nl_gdf['bu_code'].values

    # Construct the URL
    url_head = 'https://service.pdok.nl/cbs/wijkenbuurten/2023/wfs/v1_0?request=GetFeature&service=WFS&version=1.1.0&typeName=wb2021:buurten&filter=%3CFilter%3E'
    url_single_buurtcode_start = '%3CPropertyIsEqualTo%20matchCase=%22true%22%3E%3CValueReference%3Ebuurtcode%3C/ValueReference%3E%3CLiteral%3E'
    url_single_buurtcode_end = '%3C/Literal%3E%3C/PropertyIsEqualTo%3E'
    url_end = '%3C/Filter%3E'

    # If there are multiple buurtcodes, wrap them with <Or> tags
    if len(buurtcodes) > 1:
        url_head += '%3COr%3E'
        url_end = '%3C/Or%3E' + url_end

    # Append each buurtcode to the URL
    for buurtcode in buurtcodes:
        url_head += url_single_buurtcode_start + buurtcode + url_single_buurtcode_end

    download_url = url_head + url_end

    # Set the download path
    download_path = f"data/boundary_nl/{neighborhood_name}.geojson"

    # Download the data from the constructed URL
    response = requests.get(download_url)
    
    if response.status_code == 200:
        # Save the response content to a GeoJSON file
        with open(download_path, "w") as f:
            f.write(response.text)
        print(f"neighborhood boundary data downloaded successfully to {download_path}")

        # Load the GeoJSON file into a GeoDataFrame
        gdf = gpd.read_file(download_path)

        return gdf  # Return the downloaded GeoDataFrame
    else:
        print(f"Failed to download data. HTTP status code: {response.status_code}")
        return None  # Return None if the download failed


def find_matching_index(nl_boundary_gdf, kaartbladindex_gdf):
    """
    Find the rows in kaartbladindex_gdf where the geometries in nl_boundary_gdf match,
    and return the matching GeoDataFrame. Also extracts the part after the underscore
    in 'kaartbladNr'.

    Parameters:
    nl_boundary_gdf (GeoDataFrame): GeoDataFrame containing the geometries to search for.
    kaartbladindex_gdf (GeoDataFrame): GeoDataFrame containing the target geometries.

    Returns:
    GeoDataFrame: Returns the matching rows from kaartbladindex_gdf.
    """
    matching_rows = []

    # Iterate through the geometries in nl_boundary_gdf
    for nl_geom in nl_boundary_gdf["geometry"]:
        # Check if nl_geom is within any of the geometries in kaartbladindex_gdf
        matches = kaartbladindex_gdf[kaartbladindex_gdf["geometry"].apply(lambda x: nl_geom.within(x))]
        
        matching_rows.append(matches)

    # Concatenate the matching rows into a GeoDataFrame
    result_gdf = gpd.GeoDataFrame(pd.concat(matching_rows, ignore_index=True))

    # If result_gdf is empty, print an error message and exit the function
    kaartbladNr_suffix = []
    
    if result_gdf.empty:
        nl_boundary_gdf['centroid'] = nl_boundary_gdf.geometry.centroid
        nl_boundary_gdf_overall_center = nl_boundary_gdf['centroid'].unary_union.centroid

        matching_row = kaartbladindex_gdf[kaartbladindex_gdf.geometry.contains(nl_boundary_gdf_overall_center)]

        if not matching_row.empty:
            matching_geometry = matching_row.geometry.iloc[0]
            adjacent_rows = kaartbladindex_gdf[kaartbladindex_gdf.geometry.touches(matching_geometry)]

            if not adjacent_rows.empty:
                matching_suffix = matching_row['kaartbladNr'].str.split('_').str[1].iloc[0].lower()
                kaartbladNr_suffix.append(matching_suffix)

                adjacent_suffixes = adjacent_rows['kaartbladNr'].str.split('_').str[1].str.lower()
                kaartbladNr_suffix.extend(adjacent_suffixes.tolist())

                return result_gdf, kaartbladNr_suffix 
            else:
                print("no attached rows")
            sys.exit()
        else:
            print("still we can't find this neighborhood")
            sys.exit()

        print("Converting input neighborhood may sometime not succeed! \nPlease choose another neighborhood then!")
        sys.exit()  # Or use `sys.exit()` to terminate the program

    # Extract the part after the underscore in the 'kaartbladNr' column
    kaartbladNr_suffix_single_result = result_gdf['kaartbladNr'].str.split('_').str[1].loc[0].lower()
    kaartbladNr_suffix.append(kaartbladNr_suffix_single_result)

    return result_gdf, kaartbladNr_suffix 


# def download_and_extract_building_boundaries(matching_kaartbladindex_kaartbladNr_suffix, neighborhood_name):
#     """
#     Downloads and extracts building boundary data for a specific neighborhood.
    
#     Parameters:
#     matching_kaartbladindex_kaartbladNr_suffix (str): The suffix used to generate the file URL.
#     neighborhood_name (str): The name of the neighborhood for file naming.

#     Returns:
#     None
#     """
#     # Generate the download URL and file paths
#     nl_building_boundary_url = ("https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2020/hoogtestatistieken/" +
#                                 matching_kaartbladindex_kaartbladNr_suffix + "_2020_hoogtestatistieken_gebouwen.zip")
    
#     nl_building_boundary_zip_file_path = f"data//boundary_building//{neighborhood_name}"  + "_2020_hoogtestatistieken_gebouwen.zip"
#     nl_building_boundary_extract_dir = "data//boundary_building//" + neighborhood_name

#     # Make sure directories exist
#     if not os.path.exists('data/boundary_building'):
#         os.makedirs('data/boundary_building')

#     # Check if the zip file already exists, if not, download it
#     if not os.path.exists(nl_building_boundary_zip_file_path):
#         response = requests.get(nl_building_boundary_url)
#         with open(nl_building_boundary_zip_file_path, 'wb') as file:
#             file.write(response.content)
#             print(f"Downloading: {nl_building_boundary_zip_file_path}")
#     else:
#         print(f"Already downloaded: {nl_building_boundary_zip_file_path}")

#     # Check if the extracted directory exists, if not, create the directory and extract the zip file
#     if not os.path.exists(nl_building_boundary_extract_dir):
#         os.makedirs(nl_building_boundary_extract_dir)  # Create the directory
#         with zipfile.ZipFile(nl_building_boundary_zip_file_path, 'r') as zip_ref:
#             zip_ref.extractall(nl_building_boundary_extract_dir)
#             print(f"Extracting to: {nl_building_boundary_extract_dir}")
#     else:
#         print(f"Already extracted: {nl_building_boundary_extract_dir}")

#     return nl_building_boundary_extract_dir


def download_and_extract_building_boundaries(matching_kaartbladindex_kaartbladNr_suffix, neighborhood_name):
    """
    Downloads and extracts building boundary data for a specific neighborhood.
    
    Parameters:
    matching_kaartbladindex_kaartbladNr_suffix (str or list): The suffix used to generate the file URL. Can be a string or a list of strings.
    neighborhood_name (str): The name of the neighborhood for file naming.

    Returns:
    None
    """
    # Create directory for boundary data if it doesn't exist
    base_dir = "data//boundary_building"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    # If input is a single string, convert it to a list for uniform processing
    if isinstance(matching_kaartbladindex_kaartbladNr_suffix, str):
        matching_kaartbladindex_kaartbladNr_suffix = [matching_kaartbladindex_kaartbladNr_suffix]

    # List to store the paths of extracted gpkg files
    extracted_dpkg_paths = []

    # Make sure directories exist
    if not os.path.exists(f"data//boundary_building//{neighborhood_name}"):
        os.makedirs(f"data//boundary_building//{neighborhood_name}")

    # Loop through all suffixes in the list
    for suffix in matching_kaartbladindex_kaartbladNr_suffix:
        # Generate the download URL and file paths
        nl_building_boundary_url = ("https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2020/hoogtestatistieken/" +
                                    suffix + "_2020_hoogtestatistieken_gebouwen.zip")
        
        nl_building_boundary_zip_file_path = f"{base_dir}//{neighborhood_name}//{suffix}_2020_hoogtestatistieken_gebouwen.zip"
        nl_building_boundary_unzip_file_path = f"{base_dir}//{neighborhood_name}//{suffix}_2020_hoogtestatistieken_gebouwen.gpkg"

        nl_building_boundary_extract_dir = f"{base_dir}//{neighborhood_name}//"

        # print('nl_building_boundary_unzip_file_path: ', nl_building_boundary_unzip_file_path)

        # Check if the zip file already exists, if not, download it
        if not os.path.exists(nl_building_boundary_zip_file_path):
            response = requests.get(nl_building_boundary_url)
            with open(nl_building_boundary_zip_file_path, 'wb') as file:
                file.write(response.content)
                print(f"Downloading: {nl_building_boundary_zip_file_path}")
        else:
            print(f"Already downloaded: {nl_building_boundary_zip_file_path}")

        # Check if the extracted directory exists, if not, create the directory and extract the zip file
        if not os.path.exists(nl_building_boundary_unzip_file_path):
            with zipfile.ZipFile(nl_building_boundary_zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(nl_building_boundary_extract_dir)
                print(f"Extracting to: {nl_building_boundary_extract_dir}")
        else:
            print(f"Already extracted: {nl_building_boundary_unzip_file_path}")

        if os.path.exists(nl_building_boundary_extract_dir):
            extracted_dpkg_paths.append(nl_building_boundary_unzip_file_path)

    # print('extracted_dpkg_paths: ', extracted_dpkg_paths)
    # exit(0)

    # If multiple gpkg files are extracted, merge them
    if len(extracted_dpkg_paths) > 1:
        print(f"Merging {len(extracted_dpkg_paths)} gpkg files...")

        # Read all gpkg files as GeoDataFrames and concatenate them
        merged_gdf = gpd.GeoDataFrame(pd.concat([gpd.read_file(gpkg) for gpkg in extracted_dpkg_paths], ignore_index=True))

        # Define the output merged file path
        merged_dpkg_file = os.path.join(base_dir, f"{neighborhood_name}/merged_buildings.gpkg")

        # Save the merged GeoDataFrame to the new gpkg file
        if 'fid' in merged_gdf.columns:
            merged_gdf = merged_gdf.drop(columns=['fid'])
        merged_gdf.to_file(merged_dpkg_file, driver='GPKG')
        print(f"Merged gpkg file saved to: {merged_dpkg_file}")

        # Remove the original gpkg files
        for dpkg_file in extracted_dpkg_paths:
            os.remove(dpkg_file)
            print(f"Deleted old gpkg file: {dpkg_file}")
    else:
        print("No multiple gpkg files to merge.")
    
    return nl_building_boundary_extract_dir


def ahn_05m_for_study_area(extent, output_filename, coverage_id):
    """This function extracts for a given extent (bbox) the AHN3 Digital Elevation Model (DEM) or
    Digital Terrain Model (DTM) at 0.5m resolution and saves as a GeoTIFF."""
    # Specify the AHN3 WCS URL
    wcs = WebCoverageService('https://service.pdok.nl/rws/ahn/wcs/v1_0?SERVICE=WCS', version='1.0.0')
    
    # Download and save the raster (DEM or DTM) as specified by coverage_id
    response = wcs.getCoverage(identifier=coverage_id, bbox=extent, format='image/tiff',
                               crs='urn:ogc:def:crs:EPSG::28992', resx=2.5, resy=2.5)

    with open(output_filename, 'wb') as file:
        file.write(response.read())
    print(f"{coverage_id} downloaded and saved as {output_filename}")
