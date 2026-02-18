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
