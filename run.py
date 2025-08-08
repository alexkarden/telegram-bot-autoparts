import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# Импорт переменных из файла config
from config import CHECKINTERVAL
from database import close_pool, init_db

# Импорт пользовательских функций
from handlers import router
from scripts_scheduler import price_update, rassilka_for_users


load_dotenv()
bot = Bot(token=os.getenv("TOKEN_TG"))
dp = Dispatcher()


async def main():
    # Создаем базу данных, если ее нет.
    await init_db()
    scheduler = AsyncIOScheduler(timezone="Europe/Minsk")
    # Запускаем проверку цен
    scheduler.add_job(price_update, trigger="interval", seconds=CHECKINTERVAL)
    # Запускаем рассылку для пользователей
    scheduler.add_job(
        rassilka_for_users,
        trigger="interval",
        seconds=CHECKINTERVAL,
        kwargs={
            "bot": bot,
        },
    )

    # Запускаем шейдулер
    scheduler.start()
    # Подключаем роутер
    dp.include_router(router)
    # Запускаем поллинг
    await dp.start_polling(bot)
    await close_pool()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        filename="py_log.log",
        filemode="w",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down...")  # Логируем, что происходит остановка
    except Exception as e:  # Обработка ошибок
        logging.exception("Unexpected error: %s", e)
