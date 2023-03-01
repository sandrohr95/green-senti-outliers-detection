import datetime
import pandas as pd
import folium
from folium.plugins import SemiCircle, Fullscreen, LocateControl, MousePosition, Draw, MeasureControl, FloatImage
from folium.raster_layers import ImageOverlay
import streamlit as st
from streamlit_folium import st_folium, folium_static
from pathlib import Path

from main import execute_workflow
from src.productimeseries.config import settings
from src.productimeseries.mongo import MongoConnection
# from src.productimeseries.utilities.outlier_detection import get_time_series_from_products_mongo
from src.productimeseries.utilities.raster_conversion import _get_corners_raster, save_band_as_png
from src.productimeseries.utilities.utils import get_specific_tif_from_minio, get_time_series_from_products_mongo
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Generate Alerts in Time Series indexes from GeoJson",
    page_icon=":world_map:️",
    layout="wide"
)
st.sidebar.title('Alerts Form')
st.title('Generate Alerts in Time Series indexes from GeoJson')

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
# if "outliers" not in st.session_state:
#     st.session_state["outliers"] = ""
if "center" not in st.session_state:
    st.session_state["center"] = [36.72017310567467, -4.479267597198487]
if "geojson" not in st.session_state:
    st.session_state["geojson"] = "Choose Zone"
if "index" not in st.session_state:
    st.session_state["index"] = "Choose Index"
if "start_date" not in st.session_state:
    # st.session_state["start_date"] = datetime.date(2018, 2, 8)
    st.session_state["start_date"] = "2018-03-30"

if "end_date" not in st.session_state:
    # st.session_state["end_date"] = datetime.date(2023, 1, 20)
    st.session_state["end_date"] = "2025-04-20"
if "warning" not in st.session_state:
    st.session_state["warning"] = False
if "anomalies" not in st.session_state:
    st.session_state["anomalies"] = [False]
if "upper_detection" not in st.session_state:
    st.session_state["upper_detection"] = ""
if "lower_detection" not in st.session_state:
    st.session_state["lower_detection"] = ""
if "outlier_date" not in st.session_state:
    st.session_state["outlier_date"] = ""

# GENERATE FORM
with st.sidebar.form(key="my_form"):
    list_geojson = ['Choose Zone', 'Campo de futbol', 'Bulevar', 'Jardin Botanico']
    list_index = ['Choose Index', 'ndvi', 'tci', 'ri', 'cri1', 'bri','classifier', 'moisture',
                  'evi', 'osavi', 'evi2', 'ndre', 'ndyi', 'bri', 'ndsi', 'ndwi', 'mndwi', 'bsi']
    st.session_state["geojson"] = st.selectbox(
        'Which place do you want to study?',
        list_geojson
    )
    st.session_state["index"] = st.selectbox(
        'Which index do you want to study?',
        list_index
    )

    # st.session_state["start_date"] = st.date_input(
    #     label="Select a date",
    #     value=st.session_state["start_date"],
    #     min_value=datetime.date(2018, 1, 8))
    #
    # st.session_state["end_date"] = st.date_input(
    #     "Select a end date",
    #     st.session_state["end_date"],
    #     max_value=datetime.date(2023, 1, 21))

    submit_button = st.form_submit_button(label="Detect Outliers", help="Submit Button")

    if submit_button:
        if st.session_state["geojson"] == 'Choose Zone' or st.session_state["index"] == 'Choose Index':
            st.session_state["warning"] = True
        else:
            with st.spinner('Updating time-series data in the database ...'):
                st.session_state.df = execute_workflow(st.session_state["geojson"],
                                                       st.session_state["start_date"],
                                                       st.session_state["end_date"],
                                                       st.session_state["index"])
                # st.session_state["outliers"] = find_outliers_iqr(st.session_state.df)
                st.session_state["warning"] = False


