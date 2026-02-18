import logging
import os
import time

import asyncpg
from dotenv import load_dotenv


load_dotenv()


DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}


# Инициализация глобальной переменной для пула
pool = None


# Создает и возвращает пул соединений к базе данных.
async def create_pool():
    return await asyncpg.create_pool(**DATABASE_CONFIG)


# Возвращает пул соединений
async def get_pool():
    global pool
    if pool is None:
        pool = await create_pool()
    return pool


# Закрывает пул соединений
async def close_pool():
    global pool
    if pool is not None:
        await pool.close()
        pool = None


# -----------------------------------------------------------------------------------------------------------------------Инициализация базы данных
async def init_db():
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Создание таблицы users, если она еще не существует
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "id SERIAL PRIMARY KEY, "
                "user_id INT UNIQUE, "
                "first_name VARCHAR(255), "
                "last_name VARCHAR(255), "
                "username VARCHAR(255), "
                "user_added INT NOT NULL, "
                "user_blocked INT NOT NULL, "
                "type_of_notification VARCHAR(255), "
                "notification_frequency VARCHAR(255),"
                "created_at INT)"
            )
            # Создание таблицы products, если она еще не существует
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS products ("
                "id SERIAL PRIMARY KEY,"
                "product_url VARCHAR(255) NOT NULL,"
                "product_title  VARCHAR(255) NOT NULL,"
                "product_image_url VARCHAR(255),"
                "status INT NOT NULL,"
                "market VARCHAR(255))"
            )
            # Создание таблицы user_products, если она еще не существует
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS user_products ("
                "id SERIAL PRIMARY KEY,"
                "user_id INT,"
                "product_id INT,"
                "threshold INT)"
            )

            # Создание таблицы user_pools, если она еще не существует
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS user_pools ("
                "id SERIAL PRIMARY KEY,"
                "user_id INT,"
                "product_id INT,"
                "pool_title  VARCHAR(255) NOT NULL,"
                "pool_image_url VARCHAR(255))"
            )

            # Создание таблицы pool_products, если она еще не существует
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS pool_products ("
                "id SERIAL PRIMARY KEY,"
                "pools_id INT,"
                "product_id INT,"
                "user_id INT)"
            )

            # Создание таблицы product_price_history, если она еще не существует
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS product_price_history ("
                "id SERIAL PRIMARY KEY,"
                "product_id INT NOT NULL,"
                "product_availability_status VARCHAR(255),"
                "product_price INT,"
                "product_data_retrieval_time INT)"
            )
    except asyncpg.PostgresError as e:
        logging.exception(
            f"Ошибка при работе с PostgreSQL - Инициализация базы данных: {e}"
        )
    except Exception as e:
        logging.exception(f"Произошла ошибка Инициализация базы данных: {e}")


# -----------------------------------------------------------------------------------------------------------------------добавление товара в базу
async def add_new_product(
    product_url: str,
    product_title: str,
    product_image_url: str,
    product_price: int,
    product_availability_status: str,
    product_data_retrieval_time: int,
    status: int,
    user_id: int,
    market: str,
):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():  # Используем транзакцию для безопасного управления
                # Проверяем, есть ли такой продукт
                result = await conn.fetch(
                    "SELECT * FROM products WHERE product_url = $1", product_url
                )

                if not result:
                    # Если не существует, добавляем новый продукт
                    product_id = await conn.fetchval(
                        "INSERT INTO products (product_url, product_title, product_image_url, status, market) "
                        "VALUES ($1, $2, $3, $4, $5) RETURNING id",
                        product_url,
                        product_title,
                        product_image_url,
                        status,
                        market,
                    )

                    # Добавляем данные о ценах, наличии и датах
                    await conn.execute(
                        "INSERT INTO product_price_history (product_id, product_availability_status, product_data_retrieval_time, product_price) "
                        "VALUES ($1, $2, $3, $4)",
                        product_id,
                        product_availability_status,
                        product_data_retrieval_time,
                        product_price,
                    )
                else:
                    product_id = result[0]["id"]  # Получаем ID существующего продукта

                # Проверяем, есть ли запись в user_products
                result = await conn.fetch(
                    "SELECT * FROM user_products WHERE user_id = $1 AND product_id = $2",
                    user_id,
                    product_id,
                )

                if not result:
                    # Если не существует, добавляем товар к пользователю
                    await conn.execute(
                        "INSERT INTO user_products (user_id, product_id) VALUES ($1, $2)",
                        user_id,
                        product_id,
                    )

    except Exception as e:
        logging.exception(f"Ошибка при добавлении продукта: {e}")


