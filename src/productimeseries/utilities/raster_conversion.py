from os.path import join
from typing import Tuple
import numpy as np
import pyproj
import rasterio
from shapely.geometry import Point
from shapely.ops import transform
from src.productimeseries.utilities.raster import _read_raster, _get_kwargs_raster

def _get_corners_raster(
        band_path: str,
) -> Tuple[float, float, float, float]:
    """
    Given a band path, it is opened with rasterio and its bounds are extracted with shapely's transform.

    Returns the raster's corner latitudes and longitudes, along with the band's size.
    """
    final_crs = pyproj.CRS("epsg:4326")

    band = _read_raster(band_path)
    kwargs = _get_kwargs_raster(band_path)
    init_crs = kwargs["crs"]

    project = pyproj.Transformer.from_crs(init_crs, final_crs, always_xy=True).transform

    tl_lon, tl_lat = transform(project, Point(kwargs["transform"] * (0, 0))).bounds[0:2]

    tr_lon, tr_lat = transform(
        project, Point(kwargs["transform"] * (band.shape[2] - 1, 0))
    ).bounds[0:2]

    bl_lon, bl_lat = transform(
        project, Point(kwargs["transform"] * (0, band.shape[1] - 1))
    ).bounds[0:2]

    br_lon, br_lat = transform(
        project, Point(kwargs["transform"] * (band.shape[2] - 1, band.shape[1] - 1))
    ).bounds[0:2]

    return (
        tl_lat,  # ymax
        bl_lat,  # ymin
        tl_lon,  # xmax
        br_lon,  # xmin
    )


def open_band(band_file: str, channel: int = 1):
    with rasterio.open(band_file) as bf:
        # kwargs = bf.meta
        # n_channels = kwargs["count"]
        BAND = bf.read(channel).astype(np.float32)
        BAND[BAND == bf.nodata] = np.nan  # Convert NoData to NaN
    return BAND


def normalize_band(band):
    # mask_nan = band[np.isnan(band)]
    mask_nan = np.ma.array(band, mask=np.isnan(band))
    maxi = np.nanmax(mask_nan)
    mini = np.nanmin(mask_nan)
    normalized_band = (band - mini) / (maxi - mini)
    return normalized_band


def read_rgb_image(band_path: str):
    src = rasterio.open(band_path)
    rgb_src = src.read()
    rgb = normalize_band(rgb_src)
    rgb_without_nan = np.nan_to_num(rgb)
    sum_rgb = np.sum(rgb_without_nan, axis=0)
    mask = np.where(sum_rgb == 0, 0, 1)
    rgb_t = np.transpose(rgb_without_nan, (1, 2, 0))
    index_image = np.dstack((rgb_t, mask))
    return index_image
