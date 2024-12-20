import pandas as pd
import numpy as np
import requests
import aiohttp
import os
from dotenv import load_dotenv
from sklearn.linear_model import LinearRegression

dotenv_path = '.env'
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


API_KEY = os.getenv('API_KEY')
UNITS = os.getenv('UNITS')

# Определим функцию для анализа погоды в городе
def city_weather_report(data: pd.DataFrame) -> dict:
    """
    data: pd.Dataframe with DatetimeIndex, containing columns `city`,
          'temperature', 'season' with data for one city

    return: dict with results, containing keys and values shown below
     {
        'city': str (name of city),
        'avg': float (average temperature for all period in data),
        'min': float (min temperature for all period in data),
        'max': float (max temperature for all period in data),
        'anomal_values': pd.Series (series of values with anomal temperature),
        'season_profile_roll30': dict {'winter_avg': float,
                                       'winter_std': float,
                                       'spring_avg': float,
                                       'spring_std': float,
                                       'summer_avg': float,
                                       'summer_std': float,
                                       'autumn_avg': float,
                                       'autumn_std': float
                                       }
         (average values and std of 30-day rolling mean temperature in every
          season),
        'season_profile': dict {'winter_avg': float,
                                'winter_std': float,
                                'spring_avg': float,
                                'spring_std': float,
                                'summer_avg': float,
                                'summer_std': float,
                                'autumn_avg': float,
                                'autumn_std': float
                                }
         (average values and std of current temperature in every season),
         'trend': float (value of linear regression coefficient).
    }
    Anomalistic values are out of range: 30-day rolling mean ±2σ.
    """

    city_df = data.copy()
    city_name = city_df.iloc[0, 0]
    # создадим столбец со скользящим средним
    city_df['mean_30'] = city_df['temperature'].rolling(30).mean()
    # вычислим столбец со скользящей средней дисперсией
    city_df['sigma_30'] = city_df['temperature'].rolling(30).std()

    # Вычислим среднее, минимум и максимум за всё время
    avg_tmp = round(city_df['temperature'].mean(), 2)
    min_tmp = round(city_df['temperature'].min(), 2)
    max_tmp = round(city_df['temperature'].max(), 2)

    # Выделим аномальные значения
    anomal_values = city_df[
        (city_df['temperature'] > (city_df['mean_30'] + 2 * city_df['sigma_30'])) |
        (city_df['temperature'] < (city_df['mean_30'] - 2 * city_df['sigma_30']))
        ]['temperature'].copy()

    # Вычислим сезонные статистики
    # Для 30-дневных скользящих средних
    season_data_roll30 = city_df.groupby(
        ['season'])['mean_30'].agg(['mean', 'std'])
    # Для текущих значений температуры
    season_data = city_df.groupby(
        ['season'])['temperature'].agg(['mean', 'std'])

    # Заполним словари сезонными статистиками
    # По скользящему среднему
    season_profile_roll30 = {
        'winter_avg': round(season_data_roll30['mean']['winter'], 2),
        'winter_std': round(season_data_roll30['std']['winter'] , 2),
        'spring_avg': round(season_data_roll30['mean']['spring'], 2),
        'spring_std': round(season_data_roll30['std']['spring'] , 2),
        'summer_avg': round(season_data_roll30['mean']['summer'], 2),
        'summer_std': round(season_data_roll30['std']['summer'] , 2),
        'autumn_avg': round(season_data_roll30['mean']['autumn'], 2),
        'autumn_std': round(season_data_roll30['std']['autumn'] , 2)
    }

    # По текущим значениям
    season_profile = {
        'winter_avg': round(season_data['mean']['winter'], 2),
        'winter_std': round(season_data['std']['winter'] , 2),
        'spring_avg': round(season_data['mean']['spring'], 2),
        'spring_std': round(season_data['std']['spring'] , 2),
        'summer_avg': round(season_data['mean']['summer'], 2),
        'summer_std': round(season_data['std']['summer'] , 2),
        'autumn_avg': round(season_data['mean']['autumn'], 2),
        'autumn_std': round(season_data['std']['autumn'] , 2)
    }

    # Обучим линейную регрессию для выявления тренда
    X = np.array([i for i in range(1, city_df.shape[0] + 1)]).reshape(-1, 1)
    y = city_df['temperature']
    lr = LinearRegression().fit(X, y)

    # Определим коэффициент
    trend = round(lr.coef_[0], 4)

    report = {
        'city': city_name,
        'avg': avg_tmp,
        'min': min_tmp,
        'max': max_tmp,
        'anomal_values': anomal_values,
        'season_profile_roll30': season_profile_roll30,
        'season_profile': season_profile,
        'trend': trend
    }

    return report


# Функция для определения текущей температуры в городе
def current_temperature(city: str) -> float:
    """
    city: city name

    return current temperature in city using openweathermap data
    """

    # Получим широту и долготу
    geo_info = requests.get(
      f'http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={API_KEY}'
    ).json()
    lat = geo_info[0]['lat']
    lon = geo_info[0]['lon']

    # Запросим текущие данные о погоде
    cur_weather = requests.get(
      f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units={UNITS}&appid={API_KEY}'
     ).json()

    # Вернём текущую температуру
    cur_temp = cur_weather['main']['temp']

    return cur_temp


def is_anomalistic(season: str, report: dict) -> bool:
    """
    season: name of season,
    report: dict with report information

    return True if current temperature in city is out of range: mean ±2σ
           (for the city and current season)
    """

    mean = report['season_profile'][season+'_avg']
    sigma = report['season_profile'][season+'_std']
    temperature = current_temperature(report['city'])
    if  temperature > mean + 2 * sigma or temperature < mean - 2 * sigma:
        return True
    else:
        return False


# Асинхронная функция для получения данных из API
async def async_current_temperature(city: str) -> float:
    """
    city: city name

    return current temperature in city using openweathermap data
    """
    # Получим url для широты и долготы
    geo_info_url = \
    f'http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={API_KEY}'

    async with aiohttp.ClientSession() as session:
        async with session.get(geo_info_url) as geo_response:
            geo_info = await geo_response.json()
            lat = geo_info[0]['lat']
            lon = geo_info[0]['lon']

        # Получим url для текущих данных о погоде
        weather_url = \
        f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units={UNITS}&appid={API_KEY}'

        async with session.get(weather_url) as weather_response:
            cur_weather = await weather_response.json()

    # Вернём текущую температуру
    cur_temp = cur_weather['main']['temp']

    return cur_temp


# Асинхронная функция для анализа температуры на аномальность
async def async_is_anomalistic(season: str, report: dict) -> bool:
    """
    season: name of season,
    report: dict with report information

    return True if current temperature in city is out of range: mean ±2σ
           (for the city and current season)
    """

    mean = report['season_profile'][season+'_avg']
    sigma = report['season_profile'][season+'_std']
    temperature = await async_current_temperature(report['city'])
    if temperature > mean + 2 * sigma or temperature < mean - 2 * sigma:
        return True
    else:
        return False
