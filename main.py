import os
import subprocess
import urllib.parse

from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta, timezone
from datetime import datetime
from loguru import logger

import message
from database import db
from parcer import get_top_films_and_serials, check_film_release, get_youtube_link, download_video

country_emojis = {
    "Afghanistan": "🇦🇫 Афганистан",
    "Åland Islands": "🇦🇽 Аландские острова",
    "Albania": "🇦🇱 Албания",
    "Algeria": "🇩🇿 Алжир",
    "American Samoa": "🇦🇸 Американское Самоа",
    "Andorra": "🇦🇩 Андорра",
    "Angola": "🇦🇴 Ангола",
    "Anguilla": "🇦🇮 Ангилья",
    "Antarctica": "🇦🇶 Антарктида",
    "Antigua & Barbuda": "🇦🇬 Антигуа и Барбуда",
    "Argentina": "🇦🇷 Аргентина",
    "Armenia": "🇦🇲 Армения",
    "Aruba": "🇦🇼 Аруба",
    "Australia": "🇦🇺 Австралия",
    "Austria": "🇦🇹 Австрия",
    "Azerbaijan": "🇦🇿 Азербайджан",
    "Bahamas": "🇧🇸 Багамы",
    "Bahrain": "🇧🇭 Бахрейн",
    "Bangladesh": "🇧🇩 Бангладеш",
    "Barbados": "🇧🇧 Барбадос",
    "Belarus": "🇧🇾 Беларусь",
    "Belgium": "🇧🇪 Бельгия",
    "Belize": "🇧🇿 Белиз",
    "Benin": "🇧🇯 Бенин",
    "Bermuda": "🇧🇲 Бермуды",
    "Bhutan": "🇧🇹 Бутан",
    "Bolivia": "🇧🇴 Боливия",
    "Bosnia & Herzegovina": "🇧🇦 Босния и Герцеговина",
    "Botswana": "🇧🇼 Ботсвана",
    "Bouvet Island": "🇧🇻 Остров Буве",
    "Brazil": "🇧🇷 Бразилия",
    "British Indian Ocean Territory": "🇮🇴 Британская территория Индийского океана",
    "British Virgin Islands": "🇻🇬 Британские Виргинские острова",
    "Brunei": "🇧🇳 Бруней",
    "Bulgaria": "🇧🇬 Болгария",
    "Burkina Faso": "🇧🇫 Буркина-Фасо",
    "Burma": "🇲🇲 Мьянма (Бирма)",
    "Burundi": "🇧🇮 Бурунди",
    "Cambodia": "🇰🇭 Камбоджа",
    "Cameroon": "🇨🇲 Камерун",
    "Canada": "🇨🇦 Канада",
    "Cape Verde": "🇨🇻 Кабо-Верде",
    "Caribbean Netherlands": "🇧🇶 Карибские Нидерланды",
    "Cayman Islands": "🇰🇾 Каймановы острова",
    "Central African Republic": "🇨🇫 Центральноафриканская Республика",
    "Chad": "🇹🇩 Чад",
    "Chile": "🇨🇱 Чили",
    "China": "🇨🇳 Китай",
    "Christmas Island": "🇨🇽 Остров Рождества",
    "Cocos (Keeling) Islands": "🇨🇨 Кокосовые (Килинг) острова",
    "Colombia": "🇨🇴 Колумбия",
    "Comoros": "🇰🇲 Коморы",
    "Congo - Brazzaville": "🇨🇬 Конго - Браззавиль",
    "Congo - Kinshasa": "🇨🇩 Конго - Киншаса",
    "Cook Islands": "🇨🇰 Острова Кука",
    "Costa Rica": "🇨🇷 Коста-Рика",
    "Côte d’Ivoire": "🇨🇮 Кот-д’Ивуар",
    "Croatia": "🇭🇷 Хорватия",
    "Cuba": "🇨🇺 Куба",
    "Curaçao": "🇨🇼 Кюрасао",
    "Cyprus": "🇨🇾 Кипр",
    "Czechia": "🇨🇿 Чехия",
    "Czechoslovakia": "🇨🇿 Чехословакия",
    "Denmark": "🇩🇰 Дания",
    "Djibouti": "🇩🇯 Джибути",
    "Dominica": "🇩🇲 Доминика",
    "Dominican Republic": "🇩🇴 Доминиканская Республика",
    "East Germany": "🇩🇪 Восточная Германия",
    "Ecuador": "🇪🇨 Эквадор",
    "Egypt": "🇪🇬 Египет",
    "El Salvador": "🇸🇻 Сальвадор",
    "Equatorial Guinea": "🇬🇶 Экваториальная Гвинея",
    "Eritrea": "🇪🇷 Эритрея",
    "Estonia": "🇪🇪 Эстония",
    "Eswatini": "🇸🇿 Эсватини",
    "Ethiopia": "🇪🇹 Эфиопия",
    "Falkland Islands": "🇫🇰 Фолклендские острова",
    "Faroe Islands": "🇫🇴 Фарерские острова",
    "Federal Republic of Yugoslavia": "🇷🇸 Федеративная Республика Югославия",
    "Fiji": "🇫🇯 Фиджи",
    "Finland": "🇫🇮 Финляндия",
    "France": "🇫🇷 Франция",
    "French Guiana": "🇬🇫 Французская Гвиана",
    "French Polynesia": "🇵🇫 Французская Полинезия",
    "French Southern Territories": "🇹🇫 Французские Южные и Антарктические территории",
    "Gabon": "🇬🇦 Габон",
    "Gambia": "🇬🇲 Гамбия",
    "Georgia": "🇬🇪 Грузия",
    "Germany": "🇩🇪 Германия",
    "Ghana": "🇬🇭 Гана",
    "Gibraltar": "🇬🇮 Гибралтар",
    "Greece": "🇬🇷 Греция",
    "Greenland": "🇬🇱 Гренландия",
    "Grenada": "🇬🇩 Гренада",
    "Guadeloupe": "🇬🇵 Гваделупа",
    "Guam": "🇬🇺 Гуам",
    "Guatemala": "🇬🇹 Гватемала",
    "Guernsey": "🇬🇬 Гернси",
    "Guinea": "🇬🇳 Гвинея",
    "Guinea-Bissau": "🇬🇼 Гвинея-Бисау",
    "Guyana": "🇬🇾 Гайана",
    "Haiti": "🇭🇹 Гаити",
    "Heard & McDonald Islands": "🇭🇲 Остров Херд и острова Макдональд",
    "Honduras": "🇭🇳 Гондурас",
    "Hong Kong SAR China": "🇭🇰 Гонконг (САР Китай)",
    "Hungary": "🇭🇺 Венгрия",
    "Iceland": "🇮🇸 Исландия",
    "India": "🇮🇳 Индия",
    "Indonesia": "🇮🇩 Индонезия",
    "Iran": "🇮🇷 Иран",
    "Iraq": "🇮🇶 Ирак",
    "Ireland": "🇮🇪 Ирландия",
    "Isle of Man": "🇮🇲 Остров Мэн",
    "Israel": "🇮🇱 Израиль",
    "Italy": "🇮🇹 Италия",
    "Jamaica": "🇯🇲 Ямайка",
    "Japan": "🇯🇵 Япония",
    "Jersey": "🇯🇪 Джерси",
    "Jordan": "🇯🇴 Иордания",
    "Kazakhstan": "🇰🇿 Казахстан",
    "Kenya": "🇰🇪 Кения",
    "Kiribati": "🇰🇮 Кирибати",
    "Korea": "🇰🇷 Корея",
    "Kosovo": "🇽🇰 Косово",
    "Kuwait": "🇰🇼 Кувейт",
    "Kyrgyzstan": "🇰🇬 Кыргызстан",
    "Laos": "🇱🇦 Лаос",
    "Latvia": "🇱🇻 Латвия",
    "Lebanon": "🇱🇧 Ливан",
    "Lesotho": "🇱🇸 Лесото",
    "Liberia": "🇱🇷 Либерия",
    "Libya": "🇱🇾 Ливия",
    "Liechtenstein": "🇱🇮 Лихтенштейн",
    "Lithuania": "🇱🇹 Литва",
    "Luxembourg": "🇱🇺 Люксембург",
    "Macao SAR China": "🇲🇴 Макао (САР Китай)",
    "Madagascar": "🇲🇬 Мадагаскар",
    "Malawi": "🇲🇼 Малави",
    "Malaysia": "🇲🇾 Малайзия",
    "Maldives": "🇲🇻 Мальдивы",
    "Mali": "🇲🇱 Мали",
    "Malta": "🇲🇹 Мальта",
    "Marshall Islands": "🇲🇭 Маршалловы острова",
    "Martinique": "🇲🇶 Мартиника",
    "Mauritania": "🇲🇷 Мавритания",
    "Mauritius": "🇲🇺 Маврикий",
    "Mayotte": "🇾🇹 Майотта",
    "Mexico": "🇲🇽 Мексика",
    "Micronesia": "🇫🇲 Микронезия",
    "Moldova": "🇲🇩 Молдова",
    "Monaco": "🇲🇨 Монако",
    "Mongolia": "🇲🇳 Монголия",
    "Montenegro": "🇲🇪 Черногория",
    "Montserrat": "🇲🇸 Монтсеррат",
    "Morocco": "🇲🇦 Марокко",
    "Mozambique": "🇲🇿 Мозамбик",
    "Myanmar (Burma)": "🇲🇲 Мьянма (Бирма)",
    "Namibia": "🇳🇦 Намибия",
    "Nauru": "🇳🇷 Науру",
    "Nepal": "🇳🇵 Непал",
    "Netherlands": "🇳🇱 Нидерланды",
    "Netherlands Antilles": "🇦🇳 Нидерландские Антильские острова",
    "New Caledonia": "🇳🇨 Новая Каледония",
    "New Zealand": "🇳🇿 Новая Зеландия",
    "Nicaragua": "🇳🇮 Никарагуа",
    "Niger": "🇳🇪 Нигер",
    "Nigeria": "🇳🇬 Нигерия",
    "Niue": "🇳🇺 Ниуэ",
    "Norfolk Island": "🇳🇫 Остров Норфолк",
    "North Korea": "🇰🇵 Северная Корея",
    "North Macedonia": "🇲🇰 Северная Македония",
    "North Vietnam": "🇻🇳 Северный Вьетнам",
    "Northern Mariana Islands": "🇲🇵 Северные Марианские острова",
    "Norway": "🇳🇴 Норвегия",
    "Oman": "🇴🇲 Оман",
    "Pakistan": "🇵🇰 Пакистан",
    "Palau": "🇵🇼 Палау",
    "Palestine": "🇵🇸 Палестина",
    "Panama": "🇵🇦 Панама",
    "Papua New Guinea": "🇵🇬 Папуа - Новая Гвинея",
    "Paraguay": "🇵🇾 Парагвай",
    "Peru": "🇵🇪 Перу",
    "Philippines": "🇵🇭 Филиппины",
    "Pitcairn Islands": "🇵🇳 Острова Питкэрн",
    "Poland": "🇵🇱 Польша",
    "Portugal": "🇵🇹 Португалия",
    "Puerto Rico": "🇵🇷 Пуэрто-Рико",
    "Qatar": "🇶🇦 Катар",
    "Réunion": "🇷🇪 Реюньон",
    "Romania": "🇷🇴 Румыния",
    "Russia": "🇷🇺 Россия",
    "Rwanda": "🇷🇼 Руанда",
    "Samoa": "🇼🇸 Самоа",
    "San Marino": "🇸🇲 Сан-Марино",
    "São Tomé & Príncipe": "🇸🇹 Сан-Томе и Принсипи",
    "Saudi Arabia": "🇸🇦 Саудовская Аравия",
    "Senegal": "🇸🇳 Сенегал",
    "Serbia": "🇷🇸 Сербия",
    "Serbia and Montenegro": "🇷🇸 Сербия и Черногория",
    "Seychelles": "🇸🇨 Сейшельские острова",
    "Siam": "🇹🇭 Сиам",
    "Sierra Leone": "🇸🇱 Сьерра-Леоне",
    "Singapore": "🇸🇬 Сингапур",
    "Slovakia": "🇸🇰 Словакия",
    "Slovenia": "🇸🇮 Словения",
    "Solomon Islands": "🇸🇧 Соломоновы Острова",
    "Somalia": "🇸🇴 Сомали",
    "South Africa": "🇿🇦 Южная Африка",
    "South Georgia & South Sandwich Islands": "🇬🇸 Южная Георгия и Южные Сандвичевы Острова",
    "South Korea": "🇰🇷 Южная Корея",
    "Soviet Union": "🇷🇺 Советский Союз",
    "Spain": "🇪🇸 Испания",
    "Sri Lanka": "🇱🇰 Шри-Ланка",
    "St. Barthélemy": "🇧🇱 Сен-Бартелеми",
    "St. Helena": "🇸🇭 Остров Святой Елены",
    "St. Kitts & Nevis": "🇰🇳 Сент-Китс и Невис",
    "St. Lucia": "🇱🇨 Сент-Люсия",
    "St. Martin": "🇲🇫 Сен-Мартен",
    "St. Pierre & Miquelon": "🇵🇲 Сен-Пьер и Микелон",
    "St. Vincent & Grenadines": "🇻🇨 Сент-Винсент и Гренадины",
    "Sudan": "🇸🇩 Судан",
    "Suriname": "🇸🇷 Суринам",
    "Svalbard & Jan Mayen": "🇸🇯 Шпицберген и Ян-Майен",
    "Sweden": "🇸🇪 Швеция",
    "Switzerland": "🇨🇭 Швейцария",
    "Syria": "🇸🇾 Сирия",
    "Taiwan": "🇹🇼 Тайвань",
    "Tajikistan": "🇹🇯 Таджикистан",
    "Tanzania": "🇹🇿 Танзания",
    "Thailand": "🇹🇭 Таиланд",
    "Timor-Leste": "🇹🇱 Тимор-Лесте",
    "Togo": "🇹🇬 Того",
    "Tokelau": "🇹🇰 Токелау",
    "Tonga": "🇹🇴 Тонга",
    "Trinidad & Tobago": "🇹🇹 Тринидад и Тобаго",
    "Tunisia": "🇹🇳 Тунис",
    "Turkey": "🇹🇷 Турция",
    "Turkmenistan": "🇹🇲 Туркменистан",
    "Turks & Caicos Islands": "🇹🇨 Острова Теркс и Кайкос",
    "Tuvalu": "🇹🇻 Тувалу",
    "U.S. Outlying Islands": "🇺🇲 Внешние малые острова США",
    "U.S. Virgin Islands": "🇻🇮 Виргинские острова США",
    "Uganda": "🇺🇬 Уганда",
    "Ukraine": "🇺🇦 Украина",
    "United Arab Emirates": "🇦🇪 ОАЭ",
    "United Kingdom": "🇬🇧 Великобритания",
    "United States": "🇺🇸 США",
    "Uruguay": "🇺🇾 Уругвай",
    "Uzbekistan": "🇺🇿 Узбекистан",
    "Vanuatu": "🇻🇺 Вануату",
    "Vatican City": "🇻🇦 Ватикан",
    "Venezuela": "🇻🇪 Венесуэла",
    "Vietnam": "🇻🇳 Вьетнам",
    "Wallis & Futuna": "🇼🇫 Уоллис и Футуна",
    "West Germany": "🇩🇪 Западная Германия",
    "Western Sahara": "🇪🇭 Западная Сахара",
    "Yemen": "🇾🇪 Йемен",
    "Yugoslavia": "🇷🇸 Югославия",
    "Zaire": "🇿🇲 Заир",
    "Zambia": "🇿🇲 Замбия",
    "Zimbabwe": "🇿🇼 Зимбабве"
}

