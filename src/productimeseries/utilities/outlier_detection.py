from src.productimeseries.config import settings
from src.productimeseries.mongo import MongoConnection
from datetime import datetime as dt
import pandas as pd


def find_outliers_iqr(df: pd.DataFrame):
    q1 = df.quantile(0.25)
    q3 = df.quantile(0.75)
    iqr = q3 - q1
    return df[((df < (q1 - 1.5 * iqr)) | (df > (q3 + 1.5 * iqr)))]




# if __name__ == '__main__':
#     geojson_files = '/home/sandro/PycharmProjects/teatinos.geojson'
#     index = 'ndvi'
#     start_date = datetime.strptime('2018-02-01', '%Y-%m-%d')
#     final_date = datetime.strptime('2018-05-24', '%Y-%m-%d')
#
#     get_time_series_from_products_mongo(geojson_files, start_date, final_date, index)