# Function to generate a Map Visualization
def generate_map() -> folium.Map:
    map_folium = folium.Map(location=st.session_state["center"], zoom_start=18,
                            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                            attr='Satellite attribution')
    Draw(
        export=True,
        draw_options={
            "circle": False,
            "marker": False,
            "circlemarker": False,
            "polyline": False,
            "polygon": {
                "allowIntersection": False,
                "showArea": True
            }
        }
    ).add_to(map_folium)
    Fullscreen().add_to(map_folium)
    LocateControl().add_to(map_folium)
    MousePosition().add_to(map_folium)
    MeasureControl("bottomleft").add_to(map_folium)

    map_layers_dict = {
        "World Street Map": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        "Satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "Google Maps": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        "Google Satellite": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "Google Terrain": 'https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
        "Google Satellite Hybrid": 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}'
    }

    for layer in map_layers_dict:
        folium.TileLayer(
            tiles=map_layers_dict[layer],
            attr=layer,
            name=layer,
            show=False
        ).add_to(map_folium)
    return map_folium


def home_page():
    # HOME PAGE
    home1, home2 = st.columns(2)
    with home1:
        "## Start Exploring"
        """
        Currently, there are two functions defined:

        - `Select Area of Interest`: In this version of the application the user will be able to study different areas of the Teatinos campus of the University of Malaga.

        - `Select Indices`: The user can select the indices to be studied for the detection of possible anomalies in the time series.
        """
        "### Time Series Outlier Detection"

        """
        The Green-Senti project proposes a new web service for the monitoring of green areas on the campus of the University of Malaga, 
        and its evolution in general, through the capture and analysis of satellite images Sentinel-2 of the Copernicus program of the EU. 
        This service will be implemented as a demonstration pilot consisting of a platform with Big Data technology for the collection, consolidation, 
        analysis and data service. Within the scope of the project in terms of time, orientation and budget, the analysis will focus on the campus of 
        the University of Malaga (Teatinos, Extension of Teatinos and El Ejido).

        This application has been designed by [Khaos research group](https://khaos.uma.es).
        """
    with home2:
        map_folium = generate_map()
        folium_static(map_folium, height=500, width=700)


def execute_outliers_detection():
    # OUTLIER DETECTION
    data = st.session_state.df
    column = data[st.session_state['index']]
    n = len(column)
    st.session_state["outlier_date"] = data.index
    # parameters
    window_percentage = 3
    k = int(len(column) * (window_percentage / 100))
    # column = column.to_numpy()
    get_bands = lambda data: (np.mean(data) + 3 * np.std(data), np.mean(data) - 3 * np.std(data))
    # get_bands = lambda data: (np.mean(data) + np.nanquantile(data, 0.99), np.mean(data) - np.nanquantile(data, 0.99))
    bands = [get_bands(column[range(0 if i - k < 0 else i - k, i + k if i + k < n else n)]) for i in range(0, n)]
    st.session_state['upper_detection'], st.session_state['lower_detection'] = zip(*bands)
    # compute local outliers
    st.session_state["anomalies"] = (column > st.session_state['upper_detection']) | (
            column < st.session_state['lower_detection'])


def print_outliers_time_series():
    # plotting...
    fig = plt.figure(figsize=(28, 10))
    plt.xticks(fontsize=24)
    plt.yticks(fontsize=24)
    plt.plot(st.session_state["outlier_date"], column, 'k', label=st.session_state['index'])
    plt.plot(st.session_state["outlier_date"], st.session_state['upper_detection'], 'r-', label='Bands',
             alpha=0.5)
    plt.plot(st.session_state["outlier_date"], st.session_state['lower_detection'], 'r-', alpha=0.5)
    plt.plot(st.session_state["outlier_date"][st.session_state["anomalies"]],
             column[st.session_state["anomalies"]], 'ro',
             label='Anomalies')
    plt.fill_between(st.session_state["outlier_date"], st.session_state['upper_detection'],
                     st.session_state['lower_detection'],
                     facecolor='red', alpha=0.1)
    plt.legend(fontsize=24)
    st.pyplot(fig)


