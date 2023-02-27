from pathlib import Path

from pydantic import BaseSettings


class _Settings(BaseSettings):
    # Mongo-related settings
    MONGO_HOST: str = "192.168.219.5"
    MONGO_PORT: int = 27017
    MONGO_USERNAME: str = "root"
    MONGO_PASSWORD: str = "kha0sd3v"
    MONGO_DB: str = "products_database"
    MONGO_PRODUCTS_COLLECTION: str = "products_collection"
    MONGO_TIMESERIES_COLLECTION: str = 'timeseries_collection'
    MONGO_COMPOSITES_COLLECTION: str = "composite_collection"

    # Minio-related settings
    MINIO_HOST: str = '192.168.219.2'
    MINIO_PORT: str = '9000'
    MINIO_ACCESS_KEY: str = "etc-uma"
    MINIO_SECRET_KEY: str = "7bL2yzauxLrKFu3A"
    MINIO_BUCKET_NAME_PRODUCTS: str = 'etc-products'
    MINIO_BUCKET_NAME_COMPOSITES: str = None
    MINIO_BUCKET_NAME_ASTER: str = None
    MINIO_BUCKET_NAME_DEM: str = None
    MINIO_BUCKET_DATASETS: str = None
    MINIO_BUCKET_MODELS: str = None
    MINIO_BUCKET_CLASSIFICATIONS: str = None
    MINIO_BUCKET_TILE_METADATA: str = None
    MINIO_BUCKET_GEOJSONS: str = None
    MINIO_DATA_FOLDER_NAME: str = None


    # Sentinel download API
    SENTINEL_HOST: str = "https://scihub.copernicus.eu/dhus"
    SENTINEL_USERNAME: str = ""
    SENTINEL_PASSWORD: str = ""

    # Temporal directory
    TMP_DIR: str = "/home/sandro/PycharmProjects/tmp"
    TMP_DIR_CUT: str = "/home/sandro/PycharmProjects/tmp/cut"
    TMP_DIR_PNG: str = "/home/sandro/PycharmProjects/tmp/png"
    TMP_DIR_GEOJSON: str = "/home/sandro/PycharmProjects/geojson"


    # Directory containing validated datasets (.kmz or .geojson)
    DB_DIR: str = "/home/sandro/PycharmProjects/geojson"

    # For running in a distributed environment
    DASK_CLUSTER_IP: str = "0.0.0.0.0:0000"

    # Dates used for each season
    SPRING_START: str = "2001-12-31"
    SPRING_END: str = "2001-12-31"
    SUMMER_START: str = "2001-12-31"
    SUMMER_END: str = "2001-12-31"
    AUTUMN_START: str = "2001-12-31"
    AUTUMN_END: str = "2001-12-31"

    # Product filtering parameters
    MAX_CLOUD: float = 1.0

    # Model folders in MinIO
    LAND_COVER_MODEL_FOLDER: str = ""
    OPEN_FOREST_MODEL_FOLDER: str = ""
    DENSE_FOREST_MODEL_FOLDER: str = ""

    # Composite-related parameters
    MAX_PRODUCTS_COMPOSITE: int = 1

    class Config:
        env_file = ".env"
        file_path = Path(env_file)
        if not file_path.is_file():
            print("⚠️ `.env` not found in current directory")
            print("⚙️ Loading settings from environment")
        else:
            print(f"⚙️ Loading settings from dotenv @ {file_path.absolute()}")


settings = _Settings()
