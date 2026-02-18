import json
import logging
import os

import redis
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

from database import get_all_users_for_redis
from keyboards import user_list_products_keyboard


load_dotenv()


host_redis = os.getenv("REDIS_HOST")
port_redis = int(os.getenv("REDIS_PORT"))
username_redis = os.getenv("REDIS_USERNAME")
password_redis = os.getenv("REDIS_PASSWORD")


r = redis.Redis(
    host=host_redis,
    port=port_redis,
    db=0,
    username=username_redis,
    password=password_redis,
    socket_timeout=2,
)


async def redis_user_list_products_keyboard(user_id):
    # ЗАПИСЫВАЕМ КЛАВИАТУРУ В РЕДИС
    inline_keyboard = await user_list_products_keyboard(user_id)
    redis_key = f"redis_{user_id}_productlist"
    out = []
    # Если получили объект InlineKeyboardMarkup, берем его inline_keyboard
    if isinstance(inline_keyboard, InlineKeyboardMarkup):
        inline_keyboard = inline_keyboard.inline_keyboard

    # Если случайно получили JSON-строку — распарсим
    if isinstance(inline_keyboard, str):
        try:
            inline_keyboard = json.loads(inline_keyboard)
        except json.JSONDecodeError:
            logging.exception(
                "Ожидался список рядов, но получили строку, не являющуюся JSON"
            )
            inline_keyboard = []

    for row in inline_keyboard or []:
        out_row = []
        for btn in row:
            # Если это уже словарь с нужными полями
            if isinstance(btn, dict):
                text = btn.get("text") or btn.get("label") or str(btn)
                callback = btn.get("callback_data")
            # aiogram button
            elif isinstance(btn, InlineKeyboardButton):
                text = btn.text
                callback = getattr(btn, "callback_data", None)
            # простая строка — используем как текст
            elif isinstance(btn, str):
                text = btn
                callback = None
            # кортеж/список в виде (text, callback)
            elif isinstance(btn, (list, tuple)) and len(btn) >= 1:
                text = str(btn[0])
                callback = btn[1] if len(btn) > 1 else None
            else:
                # fallback — преобразуем в строку
                text = str(btn)
                callback = None

            out_row.append({"text": text, "callback_data": callback})
        out.append(out_row)

    r.set(redis_key, json.dumps(out, ensure_ascii=False))


async def get_redis_user_list_products_keyboard(user_id):
    # ПОЛУЧАЕМ КЛАВИАТУРУ ИЗ РЕДИС
    redis_key = f"redis_{user_id}_productlist"
    s = r.get(redis_key)
    if not s:
        return None
    data = json.loads(s)
    rows = []
    for row in data:
        rows.append(
            [
                InlineKeyboardButton(**{k: v for k, v in btn.items() if v is not None})
                for btn in row
            ]
        )
    #print(InlineKeyboardMarkup(inline_keyboard=rows))
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def update_redis_user_list_products_keyboard():
    user_list = await get_all_users_for_redis()
    for user in user_list:
        await redis_user_list_products_keyboard(user["user_id"])