def download_specific_tif_from_minio(specific_date: str, outliers: bool):
    # cut TIF image with the selected geojson que and return this path to get the coordinates of the TIF
    sample_band_cut_path = get_specific_tif_from_minio(st.session_state['geojson'],
                                                       specific_date,
                                                       st.session_state['index'])

    y_max, y_min, x_max, x_min = _get_corners_raster(sample_band_cut_path)
    # Get Central point
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    st.session_state["center"] = [center_y, center_x]
    # Visualization in folium
    map_raster = generate_map()
    # If we found outliers we need to show this overlay image in the map
    if outliers:
        # Convert cut band to PNG format
        png_path = str(Path(settings.TMP_DIR,
                            last_outlier_date + '_' + st.session_state['geojson'] + '_' + st.session_state[
                                "index"] + '.png'))
        save_band_as_png(st.session_state["index"], sample_band_cut_path, png_path)
        # fit bounds rasters
        ImageOverlay(
            image=png_path,
            bounds=[[y_min, x_min], [y_max, x_max]],
            opacity=0.5
        ).add_to(map_raster)
    folium_static(map_raster, height=500, width=700)
    return sample_band_cut_path


# RENDERING CODE
if st.session_state["warning"]:
    st.warning("WARNING: Please enter the required fields", icon="⚠️")
    home_page()
elif not st.session_state.df.empty:
    with st.spinner('Outlier Detection Wait for it...'):
        # First Detect Outliers
        execute_outliers_detection()
        # st.write(st.session_state.df.index)
        column = st.session_state.df[st.session_state['index']]
        # If outlier exist download last TIF outlier if not, download the last TIF os the time series
        col1, col2 = st.columns(2)
        # IF WE FIND OUTLIERS WE DOWNLOAD THE TIF FROM THIS DATE TO GENERATE THE CENTER MAP ANS SHOW THE INDEX IMAGE
        if np.any(st.session_state["anomalies"] == True):
            last_outlier_date = str(st.session_state["outlier_date"][st.session_state["anomalies"]][0])
            number_of_outliers = len(st.session_state["outlier_date"][st.session_state["anomalies"]])
            with col1:
                st.write('#### Time Series Visualization')
                st.line_chart(st.session_state.df, height=280)
                st.error('We detect ' + str(number_of_outliers) + ' outliers. The last one was: ' + last_outlier_date,
                         icon="🚨")
                st.write("##### Time Series Outlier Detection")
                # Here we plot time series detection
                print_outliers_time_series()
            with col2:
                st.write("#### Map Visualization of " + st.session_state["geojson"])
                # Show outliers in map
                sample_band_cut_path = download_specific_tif_from_minio(last_outlier_date, outliers=True)
                # Explanation of the results
                with st.expander("Get More Information"):
                    "###### Statistical Information"
                    st.write("The last outlier was the day: " + last_outlier_date)
                    st.write('Number of outliers: ' + str(number_of_outliers))
                    "###### Download Image"
                    st.write(
                        "You can download the index of the last outlier found in the time series analysis in the "
                        "button below: ")
                    # Download Button (We need to download the image from MiniO or temp directory)
                    with open(sample_band_cut_path,
                              "rb") as file:
                        st.download_button(
                            label="Download image of " + st.session_state["index"],
                            data=file,
                            file_name="index.tif",
                            mime="image/tif"
                        )
                    st.write("If you want to obtain more information about yo can go to: "
                             "*https://khaos.uma.es/green-senti/explore* ")


        # IF WE DO NOT FIND OUTLIERS WE DOWNLOAD THE LAS TIF IN THE TIME SERIES TO GENERATE THE CENTER MAP
        else:
            with col1:
                st.write('#### Time Series Visualization')
                st.line_chart(st.session_state.df, height=280)
                st.write("##### Time Series Outlier Detection")
                st.info("Fortunately, no anomaly has been found in this area of " + st.session_state['geojson'] +
                        " for the selected index:  " + st.session_state['index'], icon="ℹ️")
            with col2:
                st.write("#### Map Visualization of " + st.session_state["geojson"])

                last_date_time_series = str(st.session_state.df.index[0])
                # cut TIF image with the selected geojson que and return this path to get the coordinates of the TIF
                sample_band_cut_path = download_specific_tif_from_minio(last_date_time_series, outliers=False)

else:
    home_page()
