# импортируем библиотеки
import time
import streamlit as st
import plotly.graph_objs as go
import matplotlib
from axiluary_functions import *

# Сопоставление месяцев с сезонами
month_to_season = {12: "winter", 1: "winter", 2: "winter",
                   3: "spring", 4: "spring", 5: "spring",
                   6: "summer", 7: "summer", 8: "summer",
                   9: "autumn", 10: "autumn", 11: "autumn"}

st.title('Исследование погоды в различных городах')
st.subheader('Проверка текущей температуры на аномальность')

message, uploader = st.columns(2, vertical_alignment="bottom")
message.markdown('''Загрузите файл csv с данными о погоде в городах, с колонками `city`,
`timestamp`, `temperature`, `season`''')
uploaded_file = uploader.file_uploader("Выберите файл csv")
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    message, txt_input = st.columns(2, vertical_alignment="bottom")
    message.markdown('Укажите свой ключ к [API openweathermap](https://openweathermap.org/current)')
    API_KEY = txt_input.text_input("API KEY", type="password")

    if len(df['city']) > 0 and len(API_KEY) > 0:
        message, select = st.columns(2, vertical_alignment="bottom")
        message.markdown('Выберите город, для которого хотите получить анализ температуры')
        city = select.selectbox('Город', df['city'].unique())

        # Преобразуем тип данных в столбце с датой и временем
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d')

        # Отсортируем по дате
        df = df.sort_values(by='timestamp')

        # Cтолбец с датой и временем используем для индесации данных
        df.set_index(['timestamp'], inplace=True)

        report = city_weather_report(df[df['city'] == city])

        # Выберем единицы: температура в градусах Цельсия, ветер в м/с
        UNITS = os.getenv('UNITS')

        # Посмотрим данные выбранного города. Выполним запрос координат
        geo_info = requests.get(
            f'http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={API_KEY}'
        ).json()

        if isinstance(geo_info, dict):
            st.error('Неверный API KEY')
        else:
            # Получим широту и долготу
            lat = geo_info[0]['lat']
            lon = geo_info[0]['lon']

            # Запросим текущие данные о погоде
            weather_data = requests.get(
                f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units={UNITS}&appid={API_KEY}'
            ).json()

            # Получим текущую температуру
            cur_temperature = weather_data['main']['temp']

            # Определим сезон
            season = month_to_season[time.gmtime().tm_mon]

            mean = report['season_profile'][season + '_avg']
            sigma = report['season_profile'][season + '_std']

            if cur_temperature > mean + 2 * sigma:
                frase = f'В городе {city} температура аномально высокая'
            elif cur_temperature < mean - 2 * sigma:
                frase = f'В городе {city} температура аномально низкая'
            elif cur_temperature > report['season_profile'][season+'_avg']:
                frase = f'В городе {city} температура выше среднего'
            elif cur_temperature < report['season_profile'][season+'_avg']:
                frase = f'В городе {city} температура ниже среднего'
            else:
                frase = f'В городе {city} температура средняя по сезону'

            metric, season_stat = st.columns(2, vertical_alignment="bottom")
            metric.metric(label=frase,
                      value=f"{cur_temperature} °C",
                      delta=f"отклонение от среднего {cur_temperature - report['season_profile'][season+'_avg']: .2f} °C")

            season_stat.dataframe(data={
                'Сезон': [season],
                'Среднее': [report['season_profile'][season+'_avg']],
                'Ст. отклонение': [report['season_profile'][season+'_std']]
                })

        fig = go.Figure([
            go.Scatter(
                name='Температура (скользящее среднее)',
                x=df.index,
                y=df['temperature'].rolling(30).mean(),
                mode='lines',
                line=dict(color='rgb(31, 119, 180)'),
            ),
            go.Scatter(
                name='+2σ',
                x=df.index,
                y=df['temperature'].rolling(30).mean() + 2 * df['temperature'].rolling(30).std(),
                mode='lines',
                marker=dict(color="#444"),
                line=dict(width=0),
                fillcolor='rgba(68, 68, 68, 0.3)',
                fill='tonexty',
                showlegend=True
            ),
            go.Scatter(
                name='-2σ',
                x=df.index,
                y=df['temperature'].rolling(30).mean() - 2 * df['temperature'].rolling(30).std(),
                mode='lines',
                marker=dict(color="#444"),
                line=dict(width=0),
                fillcolor='rgba(68, 68, 68, 0.3)',
                fill='tonexty',
                showlegend=True
            ),
            go.Scatter(
                name='Аномалии',
                x=report['anomal_values'].index,
                y=report['anomal_values'],
                mode='markers',
                marker=dict(color="red"),
                line=dict(width=1),
                showlegend=True
            )
        ])
        fig.update_layout(
            yaxis=dict(title=dict(text='Температура (°C)')),
            title=dict(text='Изменение температуры во времени'),
            hovermode="x"
        )
        st.plotly_chart(fig, use_container_width=True)