# -----------------------------------------------------------------------------------------------------------------------Вынимаем товар из базы
async def get_product_from_id(product_id):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Проверяем, есть ли такой продукт
            result = await conn.fetchrow(
                "SELECT * FROM products WHERE id = $1", int(product_id)
            )
            return result  # Возвращаем результат, если продукт найден

    except Exception as e:
        logging.exception(f"Ошибка при получении продукта с ID {product_id}: {e}")
        return None  # Возвращаем None в случае ошибки


# -----------------------------------------------------------------------------------------------------------------------добавление товара в пул
async def add_to_pool(
    user_id: int,
    product_id: int,
):
    pool = await get_pool()  # Получаем пул соединений
    try:
        # Передаем pool в функцию получения информации о продукте
        product_info = await get_product_from_id(product_id)

        if product_info is None:  # Проверка на случай, если продукт не найден
            logging.error(f"Продукт с ID {product_id} не найден.")
            return

        pool_title = product_info["product_title"]  # Предполагаем, что это словарь
        pool_image_url = product_info["product_image_url"]

        async with pool.acquire() as conn:
            # Проверяем, есть ли такой пул
            result = await check_pool(
                user_id, product_id
            )  # Предполагается, что эта функция правильно реализована

            if not result:  # Если не существует, добавляем новый пул
                pools_id = await conn.fetchval(
                    "INSERT INTO user_pools (user_id, pool_title, pool_image_url, product_id) "
                    "VALUES ($1, $2, $3, $4) RETURNING id",
                    int(user_id),
                    pool_title,
                    pool_image_url,
                    int(product_id),
                )

                # Добавляем этот же товар в пул
                await conn.execute(
                    "INSERT INTO pool_products (pools_id, product_id, user_id) VALUES ($1, $2, $3)",
                    int(pools_id),
                    int(product_id),
                    int(user_id),
                )

    except Exception as e:
        logging.exception(f"Ошибка при добавлении в пул: {e}")


# -----------------------------------------------------------------------------------------------------------------------Проверяем есть ли такой пул
async def check_pool(user_id: int, product_id: int) -> bool:
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Проверяем, есть ли такой пул
            result = await conn.fetchrow(
                "SELECT 1 FROM user_pools WHERE user_id = $1 AND product_id = $2",
                int(user_id),
                int(product_id),
            )
            return (
                result is not None
            )  # Возвращаем True, если пул существует, иначе False
    except Exception as e:
        logging.exception(f"Ошибка при проверке пула: {e}")
        return False  # Возвращаем False в случае ошибки


# -----------------------------------------------------------------------------------------------------------------------Проверяем есть ли такой товар в пуле
async def check_pool_product(user_id: int, product_id: int) -> bool:
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Проверяем, есть ли такой товар в пуле
            result = await conn.fetchrow(
                "SELECT 1 FROM pool_products WHERE user_id = $1 AND product_id = $2",
                int(user_id),
                int(product_id),
            )
            return result is not None  # Возвращаем True, если товар найден, иначе False
    except Exception as e:
        logging.exception(f"Ошибка при проверке товара в пуле: {e}")
        return False  # Возвращаем False в случае ошибки


# -----------------------------------------------------------------------------------------------------------------------Формируем список пулов пользователя
async def get_list_pools(user_id: int):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Получаем все пулы для указанного пользователя
            result = await conn.fetch(
                "SELECT * FROM user_pools WHERE user_id = $1", int(user_id)
            )
            return result  # Возвращаем все найденные пулы
    except Exception as e:
        logging.exception(
            f"Ошибка при получении списка пулов для пользователя {user_id}: {e}"
        )
        return []  # Можно вернуть пустой список или None, в зависимости от вашей логики


