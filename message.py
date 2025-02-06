import os
import json
import requests
import traceback
from loguru import logger

telegram_bot_token = "TELEGRAM_BOT_TOKEN"
telegram_chat_id = "TELEGRAM_GROUP_CHAT_ID"
telegram_chat_log = "TELEGRAM_ADMIN_CHAT_ID"


def send_report(message):
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    error = f"{message}\n{traceback.format_exc()}"
    data = {
        'chat_id': telegram_chat_log,
        'text': error
    }
    requests.post(url, data=data)
    logger.error(error)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    data = {
        'chat_id': telegram_chat_id,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': 'true'
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        logger.success('Сообщение в Telegram отправлено')
    else:
        send_report(f'Ошибка при отправке сообщения в Telegram. Код статуса: {response.status_code}: {response.text}')


def send_telegram_video(video_path, message):
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendVideo"
    try:
        with open(video_path, 'rb') as video_file:
            data = {
                'chat_id': telegram_chat_id,
                'caption': message,
                'supports_streaming': True,
                'parse_mode': 'HTML',
                'disable_web_page_preview': 'true'
            }
            files = {'video': video_file}
            response = requests.post(url, data=data, files=files)
            if response.status_code == 200:
                logger.success('Видео успешно отправлено в Telegram.')
            else:
                send_report(f'Ошибка при отправке видео. Код статуса: {response.status_code}, {response.text}')
    except FileNotFoundError:
        send_report('Файл видео не найден')


def send_telegram_videos(video_paths, message):
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMediaGroup"
    media, files = [], {}
    try:
        for idx, video_path in enumerate(video_paths):
            if os.path.exists(video_path):
                file_key = f"video{idx}"
                files[file_key] = (os.path.basename(video_path), open(video_path, "rb"), "video/mp4")
                media.append({
                    "type": "video",
                    "media": f"attach://{file_key}",
                    "supports_streaming": True,
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': 'true'
                })

        if media:
            media[0]["caption"] = message  # Подпись добавляется к первому видео
            response = requests.post(url, data={"chat_id": telegram_chat_id, "media": json.dumps(media)}, files=files)
            logger.success("Видео успешно отправлены." if response.ok else f"Ошибка: {response.status_code} - {response.text}")

        for file in files.values():
            file[1].close() # Закрываем файл
    except FileNotFoundError:
        send_report('Файл видео не найден')