category_dict = {
    "Action": "#Боевик",
    "Adventure": "#Приключения",
    "Animation": "#Мультфильм",
    "Biography": "#Биография",
    "Comedy": "#Комедия",
    "Crime": "#Криминал",
    "Documentary": "#Документальный",
    "Drama": "#Драма",
    "Family": "#Семейный",
    "Fantasy": "#Фэнтези",
    "Film-Noir": "#Фильм_нуар",
    "Game-Show": "#ИгровоеШоу",
    "History": "#Исторический",
    "Horror": "#Ужасы",
    "Music": "#Музыка",
    "Musical": "#Мюзикл",
    "Mystery": "#Мистика",
    "News": "#Новости",
    "Reality-TV": "#РеалитиШоу",
    "Romance": "#Мелодрама",
    "Sci-Fi": "#Фантастика",
    "Short": "#Короткометражка",
    "Sport": "#Спорт",
    "Talk-Show": "#ТокШоу",
    "Thriller": "#Триллер",
    "War": "#Военный",
    "Western": "#Вестерн"
}

urls_dict = {
    "Фильмы": "https://www.imdb.com/chart/moviemeter/?ref_=nv_mv_mpm&sort=release_date%2Cdesc&user_rating=5%2C",
    "Сериалы": "https://www.imdb.com/chart/tvmeter/?ref_=nv_tvv_mptv&sort=release_date%2Cdesc&user_rating=5%2C"
}

