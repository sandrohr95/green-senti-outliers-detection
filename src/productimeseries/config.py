from pathlib import Path

from pydantic import BaseSettings


class _Settings(BaseSettings):
    # Mongo-related settings
    # Mongo-related settings
    MONGO_HOST: str = "0.0.0.0"
    MONGO_PORT: int = 27017
    MONGO_USERNAME: str = "user"
    MONGO_PASSWORD: str = "pass"
    MONGO_DB: str = "test"
    MONGO_PRODUCTS_COLLECTION: str = "test"
    MONGO_TIMESERIES_COLLECTION: str = 'test'

    # Minio-related settings
    MINIO_HOST: str = "0.0.0.0"
    MINIO_PORT: str = '9000'
    MINIO_ACCESS_KEY: str = "user"
    MINIO_SECRET_KEY: str = "pass"
    MINIO_BUCKET_NAME_PRODUCTS: str = 'test'
    MINIO_BUCKET_NAME_COMPOSITES: str = None

    # Temporal directory
    TMP_DIR: str = "./tmp"
    # Directory containing validated datasets (.kmz or .geojson)
    DB_DIR: str = "./geojson"

    class Config:
        env_file = ".env"
        file_path = Path(env_file)
        if not file_path.is_file():
            print("⚠️ `.env` not found in current directory")
            print("⚙️ Loading settings from environment")
        else:
            print(f"⚙️ Loading settings from dotenv @ {file_path.absolute()}")


settings = _Settings()
