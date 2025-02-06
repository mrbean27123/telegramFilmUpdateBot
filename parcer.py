import time
from yt_dlp import YoutubeDL
from deep_translator import GoogleTranslator
from loguru import logger
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from database import db
import message

remote_ip = "REMOTE_IP"

class WebDriverContext:
    def __init__(self, *args, **kwargs):
        self.driver = webdriver.Remote(*args, **kwargs)

    def __enter__(self):
        logger.success(f"Успешное подключение к Selenium")
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Закрытие соединения с Selenium")
        self.driver.quit()


# Настройки Chrome для удаленного подключения
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.116 Safari/537.36")
chrome_options.add_argument("--lang=ru-RU")


def is_page_loaded(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(1)
        return True
    except TimeoutException:
        message.send_report(TimeoutException)
        return False


def scroll_to_bottom(driver, delay=0.15):
    # Получаем общую высоту страницы
    total_height = driver.execute_script("return document.body.scrollHeight")
    step_height = driver.execute_script("return window.innerHeight * 0.9")  # 90% высоты окна
    current_position = 0  # Начальная позиция прокрутки
    while current_position < total_height:
        # Прокрутить на текущую позицию
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        time.sleep(delay)  # Задержка для подгрузки контента

        # Обновляем позицию
        current_position += step_height

    # Финальная прокрутка до самого низа
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")


def scroll_and_find_element(driver, xpath, delay=0.15, max_attempts=10):
    """
    Прокручивает страницу вниз и пытается найти элемент по XPath.
    Завершается, если элемент найден или если страница прокручена до конца.

    :param driver: Экземпляр Selenium WebDriver
    :param xpath: XPath элемента, который нужно найти
    :param delay: Задержка между прокрутками (в секундах)
    :param max_attempts: Максимальное количество попыток проверки высоты страницы
    :return: Найденный элемент (WebElement) или None, если элемент не найден
    """

    step_height = driver.execute_script("return window.innerHeight * 0.9")  # 90% высоты окна браузера
    for i in range(max_attempts):
        current_position = 0  # Начальная позиция прокрутки
        try:
            # Пытаемся найти элемент
            element = driver.find_element(By.XPATH, xpath)
            return element  # Элемент найден, выходим из функции
        except:
            pass  # Если элемент не найден, продолжаем скроллить
        last_height = driver.execute_script("return document.body.scrollHeight")  # высота страницы
        while current_position < last_height:
            # Прокрутить на текущую позицию
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(delay)  # Задержка для подгрузки контента

            # Обновляем позицию
            current_position += step_height

        # Финальная прокрутка до самого низа
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Если элемент не найден, возвращаем None
    return None


def get_top_films_and_serials(content_type, content_type_url, current_year):
    # Используем контекстный менеджер для управления драйвером
    with WebDriverContext(command_executor=f'http://{remote_ip}/wd/hub', options=chrome_options) as driver:
        logger.debug(f"Получаем все {content_type}")
        driver.get(content_type_url)

        # Проверяем, что страница загружена
        is_page_loaded(driver)

        film_table_element = driver.find_element(By.XPATH, './/ul[contains(@class, "ipc-metadata-list")]')
        film_items_list = film_table_element.find_elements(By.XPATH, './/li[contains(@class, "ipc-metadata-list-summary-item")]')

        for film_item in film_items_list:
            try:
                try:
                    year_text = film_item.find_element(By.XPATH, './/span[contains(@class, "cli-title-metadata-item")]').text
                    year_parts = year_text.split('–') # Разбиваем year_text по символу и обрабатываем начало и конец года
                    year_start = int(year_parts[0])  # Начальный год всегда присутствует

                    # Если указан конечный год, пытаемся преобразовать его, иначе присваиваем None
                    year_end = int(year_parts[1]) if len(year_parts) > 1 and year_parts[1].isdigit() else None
                except:
                    continue

                if year_start < current_year and (year_end is None or year_end < current_year):
                    continue

                title_text = film_item.find_element(By.XPATH, './/h3[contains(@class, "ipc-title__text")]').text
                url_element = film_item.find_element(By.XPATH, './/a[contains(@class, "ipc-title-link-wrapper")]')
                url = url_element.get_attribute("href").split('/?ref')[0]

                try:
                    rating = float(film_item.find_element(By.XPATH, './/span[contains(@class, "ipc-rating-star--rating")]').text)
                except:
                    rating = None

                film_exist = db.get_table(table_name=content_type, data={"url": url})
                # Если нет в таблице, добавляем фильм
                if not film_exist:
                    db.add_into_table(table_name=content_type, data={"title": title_text, "year_start": year_start, "year_end": year_end, "rating": rating, "url": url})
                    logger.success(f"{content_type} вышел: {title_text} {url}")
                # Если есть в таблице, проверяем не изменился ли year_end
                else:
                    year_end_exist = film_exist[0]["year_end"]
                    if year_end != year_end_exist:
                        db.update_table(table_name=content_type, data={"url": url}, updates={"title": title_text, "year_start": year_start, "year_end": year_end, "rating": rating, "date_now": None})
                        logger.success(f"Изменился year_end у {title_text} {year_end_exist} => {year_end}")

            except Exception as e:
                message.send_report(e)


def check_film_release(content_type, not_released_films):
    # Используем контекстный менеджер для управления драйвером
    with WebDriverContext(command_executor='http://192.168.1.97:4444/wd/hub', options=chrome_options) as driver:
        logger.debug(f"Проверяем вышли ли новые {content_type}")
        for n, film in enumerate(not_released_films, start=1):
            try:
                logger.debug(f"{n}/{len(not_released_films)} {film['title']} {film['url']}")
                driver.get(film['url'])

                # Проверяем, что страница загружена
                is_page_loaded(driver)
                # Промотка страницы для прогрузки нужного элемента
                category_span = scroll_and_find_element(driver=driver, xpath='//span[contains(text(), "Genre")]/following-sibling::div', delay=0.1, max_attempts=60)
                if not category_span:
                    logger.warning("Элемент category_span не найден.")
                    continue

                title_text = driver.find_element(By.XPATH, './/span[contains(@data-testid, "hero__primary-text")]').text

                try:
                    rating = float(driver.find_element(By.XPATH, './/div[contains(@data-testid, "hero-rating-bar__aggregate-rating__score")]/span').text)
                except:
                    continue

                try:
                    title_original_text = driver.find_element(By.XPATH, './/div[contains(text(), "Original title: ")]').text.split("Original title: ")[1]
                except:
                    title_original_text = title_text

                description_text = driver.find_element(By.XPATH, './/span[contains(@data-testid, "plot-l")]').get_attribute("textContent")
                description_text_trans = GoogleTranslator(source="en", target="ru").translate(description_text)

                country_span = driver.find_element(By.XPATH, '//span[contains(text(), "of origin")]/following-sibling::div')
                country_elements = country_span.find_elements(By.XPATH,  './/li')
                country_list = [element.text for element in country_elements]

                category_elements = category_span.find_elements(By.XPATH,  './/li')
                category_list = [element.text for element in category_elements]
                try:
                    # Поиск даты (фильм не вышел)
                    driver.find_element(By.XPATH, './/div[contains(@data-testid, "tm-box-up")]')
                    db.update_table(table_name=content_type, data={"url": film['url']}, updates={"title": title_text, "title_original": title_original_text,"categories": category_list, "rating": rating, "description": description_text_trans, "country": country_list})
                    continue
                except:
                    pass

                # Обновляем выход фильма
                db.update_table(table_name=content_type, data={"url": film['url']}, updates={"title": title_text, "title_original": title_original_text, "categories": category_list, "rating": rating, "description": description_text_trans, "country": country_list, "date_now": datetime.now(timezone.utc)})
                logger.success(f"Новый релиз: {title_text}")
            except Exception as e:
                message.send_report(e)


def get_youtube_link(video_name):
    # Используем контекстный менеджер для управления драйвером
    with WebDriverContext(command_executor='http://192.168.1.97:4444/wd/hub', options=chrome_options) as driver:
        logger.debug(f"Получаем ссылку на {video_name}")
        try:
            driver.get(f"https://www.youtube.com/results?search_query={video_name}")

            # Проверяем, что страница загружена
            is_page_loaded(driver)

            # Получаем все ссылки на видео
            video_links = driver.find_elements(By.XPATH, './/a[contains(@id, "video-title")]')

            for video in video_links:
                video_href = video.get_attribute('href')
                if video_href and "shorts/" not in video_href:  # Исключаем Shorts
                    return video_href
        except Exception as e:
            message.send_report(e)
            return None


def download_video(url, output_name):
    try:
        logger.debug(f"Скачиваем {output_name}")
        options = {
            "format": "best",
            "outtmpl": output_name + ".%(ext)s",
            "noprogress": True, # Отключаем прогрессбар
            "quiet": True,  # Отключаем лишние логи
        }
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)  # Загрузка и получение информации о видео
            file_path = ydl.prepare_filename(info)  # Генерация имени файла
        return file_path
    except Exception as e:
        message.send_report(e)


if __name__ == "__main__":
    pass