# -----------------------------------------------------------------------------------------------------------------------Формируем список продуктов в пуле пользователя
async def get_list_product_from_pools(user_id: int, pools_id: int):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Получаем все товары из указанного пула для данного пользователя
            result = await conn.fetch(
                "SELECT * FROM pool_products WHERE user_id = $1 AND pools_id = $2",
                int(user_id),
                int(pools_id),
            )
            return result  # Возвращаем все найденные товары
    except Exception as e:
        logging.exception(f"Ошибка при получении списка товаров из пула: {e}")
        return None  # Возможно, возвращаем None или другую информацию об ошибке


# -----------------------------------------------------------------------------------------------------------------------возвращаем мин цену в пуле
async def get_min_pool_price(user_id: int, pool_id: int):

    try:
        list_product = await get_list_product_from_pools(user_id, pool_id)

        # Проверяем, что список продуктов не пуст
        if list_product is None or not list_product:
            logging.warning(f"Нет продуктов в пуле {pool_id}.")
            return None

        price_min_list = []
        price_min_product_list =[]
        for product in list_product:
            product_id = product["product_id"]
            product_price = await check_price_product(product_id)
            product_min_price = await min_price_product(product_id)

            if product_price and product_price[3] is not None:  # Проверка на None
                price_min_list.append(product_price[3])
                if product_min_price:
                    price_min_product_list.append(product_min_price)
                else:
                    price_min_product_list.append(product_price[3])


        # Проверяем, что список цен не пуст
        if price_min_list:
            price_min = min(price_min_list)
            if price_min_product_list:
                price_min_product = min(price_min_product_list)
                return [price_min, price_min_product]

        
        return [None, None]  # Или любое другое значение, указывающее на отсутствие цен

    except Exception as e:
        logging.exception(f"Ошибка при получении минимальной цены: {e}")
        return [None, None]   # Возможно, возвращаем None или другую информацию об ошибке


# -----------------------------------------------------------------------------------------------------------------------Добавляем товар в уже созданный пул
async def append_product_to_pool(user_id: int, pools_id: int, product_id: int):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:

            # Проверяем, существует ли уже продукт в пуле
            existing_product = await conn.fetchrow(
                "SELECT * FROM pool_products WHERE user_id = $1 AND pools_id = $2 AND product_id = $3",
                int(user_id),
                int(pools_id),
                int(product_id),
            )

            if existing_product is None:  # Если продукта в пуле нет, добавляем
                await conn.execute(
                    "INSERT INTO pool_products (pools_id, product_id, user_id) VALUES ($1, $2, $3)",
                    int(pools_id),
                    int(product_id),
                    int(user_id),
                )
            else:
                logging.info(
                    f"Продукт с ID {product_id} уже существует в пуле для пользователя {user_id}."
                )
    except Exception as e:
        logging.exception(f"Ошибка при добавлении продукта: {e}")


# -----------------------------------------------------------------------------------------------------------------------Удаляем товар из пула
# удаляем у пользователя и если больше никто такой товар не отслеживает, то удаляем из базы


async def delete_product_from_pool(user_id: int, product_id: int):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():  # Используем транзакцию для безопасности
                # Проверяем, есть ли такой товар в пуле
                result = await conn.fetchrow(
                    "SELECT pools_id FROM pool_products WHERE user_id = $1 AND product_id = $2",
                    int(user_id),
                    int(product_id),
                )

                if result:  # Проверяем, что результат не None
                    pool_id = result[0]  # pool_id это первый элемент результата

                    # Удаляем продукт у пользователя
                    await conn.execute(
                        "DELETE FROM pool_products WHERE user_id = $1 AND product_id = $2",
                        int(user_id),
                        int(product_id),
                    )

                    # Проверяем, есть ли товары в пуле
                    result = await conn.fetch(
                        "SELECT * FROM pool_products WHERE pools_id = $1", int(pool_id)
                    )

                    # Проверяем, есть ли товары в пуле
                    if not result:  # Если результат пустой, значит товаров нет
                        await conn.execute(
                            "DELETE FROM user_pools WHERE id = $1", int(pool_id)
                        )
                else:
                    logging.info(
                        f"Продукт с ID {product_id} не найден в пуле у пользователя {user_id}."
                    )
    except Exception as e:
        logging.exception(f"Ошибка при удалении продукта из пула или самого пула: {e}")