category_ban_list = ["#Короткометражка"]

def check_updates():
    # Шаг 1: Получить список устаревших пакетов
    result = subprocess.run(
        ["pip", "list", "--outdated", "--format=json"],
        capture_output=True,
        text=True
    )
    outdated_packages = eval(result.stdout)  # Преобразуем JSON-строку в список словарей

    # Шаг 2: Для каждого устаревшего пакета выполнить обновление
    for package in outdated_packages:
        package_name = package['name']
        if package_name == "pip":
            # Специальная команда для обновления pip
            logger.info("Обновляем pip...")
            subprocess.run([
                "python", "-m", "pip", "install", "--upgrade", "pip"
            ])
        else:
            logger.info(f"Обновляем пакет: {package_name}")
            subprocess.run(["pip", "install", "--upgrade", package_name])


def update_table():
    logger.info("Запускаю обновление таблиц")
    time_start = datetime.now()
    current_year = datetime.now().year - 1
    for content_type, content_type_url in urls_dict.items():
        # Создаем таблицы
        db.create_table(table_name=content_type)
        # Обновляем общий топ фильмов
        get_top_films_and_serials(content_type, content_type_url, current_year)
        # Обновляем каждый не вышедший фильм
        not_released_films = db.get_table(table_name=content_type, data={"date_now": None})
        if not_released_films:
            check_film_release(content_type=content_type, not_released_films=not_released_films)
    time_end = datetime.now() - time_start
    logger.info(f"Завершено за {f'{time_end.seconds % 3600 // 60} мин ' if time_end.seconds % 3600 // 60 > 0 else ''}{time_end.seconds % 60} сек")


