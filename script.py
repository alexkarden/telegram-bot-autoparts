import logging
import time
from urllib.parse import urlparse

import requests

from database import add_new_price_product, check_price_product
from sites.onlinerby import get_info_from_item_onlinerby
from sites.remzonaby import get_info_from_item_remzonaby
from sites.shate import get_info_from_item_shate
from sites.site21vekby import get_info_from_item_21vekby
from sites.wbby import get_info_from_item_wbby


# -----------------------------------------------------------------------------------------------------------------------выбор сайтов
async def is_link_belongs_to_site(url):

    # Разбираем URL
    parsed_url = urlparse(url)
    clear_url = parsed_url.netloc + parsed_url.path
    hostname = parsed_url.hostname

    # Выбираем сайт и вызываем асинхронные функции
    # onliner.by
    if hostname in ["catalog.onliner.by", "www.catalog.onliner.by"]:
        # Разделяем URL по символу '/'
        path_parts = clear_url.split("/")
        # Последний элемент — нужное значение
        value = path_parts[-1]
        url_onliner = 'https://catalog.api.onliner.by/products/'+value

        return await get_info_from_item_onlinerby(await get_item_from_url(url_onliner,0))
    elif hostname in ["www.remzona.by", "remzona.by"]:
        url_remzona = parsed_url.scheme + "://" + clear_url
        return await get_info_from_item_remzonaby(await get_item_from_url(url_remzona,1))
    elif hostname in ["www.shate-mag.by", "shate-mag.by"]:
        url_shate = parsed_url.scheme + "://" + clear_url

        return await get_info_from_item_shate(await get_item_from_url(url_shate,1))
    elif hostname in ["www.21vek.by", "m.21vek.by", "21vek.by"]:
        str_21vek = clear_url.replace("m.", "www.", 1)
        url_21vek = parsed_url.scheme + "://" + str_21vek
        return await get_info_from_item_21vekby(await get_item_from_url(url_21vek,0))
    elif hostname in ["www.wildberries.by", "www.wildberries.ru"]:
        # Разделяем URL по символу '/'
        path_parts = clear_url.split("/")
        # Последний элемент — нужное значение
        value = path_parts[-2]
        url_wb = f"https://card.wb.ru/cards/v2/list?curr=byn&dest=-59202&nm={value}&ignore_stocks=true"
        return await get_info_from_item_wbby(await get_item_from_url(url_wb,1))
    return None


# -----------------------------------------------------------------------------------------------------------------------
async def get_item_from_url(url, number_header):

    if number_header == 1:




        default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,be;q=0.6",
        }
    else:
        default_headers = {}

    try:
        response = requests.get(
            url, headers=default_headers)
          # Используйте requests.get для простоты
        response.raise_for_status()  # Проверка для HTTP ошибок (например, 404, 500 и т.д.)
        x = response.text  # Получаем JSON ответ от сервера
        return x
    except requests.exceptions.HTTPError as http_err:
        logging.exception(
            f"HTTP error occurred: {http_err}"
        )  # Вывод ошибки для отладки
    except Exception as err:
        logging.exception(f"An error occurred: {err}")  # Общая обработка исключений


# -----------------------------------------------------------------------------------------------------------------------Проверяем цены и записываем в базу
async def check_price(list_from_db):

    try:
        for product in list_from_db:
            # Предполагаем, что is_link_belongs_to_site - асинхронная
            result = await is_link_belongs_to_site(product[1])

            result2 = await check_price_product(product[0])
            # print(result[3], result2[3], result[4], result2[2])

            if result and result2:
                # Проверяем длину списков / корректность индексов, чтобы избежать ошибок
                if len(result) > 4 and len(result2) > 3:
                    if result[3] != result2[3] or result[4] != result2[2]:
                        current_time = int(time.time())
                        await add_new_price_product(
                            product[0], result[4], current_time, result[3]
                        )
                else:
                    logging.warning(
                        f"Получены некорректные данные по продукту {product[0]}"
                    )
    except Exception as err:
        logging.error(f"An error occurred: {err}", exc_info=True)


# _______________________________________________________________________________________________________________________ Функция для преобразования временной метки в строковую дату
async def convert_date_to_str(date_sec, hours):
    try:
        # Преобразуем временную метку (timestamp) в объект time.struct_time в формате UTC
        date_object = time.gmtime(date_sec + (hours * 60 * 60))
        # Форматируем объект time.struct_time в строку в формате "YYYY-MM-DD"
        naive_datetime = time.strftime("%d.%m.%Y %H:%M", date_object)

        return naive_datetime  # Возвращаем отформатированную строку даты
    except Exception as e:  # Обрабатываем любые исключения, которые могут произойти
        # Выводим сообщение об ошибке, если произошла ошибка во время преобразования
        logging.exception(f"Ошибка преобразования даты: {e}")
        return None  # Возвращаем None в случае ошибки