# -----------------------------------------------------------------------------------------------------------------------Возвращаем порог цены для товара
async def get_threshold(user_id: int, product_id: int):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Проверяем, есть ли такой товар у пользователя
            result = await conn.fetchrow(
                "SELECT * FROM user_products WHERE user_id = $1 AND product_id = $2",
                user_id,
                int(product_id),
            )
            if result:
                return result[3]  # Предполагаем, что третий элемент является порогом
            return None
    except Exception as e:
        logging.exception(f"Ошибка при получении порога из базы данных: {e}")
        return None  # Возвращаем None в случае ошибки


# -----------------------------------------------------------------------------------------------------------------------Добавляем порог цены для товара
async def add_threshold(user_id: int, product_id: int, threshold: float):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            if threshold is None:
                # Устанавливаем значение threshold в NULL
                await conn.execute(
                    "UPDATE user_products SET threshold = NULL WHERE user_id = $1 AND product_id = $2",
                    user_id,
                    int(product_id),
                )
            else:
                # Устанавливаем значение threshold
                await conn.execute(
                    "UPDATE user_products SET threshold = $1 WHERE user_id = $2 AND product_id = $3",
                    threshold,
                    user_id,
                    int(product_id),
                )
    except Exception as e:
        logging.exception(
            f"Ошибка при добавлении порога в базу для пользователя {user_id} и продукта {product_id}: {e}"
        )


# -----------------------------------------------------------------------------------------------------------------------Формируем список товаров которые надо обновлять
async def get_list_product():
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Получаем все продукты из таблицы
            result = await conn.fetch("SELECT * FROM products")
            # Возвращаем только 1-й и 2-й элемент из каждой строки
            filtered_result = [(row[0], row[1], row[5]) for row in result]
            return filtered_result
    except Exception as e:
        logging.exception(f"Ошибка при получении списка продуктов: {e}")
        return []  # Можно вернуть пустой список или None в случае ошибки


# -----------------------------------------------------------------------------------------------------------------------Проверяем последнюю цену товара
async def check_price_product(product_id):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Получаем последнюю цену для продукта
            result = await conn.fetchrow(
                "SELECT * FROM product_price_history "
                "WHERE product_id = $1 "
                "AND product_data_retrieval_time = ("
                "    SELECT MAX(product_data_retrieval_time) "
                "    FROM product_price_history "
                "    WHERE product_id = $1)",
                int(product_id),
            )

            if result:
                return result  # Возвращаем результат (или None, если ничего не найдено)

            logging.info(f"Нет цен для товара с ID {product_id}.")
            return None
    except Exception as e:
        logging.exception(f"Ошибка при извлечении цены товара с ID {product_id}: {e}")
        return None  # Возвращаем None в случае ошибки


# ----------------------------------------------------------------------------------------------------------------------Функция извлечения min и max цен
async def min_max_price_product(product_id: int):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Проверяем наличие хотя бы двух различных цен
            result = await conn.fetchrow(
                "SELECT COUNT(DISTINCT product_price) FROM product_price_history WHERE product_id = $1",
                int(product_id),
            )
            unique_price_count = result[0] if result else 0

            if unique_price_count < 2:

                logging.info(
                    f"Недостаточно данных для извлечения цен: только {unique_price_count} уникальных записей."
                )
                return None  # Возвращаем None, если меньше двух уникальных цен

            # Извлекаем минимальную и максимальную цену
            min_max_price = await conn.fetchrow(
                "SELECT MIN(product_price) AS min_price, MAX(product_price) AS max_price FROM product_price_history WHERE product_id = $1",
                int(product_id),
            )

            if min_max_price:

                return min_max_price  # Возвращаем кортеж (min_price, max_price)
            logging.info("Не найдено цен для данного продукта.")

            return None

    except Exception as e:
        logging.exception(f"Ошибка при извлечении цен товара с ID {product_id}: {e}")
        print(f"Ошибка при извлечении цен товара с ID {product_id}: {e}")
        return None

# ----------------------------------------------------------------------------------------------------------------------Функция извлечения min цен
async def min_price_product(product_id: int):
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            min_price = await conn.fetchval(
                "SELECT MIN(product_price) FROM product_price_history WHERE product_id = $1",
                int(product_id),
            )
            if min_price is None:
                logging.info("Не найдено цен для product_id=%s", product_id)
                return None
            return int(min_price)

    except Exception:
        logging.exception("Ошибка при извлечении минимальной цены для product_id=%s", product_id)
        return None