def send_new_films():
    logger.info("Запускаю отправку сообщения в telegram")

    for content_type, content_type_url in urls_dict.items():
        # Проверяем что вышло за последнее время
        hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_movies = db.get_table(table_name=content_type, data={"date_now": (">=", hours_ago)}, sort_by="rating DESC")
        if recent_movies:
            for movie in recent_movies:
                title = movie['title']
                title_original = movie['title_original']

                year_start = movie['year_start']
                year_end = "" if movie['year_end'] is None else str(movie['year_end'])

                categories = ', '.join([category_dict.get(category.strip('"'), category) for category in movie['categories']])
                # Фильтр category_ban_list
                if any(banned in categories for banned in category_ban_list):
                    continue

                rating = movie['rating']

                description = movie['description']

                country = ', '.join([country_emojis.get(country.strip('"'), country) for country in movie['country']])

                url = movie['url']

                year_mod = f"{year_start}-{year_end}" if year_end else year_start
                title_full = f"{title} ({year_mod})"
                title_trailer = f"{title_original} {year_end} трейлер" if year_end else f"{title_original} {year_start} трейлер"

                # Кодируем название фильма для YouTube-поиска
                title_trailer_encoded = urllib.parse.quote_plus(title_trailer)
                youtube_url = f"https://www.youtube.com/results?search_query={title_trailer_encoded}"

                genre_content = (
                    f"<b><u>#{content_type}</u></b>\n"
                    f"<b><a href='{youtube_url}'>{title_full}</a></b>\n"
                    f"{country}\n"
                    f"🎬 {categories}\n"
                    f"⭐️ <a href='{url}'>{rating}</a>\n"
                    f"{description}")
                try:
                    # Получаем трейлер
                    youtube_link = get_youtube_link(video_name=title_trailer)
                    video_path = download_video(url=youtube_link, output_name=title_trailer)
                    if len(genre_content) <= 4096:
                        message.send_telegram_video(video_path=video_path, message=genre_content)
                    else:
                        message.send_report(f"Сообщение не отправилось. Длина сообщения: {len(genre_content)}")
                    # Удаление файла
                    os.remove(video_path)
                except Exception as e:
                    # Обновляем выход фильма
                    db.update_table(table_name=content_type, data={"url": url}, updates={"date_now": None})
                    message.send_report(e)


scheduler = BlockingScheduler()
scheduler.add_job(check_updates, 'cron', hour=14, minute=0)
scheduler.add_job(update_table, 'cron', hour=15, minute=0)
scheduler.add_job(send_new_films, 'cron', hour=16, minute=0)

if __name__ == "__main__":
    scheduler.start()
    #check_updates()
    #update_table()
    #send_new_films()