# This is a sample Python script.
from src.productimeseries.utilities.raster import _read_raster
from src.productimeseries.utilities.utils import _group_polygons_by_tile, get_products_by_tile_and_date, \
    _download_sample_band_from_product_list, _cut_specific_tif, get_products_id_from_mongo, \
    get_time_series_from_products_mongo
from src.productimeseries.mongo import *
from src.productimeseries.minio import *
from sentinelsat.sentinel import read_geojson
import json
from datetime import datetime
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import calendar
from pathlib import Path


def main(geojson_path: str, start_date: str, end_date: str, index: str):
    """
    Cada vez que un usuario haga una petición se ejecutará el siguiente flujo de trabajo:
    Consultaremos las coleccions de MongoDB (products_collection y timeseries_collection)
    1. Si encontramos nuevos actualizamos la colección de time series. Para ello:
       1.A) Descargamos el product de minio
       1.B) Lo recortamos con el GeoJson correspondiente
       1.C) Calculamos la media del índice
       1.D) Actualizamos la serie temporal en timeseries_collection
       1.E) Devolvemos la serie temporal completa para mostrarla en Streamlit
    2. Si no encontramos actualización en los datos:
        1.E) Devolvemos la serie temporal completa para mostrarla en Streamlit

    Args:
        geojson_path:
        start_date:
        end_date:
        index:

    Returns:

    """

    """ From GJSON get TILES """
    tiles = _group_polygons_by_tile(geojson_path)
    list_tiles = list(tiles.keys())
    tile = list_tiles[0]

    """ Compare MongoDB collections products_collection and timeseries_collection"""

    """ Get products ids from MongoDB in products_collection """
    mongo_client = MongoConnection()
    products_collection = mongo_client.get_collection_object()
    list_products = get_products_id_from_mongo(products_collection, start_date, end_date, tile)
    last_product = list_products[0]['date']
    print(last_product)

    """ Get the last time series """
    # Establish connection with timeseries_collection
    mongo_client.set_collection(settings.MONGO_TIMESERIES_COLLECTION)
    timeseries_collection = mongo_client.get_collection_object()
    # From geojson path take the name of the geojson file. Ex: Boulevard
    name_geojson = geojson_path.split('/')[-1].split('.')[0]
    df_ts = get_time_series_from_products_mongo(timeseries_collection, name_geojson, index, start_date, end_date)
    last_ts = df_ts.index[0].to_pydatetime()

    """ Compare datetime """
    if last_product > last_ts:
        # We need to download and process the products than are not in timeseries_collection yet
        for product in list_products:
            print(product['date'])
            title = product['title']
            date_product = product['date']
            year = date_product.year
            print(year)
            month = date_product.month
            print(month)
            day = date_product.day
            print(day)


    # Download products in local directory (The user will pass by parameters the index to be downloaded)
    minio_client = MinioConnection()

    #
    # for product in list_products:
    #     title = product['title']
    #     date_product = title.split('_')[2].split('T')[0]
    #     year = date_product[:4]
    #     month = date_product[4:6]
    #     day = date_product[6:8]
    #     month_name = calendar.month_name[int(date_product[4:6])]
    #
    #     try:
    #         # Define the zone to be cut
    #         id_geojson = geojson_path.split('/')[-1].split('.')[0]
    #         # Download TIF in local
    #         sample_band_path = str(Path(settings.TMP_DIR, title + '_' + index + '.tif'))
    #         _download_sample_band_from_product_list(sample_band_path, title, year, month_name, index, minio_client)
    #         # We read and cut out the bands for each of the products.
    #         sample_band_cut_path = str(Path(settings.TMP_DIR_CUT, title + '_' + id_geojson + '_' + index + '.tif'))
    #         raster_result = _cut_specific_tif(geojson_path, sample_band_path, sample_band_cut_path)
    #         if np.isnan(raster_result).all():
    #             print("This product only contains nan values for this index")
    #         else:
    #             # Calculate the mean of the index for each product
    #             raster_result_mean = np.nanmean(raster_result)
    #             date_mongo = datetime.strptime(year + '-' + month + '-' + day, '%Y-%m-%d')
    #
    #             """ Insert data in this collection. Example structure:
    #                     _id(mongo): value
    #                     id_geojson: value
    #                     date:value
    #                     index: value
    #             """
    #
    #             """ We need to check if exists this ranges of dates. If exists update it if not, insert new one
    #                 - Creates a new document if no documents match the filter.
    #                 - Updates a single document that matches the filter.
    #             """
    #             query = {'id_geojson': id_geojson, 'date': date_mongo}
    #             new_values = {"$set": {index: float(raster_result_mean)}}
    #             timeseries_collection.update_one(query, new_values, upsert=True)
    #     except:
    #         print("Something went wrong in the Download")


if __name__ == '__main__':
    path_geojson = "/home/sandro/PycharmProjects/geojson"
    geojson_files = [path_geojson + '/jardin.geojson']  # , path_geojson+'/Campo de futbol.geojson'
    list_index = ['ndvi']  # , 'ndvi', 'tci', 'ri', 'cri1', 'bri', 'mndwi'
    # main(geojson_files, "2018-03-26", "2022-07-28", 'ndvi')
    for ind in list_index:
        for g in geojson_files:
            main(g, "2018-03-26", "2020-02-13", ind)
