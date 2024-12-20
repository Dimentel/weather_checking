import time
from concurrent.futures import ProcessPoolExecutor
from  axiluary_functions import *

dotenv_path = '.env'
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

DATA_PATH = os.getenv('DATA_PATH')

# Загрузим датасет
df = pd.read_csv(os.path.join(DATA_PATH,'temperature_data.csv'))

# Преобразуем тип данных в столбце с датой и временем
df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d')

# Отсортируем по дате
df = df.sort_values(by='timestamp')

# Cтолбец с датой и временем используем для индесации данных
df.set_index(['timestamp'], inplace=True)


# Параллельное выполнение
def make_reports():
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = [res for res in executor.map(city_weather_report, chunks)]
    return pd.DataFrame(results)


# Запустим параллельное выполнение
if __name__ == '__main__':
    start = time.time()
    # Разобъём датасет на части по городам
    chunks = [df[df['city'] == city] for city in df['city'].unique()]
    reports = make_reports()
    print(f'Выполнение завершено за {time.time() - start: .3f} с')
    print(pd.DataFrame(reports).info())