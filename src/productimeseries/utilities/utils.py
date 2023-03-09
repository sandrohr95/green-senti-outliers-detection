from sentinelsat.sentinel import read_geojson
from datetime import datetime
from pymongo.cursor import Cursor
from src.productimeseries.minio import MinioConnection
from pathlib import Path
from src.productimeseries.utilities.geometries import _get_mgrs_from_geometry
import calendar
import json
from src.productimeseries.utilities.raster import _read_raster
from datetime import datetime as dt
from src.productimeseries.mongo import *
import os


def _group_polygons_by_tile(*geojson_files: str) -> dict:
    """
    Extracts coordinates of geometries from specific geojson files, then creates a mapping [Sentinel's tile -> List of geometries contained in that tile].
    """
    tiles = {}

    for geojson_file in geojson_files:
        geojson = read_geojson(geojson_file)
        print(f"Querying relevant tiles for {len(geojson['features'])} features")
        for feature in geojson["features"]:
            small_geojson = {"type": "FeatureCollection", "features": [feature]}
            geometry = small_geojson["features"][0]["geometry"]
            properties = small_geojson["features"][0]["properties"]
            intersection_tiles = _get_mgrs_from_geometry(geometry)
            for tile in intersection_tiles:
                if tile not in tiles:
                    tiles[tile] = []

                tiles[tile].append(
                    {
                        "geometry": geometry,
                        "properties": properties
                    }
                )
    return tiles


def get_products_by_tile_and_date(
        tile: str,
        mongo_collection: Collection,
        start_date: datetime,
        end_date: datetime,
        cloud_percentage=0.05
) -> Cursor:
    """
    Query to mongo for obtaining products filtered by tile, date and cloud percentage
    """
    product_metadata_cursor = mongo_collection.aggregate(
        [
            {
                "$project": {
                    "_id": 1,
                    "indexes": {
                        "$filter": {
                            "input": "$indexes",
                            "as": "index",
                            "cond": {
                                "$and": [
                                    {"$eq": ["$$index.mask.geojson", "teatinos"]},
                                    {"$eq": ["$$index.name", "cloud-mask"]},
                                    {"$lt": ["$$index.value", cloud_percentage]},
                                ]
                            },
                        }
                    },
                    "id": 1,
                    "title": 1,
                    "size": 1,
                    "date": 1,
                    "creationDate": 1,
                    "ingestionDate": 1,
                    "objectName": 1,
                }
            },
            {
                "$match": {
                    "indexes.0": {"$exists": True},
                    "title": {"$regex": f"_T{tile}_"},
                    "date": {
                        "$gte": start_date,
                        "$lte": end_date,
                    },
                }
            },
            {
                "$sort": {"date": -1}
            },
        ]
    )

    return product_metadata_cursor


def get_tile_from_geojson(geojson_path: str) -> str:
    """ From GJSON get TILES """
    tiles = _group_polygons_by_tile(geojson_path)
    list_tiles = list(tiles.keys())
    tile = list_tiles[0]
    return tile


def get_time_series_from_products_mongo(mongo_collection: Collection, name_geojson: str, index_name: str,
                                        start_date: str, end_date: str):
    """ Get time series index from specific geojson file and a range of dates
        by default we have processed Teatinos and Ejido
    """

    timeseries_metadata_cursor = mongo_collection.aggregate(
        [
            {
                "$match": {
                    'id_geojson': name_geojson,
                    index_name: {'$exists': True},
                    "date": {
                        "$gte": dt.strptime(str(start_date), '%Y-%m-%d'),
                        "$lte": dt.strptime(str(end_date), '%Y-%m-%d')},
                }
            },
            {
                "$sort": {"date": -1}
            },
        ]
    )

    return list(timeseries_metadata_cursor)


def _download_sample_band_from_product_list(
        sample_band_path: str, title: str, year: str, month: str, index: str, minio_client: MinioConnection
):
    """
    Having a list of products, download a sample sentinel band of the product.
    """
    minio_bucket_product = settings.MINIO_BUCKET_NAME_PRODUCTS
    # De esta forma nos traemos los recortes de teatinos
    sample_band_path_minio = str(Path(year, month, title, 'indexes', 'teatinos', index + '.tif'))
    minio_client.fget_object(minio_bucket_product, sample_band_path_minio, sample_band_path)


def get_products_by_tile_and_specific_date(
        tile: str,
        mongo_collection: Collection,
        specific_date: str
) -> Cursor:
    """
    Query to mongo for obtaining products filtered by tile, date and then query MiniO to obtain the required TIF to plot it in the map
    """
    product_cursor = mongo_collection.aggregate(
        [
            {
                "$match": {
                    "indexes.0": {"$exists": True},
                    "title": {"$regex": f"_T{tile}_"},
                    "$expr": {
                        "$eq": [
                            specific_date,
                            {
                                "$dateToString": {
                                    "date": "$date",
                                    "format": "%Y-%m-%d"
                                }
                            }
                        ]
                    }
                }
            }
        ])

    return product_cursor


def _cut_specific_tif(path_geojson: str, sample_band_path: str, sample_band_cut_path: str):
    """
        Cut Raster from specific geometry
    """
    with open(path_geojson) as f:
        mask_geometry = json.load(f)
        features = mask_geometry['features']
        geometry = features[0]['geometry']
    raster_result = _read_raster(band_path=sample_band_path,
                                 mask_geometry=geometry,
                                 path_to_disk=sample_band_cut_path)
    return raster_result


def get_products_id_from_mongo(mongo_collection: Collection, start_date: str, end_date: str, tile: str):
    """
        Get products ids from MongoDB in products_collection
    """
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    cursor_products = get_products_by_tile_and_date(tile, mongo_collection, start_date, end_date)
    list_products = list(cursor_products)
    return list_products


def download_specific_tif_from_minio(name_geojson: str, specific_date: str, index: str):
    """
        Download specific TIF from MiniO to show in the Map
    """
    # From GJSON get TILES
    path_geojson = str(Path(settings.DB_DIR, name_geojson + '.geojson'))
    tile = get_tile_from_geojson(path_geojson)

    # Get products ids from MongoDB in products_collection
    specific_date = specific_date.split(' ')[0]
    mongo_client = MongoConnection()
    mongo_collection = mongo_client.get_collection_object()
    cursor_products = get_products_by_tile_and_specific_date(tile, mongo_collection, specific_date)
    list_products = list(cursor_products)
    product = list_products[0]
    # Get product information
    title = product['title']
    date_product = title.split('_')[2].split('T')[0]
    year = date_product[:4]
    month_name = calendar.month_name[int(date_product[4:6])]

    # Download TIF in local from
    minio_client = MinioConnection()
    sample_band_path = str(Path(settings.TMP_DIR, title + '_' + index))
    _download_sample_band_from_product_list(sample_band_path, title, year, month_name, index, minio_client)

    # We read and cut out the bands for each of the products.
    sample_band_cut_path = str(Path(settings.TMP_DIR, title + '_' + name_geojson + '_' + index + '.tif'))
    _cut_specific_tif(path_geojson, sample_band_path, sample_band_cut_path)

    # Remove product form tmp folder
    if os.path.exists(sample_band_path):
        os.remove(sample_band_path)

    return sample_band_cut_path
