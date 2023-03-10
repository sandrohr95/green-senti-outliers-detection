from src.productimeseries.utilities.utils import _download_sample_band_from_product_list, _cut_specific_tif, \
    get_products_id_from_mongo, \
    get_time_series_from_products_mongo, get_tile_from_geojson
from src.productimeseries.mongo import *
from src.productimeseries.minio import *
from datetime import datetime
import pandas as pd
import numpy as np
import os
import calendar
from pathlib import Path


def execute_workflow(geojson_name: str, start_date: str, end_date: str, index: str, tmp_dirname: str):
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

    """

    """ From GJSON get TILE """
    geojson_path = str(Path(settings.DB_DIR, geojson_name + '.geojson'))
    tile = get_tile_from_geojson(geojson_path)

    """ Compare MongoDB collections products_collection and timeseries_collection"""

    """ Get products ids from MongoDB in products_collection """
    mongo_client = MongoConnection()
    products_collection = mongo_client.get_collection_object()
    list_products = get_products_id_from_mongo(products_collection, start_date, end_date, tile)
    last_product = list_products[0]['date']
    # print(last_product)
    """ Get the last time series """
    # Establish connection with timeseries_collection
    mongo_client.set_collection(settings.MONGO_TIMESERIES_COLLECTION)
    timeseries_collection = mongo_client.get_collection_object()
    list_ts = get_time_series_from_products_mongo(timeseries_collection, geojson_name, index, start_date, end_date)
    # Si ese GeoJson aún no existe en MongoDB nos lo descargamos
    if len(list_ts) < 1:
        generate_time_series_from_products(geojson_path, geojson_name, index, list_products, timeseries_collection,
                                           tmp_dirname)

    # Si ya existe lo actualizamos
    else:
        last_ts = list_ts[0]['date']
        """ Compare datetime """
        if last_product > last_ts:
            # Take a sublist of products to update the timeseries_collection
            sublist_products = get_products_id_from_mongo(products_collection, last_ts.strftime("%Y-%m-%d"),
                                                          end_date, tile)
            print("We need to insert " + str(len(sublist_products)) + " products in time series collection")
            generate_time_series_from_products(geojson_path, geojson_name, index, sublist_products,
                                               timeseries_collection, tmp_dirname)

    final_ts_list = get_time_series_from_products_mongo(timeseries_collection, geojson_name, index,
                                                        start_date, end_date)
    list_index = []
    list_dates = []
    for ts in final_ts_list:
        list_index.append(ts[index])
        list_dates.append(ts['date'])
    dataframe = pd.DataFrame(list_index, columns=[index], index=list_dates)
    return dataframe


def generate_time_series_from_products(geojson_path, geojson_name, index, list_products,
                                       timeseries_collection, tmp_dirname):
    """
            From products in MiniO download TIF images and calculate the mean of the index to insert in
            Time Series Collection
    """
    # create a tmp directory to save TIF from products
    # if not os.path.exists(settings.TMP_DIR):
    #     os.mkdir(settings.TMP_DIR)

    # Download products in local directory (The user will pass by parameters the index to be downloaded)
    minio_client = MinioConnection()
    # We need to download and process the products than are not in timeseries_collection yet
    for product in list_products:
        title = product['title']
        date_product = product['date']
        year = str(date_product.year)
        month = date_product.month
        day = str(date_product.day)
        month_name = calendar.month_name[month]
        try:
            # Download TIF in local
            sample_band_path = str(Path(tmp_dirname, title + '_' + index + '.tif'))
            _download_sample_band_from_product_list(sample_band_path, title, year, month_name, index, minio_client)
            # We read and cut out the bands for each of the products.
            sample_band_cut_path = str(
                Path(tmp_dirname, title + '_' + geojson_name + '_' + index + '.tif'))
            raster_result = _cut_specific_tif(geojson_path, sample_band_path, sample_band_cut_path)
            if np.isnan(raster_result).all():
                print("This product only contains nan values for this index")
            else:
                # Calculate the mean of the index for each product
                raster_result_mean = np.nanmean(raster_result)

                date_mongo = datetime.strptime(year + '-' + str(month) + '-' + day, '%Y-%m-%d')

                """ Insert data in this collection. Example structure:
                        _id(mongo): value
                        id_geojson: value
                        date:value
                        index: value
                """

                """ We need to check if exists this ranges of dates. If exists update it if not, insert new one
                    - Creates a new document if no documents match the filter.
                    - Updates a single document that matches the filter.
                """
                query = {'id_geojson': geojson_name, 'date': date_mongo}
                new_values = {"$set": {index: float(raster_result_mean)}}
                timeseries_collection.update_one(query, new_values, upsert=True)

                """
                Finally we need to remove this Tail from local
                """
                if os.path.exists(sample_band_path):
                    os.remove(sample_band_path)
                if os.path.exists(sample_band_cut_path):
                    os.remove(sample_band_cut_path)
        except Exception as err:
            print(f"Unexpected {err=}, {type(err)=}")
            print("Something went wrong in the Download")


# def delete_documents_mongo(id_geojson):
#     mongo_client = MongoConnection()
#     # Establish connection with timeseries_collection
#     mongo_client.set_collection(settings.MONGO_TIMESERIES_COLLECTION)
#     timeseries_collection = mongo_client.get_collection_object()
#     timeseries_collection.delete_many({'id_geojson': id_geojson})


if __name__ == '__main__':
    # delete_documents_mongo("Campo de futbol")

    geojson_files = ['Campo de futbol', 'Jardin Botanico', 'Bulevar']  # , path_geojson+'/Campo de futbol.geojson'
    indexes = ['ndvi', 'tci', 'ri', 'cri1', 'bri', 'classifier', 'moisture',
               'evi', 'osavi', 'evi2', 'ndre', 'ndyi', 'bri', 'ndsi', 'ndwi', 'mndwi', 'bsi']

    for g in geojson_files:
        for i in indexes:
            execute_workflow(g, "2018-03-26", "2029-02-19", i)
    # df.sort_index(inplace=True)
    # print(df)
    # df.to_csv("/home/sandro/PycharmProjects/ndvi.csv")
