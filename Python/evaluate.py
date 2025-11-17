import geopandas as gpd
from sklearn.metrics import root_mean_squared_error

from utils import *

import matplotlib.pyplot as plt

estimated_buildings_height_folder = "output//estimated_building_height//"

all_files, filenames_without_extension = list_files_in_directory(estimated_buildings_height_folder)

real_buildings_height_folder = "data//boundary_building//"

for i in range(len(all_files)):
    # print(all_files[i], filenames_without_extension[i])

    # read real building height value
    real_buildings_height_path = real_buildings_height_folder + all_files[i][:-5] + "_vector.shp"
    real_buildings_height_gdf = gpd.read_file(real_buildings_height_path)
    # print('columns: ', real_buildings_height_gdf.columns)

    real_buildings_height_gdf["ground truth bh value"] = real_buildings_height_gdf["dd_h_dak_m"] - real_buildings_height_gdf["h_maaiveld"] 

    # read estimated building height value
    estimated_buildings_height_path = estimated_buildings_height_folder + all_files[i]
    estimated_buildings_height_gdf = gpd.read_file(estimated_buildings_height_path)

    # check the nan value
    # print("nan value: ", "clipped_buildings_gdf nan: ", \
    #     real_buildings_height_gdf["ground truth bh value"].isnull().sum(), \
    #     "predict_gdf nan: ", \
    #         estimated_buildings_height_gdf["MeanValue"].isnull().sum())
    
    null_index_1 = real_buildings_height_gdf[real_buildings_height_gdf["ground truth bh value"].isnull()].index
    clipped_buildings_gdf_1 = real_buildings_height_gdf.drop(null_index_1)
    predict_gdf_1 = estimated_buildings_height_gdf.drop(null_index_1)
    null_index_2 = predict_gdf_1[predict_gdf_1["MeanValue"].isnull()].index
    clipped_buildings_gdf_2 = clipped_buildings_gdf_1.drop(null_index_2)
    predict_gdf_2 = predict_gdf_1.drop(null_index_2)

    # print(real_buildings_height_gdf.shape, estimated_buildings_height_gdf.shape)

    rmse = root_mean_squared_error(clipped_buildings_gdf_2["ground truth bh value"], predict_gdf_2["MeanValue"])

    print(f"RMSE for {filenames_without_extension[i]} is {rmse}")
    

    """ Create 2d map png """
    
    error_percentage = abs(abs(abs(clipped_buildings_gdf_2["ground truth bh value"]) - abs(predict_gdf_2["MeanValue"])) / clipped_buildings_gdf_2["ground truth bh value"]) * 100

    cleaned_gdf = gpd.GeoDataFrame({
        "geometry": clipped_buildings_gdf_2.geometry,  # 
        "ground truth bh value": clipped_buildings_gdf_2["ground truth bh value"],
        "edtimated bh meanvalue": predict_gdf_2["MeanValue"],
        "error_percentage": error_percentage
    }, geometry="geometry")

    cleaned_gdf = cleaned_gdf[(cleaned_gdf["error_percentage"] >= 0) & (cleaned_gdf["error_percentage"] <= 100)]

    cleaned_gdf["height_difference"] = cleaned_gdf["ground truth bh value"] - cleaned_gdf["edtimated bh meanvalue"]
    cleaned_gdf["absolute_difference"] = abs(cleaned_gdf["ground truth bh value"] - cleaned_gdf["edtimated bh meanvalue"])

    output_folder = f"output/{filenames_without_extension[i]}/"
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f'created folder {output_folder}')
    
    # height_difference_map
    legend_kwds= {
        'loc': 'upper right',
        'bbox_to_anchor': (1.2, 1),
        'fmt': '{:<5.0f}',
        'frameon': False,
        'fontsize': 8,
        'title': 'height difference (m)'
    }
    classification_kwds={
        'bins':[-4, -3, -2, -1, 0, 1, 2, 3, 4, 5]
    }
    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches(10,10)

    cleaned_gdf.plot(ax=ax, column='height_difference', cmap='PuOr_r', scheme='User_Defined',
            classification_kwds=classification_kwds,
            legend=True, legend_kwds=legend_kwds,
            edgecolor='black', linewidth=0.2)

    ax.set_axis_off()

    # Change the last entry in the legend to '>5000'
    legend = ax.get_legend()
    legend.texts[0].set_text('< -4')
    legend.texts[-1].set_text('> 4')

    # Add a title
    ax.set_title(f'{filenames_without_extension[i]} Building Height Difference (m) Map', size = 18)

    output_path1 = os.path.join(output_folder, f'{filenames_without_extension[i]}_height_difference_map.png')
    plt.savefig(output_path1, dpi=640, bbox_inches='tight', transparent=False)

    legend_kwds= {
        'loc': 'upper right',
        'bbox_to_anchor': (1.2, 1),
        'fmt': '{:<5.1f}',
        'frameon': False,
        'fontsize': 8,
        'title': 'absolute height difference (m)'
    }
    classification_kwds={
       'bins':[0.5, 1, 1.5, 2.5, 3, 4]
    }

    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches(10,10)
    cleaned_gdf.plot(ax=ax, column='absolute_difference', cmap='Oranges', scheme='User_Defined',
            classification_kwds=classification_kwds,
            legend=True, legend_kwds=legend_kwds,
            edgecolor='black', linewidth=0.2)

    ax.set_axis_off()

    # Change the last entry in the legend to '>5000'
    legend = ax.get_legend()
    legend.texts[-1].set_text('> 4')

    # Add a title
    ax.set_title(f'{filenames_without_extension[i]} Absolute Building Height Difference (m) Map', size = 18)
    output_path2 = os.path.join(output_folder, f'{filenames_without_extension[i]}_absolute_height_difference_map.png')

    plt.savefig(output_path2, dpi=640, bbox_inches='tight', transparent=False)


    legend_kwds= {
        'loc': 'upper right',
        'bbox_to_anchor': (1.2, 1),
        'fmt': '{:<5.0f}',
        'frameon': False,
        'fontsize': 8,
        'title': 'error percentage (%)'
    }
    classification_kwds={
     'bins':[1, 5, 10, 25, 50, 100]
    }

    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches(10,10)
    cleaned_gdf.plot(ax=ax, column='error_percentage', cmap='RdYlGn_r', scheme='User_Defined',
            classification_kwds=classification_kwds,
            legend=True, legend_kwds=legend_kwds,
                edgecolor='black', linewidth=0.2)

    ax.set_axis_off()

    # Change the last entry in the legend to '>5000'
    legend = ax.get_legend()
    legend.texts[-1].set_text('> 50')

    # Add a title
    ax.set_title(f'{filenames_without_extension[i]} Error Percentage (%) Map', size = 18)

    output_path3 = os.path.join(output_folder, f'{filenames_without_extension[i]}_error_map.png')
    plt.savefig(output_path3, dpi=640, bbox_inches='tight', transparent=False)

