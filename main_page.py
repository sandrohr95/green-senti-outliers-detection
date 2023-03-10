import pandas as pd
import folium
from folium.plugins import Fullscreen, LocateControl, MousePosition, Draw, MeasureControl, FloatImage
from folium.raster_layers import ImageOverlay
import streamlit as st
from matplotlib import cm
from streamlit_folium import folium_static
import shutil
from main import execute_workflow
import os
from src.productimeseries.utilities.raster_conversion import _get_corners_raster, open_band, normalize_band, read_rgb_image
from src.productimeseries.utilities.utils import download_specific_tif_from_minio
from src.productimeseries.utilities.streamlit_download_button import download_button
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import tempfile

st.set_page_config(
    page_title="Generate Alerts in Time Series indexes from GeoJson",
    layout="wide"
)
st.sidebar.title('Alerts Form')
st.title('Generate Alerts in Time Series indexes from GeoJson')

if "geojson" not in st.session_state:
    st.session_state["geojson"] = "Choose Zone"
if "index" not in st.session_state:
    st.session_state["index"] = "Choose Index"
if "start_date" not in st.session_state:
    st.session_state["start_date"] = "2018-03-30"
if "end_date" not in st.session_state:
    st.session_state["end_date"] = "2025-04-20"


@st.cache_data
def _execute_complete_workflow(geojson_name: str, start_date: str,
                               end_date: str, index_name: str, tmp_dirname) -> pd.DataFrame:
    df_wk = execute_workflow(geojson_name,
                             start_date,
                             end_date,
                             index_name,
                             tmp_dirname)
    return df_wk


# Function to generate a Map Visualization
def generate_map(center_location=None) -> folium.Map:
    if center_location is None:
        center_location = [36.72017310567467, -4.479267597198487]

    map_folium = folium.Map(location=center_location, zoom_start=16,
                            tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                            attr="Google Satellite",
                            name="Google Satellite",
                            show=True
                            )
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
        "Google Maps": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        "Google Terrain": 'https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
        "Google Satellite Hybrid": 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        "Satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    }

    for layer in map_layers_dict:
        folium.TileLayer(
            tiles=map_layers_dict[layer],
            attr=layer,
            name=layer,
            show=False
        ).add_to(map_folium)

    folium.Marker(
        location=center_location,
        popup=st.session_state["geojson"],
    ).add_to(map_folium)

    return map_folium


def isolation_forest_outliers(df: pd.DataFrame):
    outliers_fraction = float(.01)
    scaler = StandardScaler()
    np_scaled = scaler.fit_transform(df.values.reshape(-1, 1))
    data = pd.DataFrame(np_scaled)
    # train isolation forest
    model = IsolationForest(contamination=outliers_fraction, n_estimators=200)  #
    model.fit(data)
    # plot outliers
    index = st.session_state['index']
    df['anomaly'] = model.predict(data)
    # visualization
    figure, ax = plt.subplots(figsize=(28, 10))
    plt.xticks(fontsize=24)
    plt.yticks(fontsize=24)
    a = df.loc[df['anomaly'] == -1, [index]]  # anomaly
    ax.plot(df.index, df[index], color='black', label='Normal')
    ax.scatter(a.index, a[index], color='red', label='Anomaly')
    plt.legend(fontsize=24)
    st.pyplot(figure)


def plot_specific_tif_from_minio(specific_date: str, outliers: bool):
    # cut TIF image with the selected geojson que and return this path to get the coordinates of the TIF
    band_cut_path = download_specific_tif_from_minio(st.session_state['geojson'],
                                                     specific_date,
                                                     st.session_state['index'])

    y_max, y_min, x_max, x_min = _get_corners_raster(band_cut_path)
    # Get Central point
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    center_location = [center_y, center_x]
    # Visualization in folium
    map_raster = generate_map(center_location)
    # If we found outliers we need to show this overlay image in the map
    if outliers:
        band = open_band(band_cut_path)
        band_n = normalize_band(band)
        cmap = cm.get_cmap('YlGnBu')
        # fit bounds rasters
        ImageOverlay(
            image=band_n,
            bounds=[[y_min, x_min], [y_max, x_max]],
            opacity=0.8,
            colormap=cmap,
            show=True,
            name=st.session_state["index"]).add_to(map_raster)

        # CONVERT TCI BAND TO RGB PNG FORMAT
        sample_tci_rgb_path = download_specific_tif_from_minio(st.session_state['geojson'],
                                                               specific_date,
                                                               'tci')
        index_image = read_rgb_image(sample_tci_rgb_path)
        cmap = cm.get_cmap("viridis", 7)
        ImageOverlay(
            image=index_image,
            bounds=[[y_min, x_min], [y_max, x_max]],
            opacity=0.8,
            colormap=cmap,
            name="True color",
            show=False
        ).add_to(map_raster)
    folium.LayerControl().add_to(map_raster)
    folium_static(map_raster, height=500, width=700)
    return band_cut_path


