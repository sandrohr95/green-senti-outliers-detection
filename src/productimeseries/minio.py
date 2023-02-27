from minio import Minio
from src.productimeseries.config import settings


class MinioConnection(Minio):
    "A class including handled MinIO methods"

    def __init__(self, host=settings.MINIO_HOST, port=settings.MINIO_PORT, access_key=settings.MINIO_ACCESS_KEY,
                 secret_key=settings.MINIO_SECRET_KEY):
        super().__init__(
            endpoint=f"{host}:{port}",
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )

    # @retry(n_retries=1, delay=10)
    def fget_object(self, *args, **kwargs):
        "Handled version of the fget_object Minio's method"
        super().fget_object(*args, **kwargs)

    # @retry(n_retries=100, delay=60)
    def fput_object(self, *args, **kwargs):
        "Handled version of the fput_object Minio's method"
        super().fput_object(*args, **kwargs)
