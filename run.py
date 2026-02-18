import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Импорт переменных из файла config
from config import CHECKINTERVAL
from database import close_pool, init_db
# Импорт пользовательских функций
from handlers import router
from scripts_scheduler import price_update_interval, rassilka_for_users, price_update_cron
from database_redis import update_redis_user_list_products_keyboard


load_dotenv()
bot = Bot(token=os.getenv("TOKEN_TG"))
dp = Dispatcher()


async def main():
    # Создаем базу данных, если ее нет.

    await init_db()
    await update_redis_user_list_products_keyboard()
    # раскоментить перед продом
    await price_update_interval()
    scheduler = AsyncIOScheduler(timezone="Europe/Minsk")
    # Запускаем проверку цен
    scheduler.add_job(
        price_update_interval, trigger="interval", seconds=CHECKINTERVAL, max_instances=1
    )
    scheduler.add_job(
        price_update_cron, trigger=CronTrigger(hour="3,9,15", minute="00"), max_instances=1
    )


    # Запускаем рассылку для пользователей
    scheduler.add_job(
        rassilka_for_users,
        trigger="interval",
        seconds=CHECKINTERVAL + 100,
        kwargs={
            "bot": bot,
        },
        max_instances=1,
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