# RENDERING CODE
home = st.empty()
with home.container():
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
        the University of Malaga (Teatinos).

        This application has been designed by [Khaos research group](https://khaos.uma.es).
        """
    with home2:
        map_static = generate_map()
        folium_static(map_static, height=500, width=700)

# GENERATE FORM
with st.sidebar.form(key="my_form"):
    list_geojson = ['Choose Zone', 'Teatinos', 'Bulevar', 'Campo de futbol', 'Jardin Botanico']
    list_index = ['Choose Index', 'ndvi', 'tci', 'ri', 'cri1', 'bri', 'classifier', 'moisture',
                  'evi', 'osavi', 'evi2', 'ndre', 'ndyi', 'bri', 'ndsi', 'ndwi', 'mndwi', 'bsi']
    st.session_state["geojson"] = st.selectbox(
        'Which place do you want to study?',
        list_geojson
    )
    st.session_state["index"] = st.selectbox(
        'Which index do you want to study?',
        list_index
    )

    submit_button = st.form_submit_button(label="Detect Outliers", help="Execute Outliers Detection")

# SUBMIT BUTTON
if submit_button:
    if st.session_state["geojson"] == 'Choose Zone' or st.session_state["index"] == 'Choose Index':
        st.warning("WARNING: Please enter the required fields", icon="⚠️")
    else:
        with st.spinner('Outlier Detection Wait for it...'):
            # if everything goes correctly remove home page and execute workflow
            home.empty()
            # Create a temp folder to save results
            with tempfile.TemporaryDirectory() as tmp_dirname:
                print('created temporary directory', tmp_dirname)

            # execute workflow
            dataframe = _execute_complete_workflow(st.session_state["geojson"],
                                                   st.session_state["start_date"],
                                                   st.session_state["end_date"],
                                                   st.session_state["index"],
                                                   tmp_dirname)
            tempfile.TemporaryDirectory().cleanup()
            # First Detect Outliers OUTLIER DETECTION
            column = dataframe[st.session_state['index']]
            n = len(column)
            outlier_date = dataframe.index
            window_percentage = 5
            k = int(len(column) * (window_percentage / 100))
            get_bands = lambda data: (np.mean(data) + 2.5 * np.std(data), np.mean(data) - 2.5 * np.std(data))
            # get_bands = lambda data: (np.mean(data) + np.nanquantile(data, 0.98), np.mean(data) - np.nanquantile(data, 0.98))
            bands = [get_bands(column[range(0 if i - k < 0 else i - k, i + k if i + k < n else n)]) for i in
                     range(0, n)]
            upper_detection, lower_detection = zip(*bands)
            # compute local outliers
            anomalies = (column > upper_detection) | (
                    column < lower_detection)

            # If outlier exist download last TIF outlier if not, download the last TIF os the time series
            col1, col2 = st.columns(2)
            if np.any(anomalies):
                # if outliers, download the TIF from this date to generate center map and show index image
                last_outlier_date = str(outlier_date[anomalies][0])
                number_of_outliers = len(outlier_date[anomalies])
                with col1:
                    st.write('#### Time Series Visualization')
                    st.line_chart(dataframe, height=280)
                    st.error('We detect ' + str(
                        number_of_outliers) + ' outliers. The last one was: ' + last_outlier_date,
                             icon="🚨")
                    st.write("##### Time Series Outlier Detection")

                    # PLOT TIME SERIES DETECTION
                    fig = plt.figure(figsize=(28, 10))
                    plt.xticks(fontsize=24)
                    plt.yticks(fontsize=24)
                    plt.plot(outlier_date, column, 'k', label=st.session_state['index'])
                    plt.plot(outlier_date, upper_detection, 'r-', label='Bands',
                             alpha=0.5)
                    plt.plot(outlier_date, lower_detection, 'r-', alpha=0.5)
                    plt.plot(outlier_date[anomalies],
                             column[anomalies], 'ro',
                             label='Anomalies')
                    plt.fill_between(outlier_date, upper_detection,
                                     lower_detection,
                                     facecolor='red', alpha=0.1)
                    plt.legend(fontsize=24)
                    st.pyplot(fig)
                    # ANOTHER DETECTION METHOD
                    isolation_forest_outliers(dataframe)
                with col2:
                    st.write("#### Map Visualization of " + st.session_state["geojson"])
                    # Show outliers in map
                    sample_band_cut_path = plot_specific_tif_from_minio(last_outlier_date, outliers=True)
                    # Explanation of the results
                    with st.expander("Get More Information"):
                        "###### Statistical Information"
                        st.write("The last outlier was the day: " + last_outlier_date)
                        st.write('Number of outliers: ' + str(number_of_outliers))
                        "###### Download Image"
                        st.write(
                            "You can download the index of the last outlier found in the time series analysis in the "
                            "button below: ")

                        # Load selected file
                        with open(sample_band_cut_path, 'rb') as f:
                            s = f.read()
                        download_button_str = download_button(s, sample_band_cut_path, f'Click here to download {st.session_state["index"]}')
                        st.markdown(download_button_str, unsafe_allow_html=True)
                        st.write("If you want to obtain more information about yo can go to: "
                                 "*https://khaos.uma.es/green-senti/explore* ")

            # if not outliers we download the last TIF in time series to generate the center map
            else:
                with col1:
                    st.write('#### Time Series Visualization')
                    st.line_chart(dataframe, height=280)
                    st.write("##### Time Series Outlier Detection")
                    st.info(
                        "Fortunately, no anomaly has been found in this area of " + st.session_state['geojson'] +
                        " for the selected index:  " + st.session_state['index'], icon="ℹ️")
                with col2:
                    st.write("#### Map Visualization of " + st.session_state["geojson"])
                    last_date_time_series = str(dataframe.index[0])
                    # cut TIF image with the selected geojson and get the coordinates of the TIF
                    sample_band_cut_path = plot_specific_tif_from_minio(last_date_time_series, outliers=False)

        # DELETE TEMPORARY FOLDER AND ALL ITS CONTENTS
        if os.path.exists(tmp_dirname):
            shutil.rmtree(tmp_dirname)
