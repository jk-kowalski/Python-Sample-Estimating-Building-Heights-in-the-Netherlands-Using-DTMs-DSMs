import leafmap.maplibregl as leafmap
import geopandas as gpd
import os


# Read the list of names from the text file
records_txt = "data/nl_records.txt"
with open(records_txt, 'r') as file:
    names = file.read().splitlines()

for name in names:
    # Load your GeoJSON data into a GeoDataFrame
    nl_bh_gdf_path = f"output/estimated_building_height/{name}.json"
    nl_bh_gdf = gpd.read_file(nl_bh_gdf_path)

    # Calculate the centroid for each geometry
    nl_bh_gdf['centroid'] = nl_bh_gdf.geometry.centroid

    # Get the overall center point
    overall_center = nl_bh_gdf['centroid'].unary_union.centroid

    if not os.path.exists(f"output/{name}"):
        os.makedirs(f"output/{name}")
        
    # Check if the 3D map HTML already exists
    map_3d_html_path = f"output/{name}/{name}_map_3d.html"
    if not os.path.exists(map_3d_html_path):
        m = leafmap.Map(
            center=[overall_center.x, overall_center.y], zoom=11, style="dark-matter", pitch=45, bearing=0
        )
    
        paint_line = {
            "line-color": "white",
            "line-width": 2,
        }
        paint_fill = {
            "fill-extrusion-color": {
                "property": "MeanValue",
                "stops": [
                    [0, "white"],
                    [5, "yellow"],
                    [10, "orange"],
                    [15, "darkred"],
                    [20, "purple"],
                ],
            },
            "fill-extrusion-height": ["*", 10, ["sqrt", ["get", "MeanValue"]]],
            "fill-extrusion-opacity": 0.9,
        }
        m.add_geojson(nl_bh_gdf_path, layer_type="line", paint=paint_line, name="blocks-line")
        m.add_geojson(nl_bh_gdf_path, layer_type="fill-extrusion", paint=paint_fill, name="blocks-fill")
        
        # Defining legend
        legend_html = '''
        <div style="
            position: fixed;
            bottom: 50px;
            right: 10px;
            z-index: 9999;
            background-color: rgba(255, 255, 255, 0.8);
            padding: 10px 20px; 
            font-size: 14px;
            border-radius: 5px;
            width: 200px;  
            ">
            <strong>Mean Building Height Value</strong><br>
            <i style="background: white; width: 18px; height: 18px; float: left; margin-right: 8px; opacity: 0.7;"></i> 0 <br>
            <i style="background: yellow; width: 18px; height: 18px; float: left; margin-right: 8px; opacity: 0.7;"></i> 0-5m<br>
            <i style="background: orange; width: 18px; height: 18px; float: left; margin-right: 8px; opacity: 0.7;"></i> 5-10m<br>
            <i style="background: darkred; width: 18px; height: 18px; float: left; margin-right: 8px; opacity: 0.7;"></i> 10-15m<br>
            <i style="background: purple; width: 18px; height: 18px; float: left; margin-right: 8px; opacity: 0.7;"></i> >15m<br>
        </div>
        '''

        
        # Add the HTML legend to the map
        m.add_html(legend_html)
        
        m.to_html(map_3d_html_path)
        print(f"3D map created for {name}: {map_3d_html_path}")
    else:
        print(f"3D map already exists for {name}: {map_3d_html_path}")
        
    """
    Second map without 3D extrusion and valid parameter names
    """
    # Check if the 2D map HTML already exists
    map_2d_html_path = f"output/{name}/{name}_map_2d.html"
    if not os.path.exists(map_2d_html_path):
        m2 = leafmap.Map(
            center=[overall_center.x, overall_center.y], zoom=11, style="dark-matter", pitch=45, bearing=0
        )

        paint_line = {
            "line-color": "white",
            "line-width": 2,
        }
        paint_fill_2d = {
            "fill-color": {
                "property": "MeanValue",
                "stops": [
                    [0, "white"],
                    [5, "yellow"],
                    [10, "orange"],
                    [15, "darkred"],
                    [20, "purple"],
                ],
            },
            "fill-opacity": 0.7,
        }

        # Adding legend. Credits: https://leafmap.org/notebooks/06_legend/
        labels = ["0", "0-5m", "5-10m", "10-15m", "15-20m"]

        colors = ["#FFFFFF", "#FFFF00", "#FFA500", "#8B0000", "#A020F0"]

        m2.add_legend(title="Legend", labels=labels, colors=colors)

        m2.add_geojson(nl_bh_gdf_path, layer_type="line", paint=paint_line, name="blocks-line")
        m2.add_geojson(nl_bh_gdf_path, layer_type="fill", paint=paint_fill_2d, name="blocks-fill")
        m2.to_html(map_2d_html_path)
        print(f"2D map created for {name}: {map_2d_html_path}")
    else:
        print(f"2D map already exists for {name}: {map_2d_html_path}")

os.remove(records_txt)
