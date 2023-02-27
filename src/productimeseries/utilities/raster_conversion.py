from os.path import join
from typing import Tuple
import numpy as np
import pyproj
import rasterio
from shapely.geometry import Point
from shapely.ops import transform
from matplotlib import pyplot as plt
from matplotlib import colors
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


def save_band_as_png(band_name, band_file: str, output_directory: str):
    """ Save band in .PNG format.

    :param band_name: Band name.
    :param band_file: Band filename in jp2.
    :param output_directory: Output directory path.
    """
    with rasterio.open(band_file) as bf:
        BAND = bf.read(1).astype(np.float32)
        BAND[BAND == bf.nodata] = np.nan  # Convert NoData to NaN

    # plot image
    fig, ax = plt.subplots(figsize=plt.figaspect(BAND), frameon=False)
    fig.subplots_adjust(0, 0, 1, 1)

    # export to file
    if band_name.lower() == 'ndvi':
        vmin, vmax = np.nanpercentile(BAND, (1, 99))  # 1-99% contrast stretch
        ax.imshow(BAND, cmap='RdYlGn', vmin=vmin, vmax=vmax)
    elif band_name.lower() == 'classifier':
        colors_list = ["white", "wheat", "green", "blue"]
        cmap = colors.ListedColormap(colors_list)
        vmin, vmax = np.nanpercentile(BAND, (1, 99))  # 1-99% contrast stretch
        ax.imshow(BAND, cmap=cmap, vmin=vmin, vmax=vmax)
    else:
        ax.imshow(BAND)

    fig.savefig(output_directory, dpi=120)

    # close figure to avoid overflow
    plt.close(fig)