# -----------------------------------------------------------------------------------------------------------------------Возвращаем последние 2 записи
async def check_last_two_price_times(product_id: int):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Получаем два последних времени извлечения данных для указанного продукта
            result = await conn.fetch(
                "SELECT product_price FROM product_price_history WHERE product_id = $1 "
                "ORDER BY product_data_retrieval_time DESC LIMIT 2",
                int(product_id),
            )

            if result:
                if len(result) == 1:
                    # Если найдена только одна запись, возвращаем список с двумя одинаковыми значениями
                    last_price = result[0][0]
                    return [last_price, last_price]

                # Если найдено больше одной записи, возвращаем реальные последние два значения
                last_two_price = [row[0] for row in result]
                return last_two_price

            logging.warning(f"Не найдены записи для продукта с ID: {product_id}")
            return None  # Возвращаем None, если записи не найдены

    except Exception as e:
        logging.exception(
            f"Ошибка при проверке времени извлечения цены продукта с ID {product_id}: {e}"
        )
        return None  # Возвращаем None в случае возникновения ошибки


# -----------------------------------------------------------------------------------------------------------------------Возвращаем все записи для графика
async def get_all_price_times(product_id: int):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Получаем все данные для указанного продукта
            result = await conn.fetch(
                "SELECT * FROM product_price_history WHERE product_id = $1 "
                "ORDER BY product_data_retrieval_time",
                int(product_id),
            )

            # Формируем список пар: (номер по порядку, product_price)
            # Предполагаем, что product_price находится по индексу 3 и другая информация по индексу 4
            price_list = [
                (index + 1, row[3], row[4]) for index, row in enumerate(result)
            ]
            return price_list  # Возвращаем результат

    except Exception as e:
        logging.exception(
            f"Ошибка при получении всех времён цен продукта с ID {product_id}: {e}"
        )
        return None  # Возвращаем None в случае возникновения ошибки


# -----------------------------------------------------------------------------------------------------------------------Записываем новую цену
async def add_new_price_product(
    product_id: int,
    product_availability_status: str,
    product_data_retrieval_time: int,
    product_price: float,
):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Записываем новую цену
            await conn.execute(
                "INSERT INTO product_price_history ("
                "product_id, "
                "product_availability_status, "
                "product_data_retrieval_time, "
                "product_price"
                ") VALUES ($1, $2, $3, $4)",  # Используем $1, $2 и т.д.
                product_id,
                product_availability_status,
                product_data_retrieval_time,
                product_price,
            )

            # Устанавливаем статус для товара
            await conn.execute(
                "UPDATE products SET status = 1 WHERE id = $1", int(product_id)
            )

    except Exception as e:
        logging.exception(f"Ошибка при добавлении продукта: {e}")


# -----------------------------------------------------------------------------------------------------------------------Добавляем нового пользователя
# Добавление пользователя в базу данных
async def add_user_db(user_id: int, first_name: str, last_name: str, username: str):
    created_at = int(time.time())
    pool = await get_pool()  # Получаем пул соединений

    try:
        async with pool.acquire() as conn:
            # Проверка, существует ли пользователь в базе данных
            result = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", user_id
            )

            if result is not None:
                # Если пользователь существует, обновляем его данные
                await conn.execute(
                    "UPDATE users SET first_name = $1, last_name = $2, username = $3, user_added = $4 WHERE user_id = $5",
                    first_name,
                    last_name,
                    username,
                    1,
                    user_id,
                )

                logging.info(f"Пользователь с ID {user_id} обновлен в базе данных.")
            else:
                # Если не существует, добавляем нового пользователя
                await conn.execute(
                    "INSERT INTO users (user_id, first_name, last_name, username, user_added, user_blocked, created_at, type_of_notification, notification_frequency) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                    user_id,
                    first_name,
                    last_name,
                    username,
                    1,
                    0,
                    created_at,
                    "full",
                    "never",
                )
                logging.info(f"Пользователь с ID {user_id} добавлен в базу данных.")

    except Exception as e:
        logging.exception(
            f"Произошла неожиданная ошибка при добавлении пользователя с ID {user_id}: {e}"
        )


# -----------------------------------------------------------------------------------------------------------------------Извлекаем список товаров для рассылки
async def get_list_product_for_rassilka(status):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Получаем все продукты из таблицы, которые надо разослать
            result = await conn.fetch(
                "SELECT * FROM products WHERE status = $1", status
            )

            if result:
                return result  # Возвращаем результат, если есть
            else:
                logging.info("Нет списка продуктов.")
                return []  # Просто возвращаем пустой список
    except Exception as e:
        logging.exception(f"Получение списка для рассылки Неизвестная ошибка: {e}")
        return []  # Возвращаем пустой список в случае ошибки


# -----------------------------------------------------------------------------------------------------------------------Извлекаем список пользователей для рассылки
async def get_list_users_for_rassilka(product_id):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Получаем всех пользователей для указанного продукта
            result = await conn.fetch(
                "SELECT * FROM user_products WHERE product_id = $1", product_id
            )

            # Возвращаем результат, если есть, иначе пустой список
            if result:
                return result
            else:
                logging.info(f"Нет пользователей для продукта с ID {product_id}.")
                return []

    except Exception as e:
        logging.exception(
            f"Ошибка при получении пользователей для продукта с ID {product_id}: {e}"
        )
        return []  # Возвращаем пустой список в случае ошибки


async def get_all_users_for_redis():
    pool = await get_pool()  # get_pool — coroutine, OK
    query = "SELECT * FROM users"

    try:
        async with pool.acquire() as conn:
            records = await conn.fetch(query)
            if not records:
                logging.info("Нет пользователей в таблице users.")
                return []

            users = [dict(rec) for rec in records]
            return users

    except Exception:
        logging.exception("Ошибка при получении пользователей из БД")
        return []


# -----------------------------------------------------------------------------------------------------------------------Извлекаем список пользователей для рассылки
async def change_status_product(status, product_id):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Обновляем статус продукта в таблице products
            await conn.execute(
                "UPDATE products SET status = $1 WHERE id = $2", status, product_id
            )

            logging.info(
                f"Статус продукта с ID {product_id} обновлен на {status}."
            )  # Добавлено логирование успешного обновления
    except Exception as e:
        logging.exception(
            f"Ошибка при обновлении статуса продукта с ID {product_id}: {e}"
        )


# -----------------------------------------------------------------------------------------------------------------------Получаем список товаров пользователя
async def get_user_list_product(user_id: int):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Получаем все продукты для указанного пользователя
            user_products = await conn.fetch(
                "SELECT * FROM user_products WHERE user_id = $1", int(user_id)
            )

            # Проверка, есть ли результаты
            if not user_products:
                logging.warning(f"Не найдены продукты для пользователя с ID {user_id}.")
                return []  # Возвращаем пустой список, если продукты не найдены

            # Извлекаем ID продуктов
            product_ids = [
                item[2] for item in user_products
            ]  # Предполагаем, что ID продукта находится на позиции item[2]

            # Получаем все продукты по их ID
            products = await conn.fetch(
                "SELECT * FROM products WHERE id = ANY($1)", product_ids
            )

            return products  # Возвращаем список найденных продуктов

    except Exception as e:
        logging.exception(
            f"Ошибка при получении списка продуктов для пользователя {user_id}: {e}"
        )
        return []  # Возвращаем пустой список в случае ошибки


# -----------------------------------------------------------------------------------------------------------------------Удаляем товар у пользователя
# удаляем у пользователя и если больше никто такой товар не отслеживает, то удаляем из базы


async def delete_product_from_user(user_id, product_id):
    pool = await get_pool()  # Получаем пул соединений
    try:
        async with pool.acquire() as conn:
            # Удаляем продукт из user_products
            await conn.execute(
                "DELETE FROM user_products WHERE user_id = $1 AND product_id = $2",
                int(user_id),
                int(product_id),
            )

            # Удаляем продукт из пула, если это необходимо
            await delete_product_from_pool(user_id, product_id)

            # Проверяем, есть ли такие продукты у других пользователей
            result = await conn.fetch(
                "SELECT * FROM user_products WHERE product_id = $1", int(product_id)
            )

            # Если список пустой, удаляем продукт из основной таблицы и истории цен
            if not result:
                await conn.execute(
                    "DELETE FROM products WHERE id = $1", int(product_id)
                )
                await conn.execute(
                    "DELETE FROM product_price_history WHERE product_id = $1",
                    int(product_id),
                )

    except Exception as e:
        logging.exception(f"Ошибка при удалении продукта: {e}")
