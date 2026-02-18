import logging
import pathlib
import time

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from config import LISTOFADMINS
from database import (add_new_product, add_threshold, add_to_pool, add_user_db,
                      append_product_to_pool, check_pool_product, check_price_product,
                      delete_product_from_pool, delete_product_from_user,
                      get_product_from_id, get_threshold, min_max_price_product, min_price_product, )
from database_redis import (get_redis_user_list_products_keyboard,
                            redis_user_list_products_keyboard,
                            update_redis_user_list_products_keyboard,)
from keyboards import (key_under_exel, key_under_graph, key_under_threshold,
                       main_menu_my_products_keyboard_inline, product_delete_yes,
                       start_keyboard_inline, user_info_product,
                       user_list_pool_add_keyboard,
                       user_list_product_from_pool_keyboard,)
from script import convert_date_to_str, is_link_belongs_to_site
from script_export import create_exel, create_image_graph, delete_file


class Reg(StatesGroup):
    threshold = State()
    product_id = State()
    developer = State()


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id in LISTOFADMINS:

        welcome_text = (
            f"👋 <b>Добро пожаловать, {message.from_user.first_name}!</b>\n"
            f"\n"
            f"🔅 С помощью этого бота вы сможете отследить изменение цены на автозапчасти в Интернет-магазинах:\n"
            f"21vek.by\n"
            f"onliner.by\n"
            f"remzona.by\n"
            f"shate-mag.by\n"
            f"wildberries.by\n"
            f"\n"
            f"🔅 Для начала отслеживания цены на товар отправьте боту ссылку на товар.\n"
        )
        # Записываем пользователя в базу
        await add_user_db(
            int(message.from_user.id),
            message.from_user.first_name,
            message.from_user.last_name,
            message.from_user.username,
        )
        await message.answer(
            welcome_text, reply_markup=start_keyboard_inline, parse_mode=ParseMode.HTML
        )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    if message.from_user.id in LISTOFADMINS:
        await state.clear()

        text = (
            "<b>☑️ Главное меню</b>\n\n"
            "🔅 Мои товары - <i>список отслеживаемых товаров</i>\n\n"
            "🔅 Помощь - <i>полезная информация о боте</i>\n\n"
            "🔅 Настройки - <i>глобальные настройки для всех отслеживаемых товаров</i>"
        )

        await message.answer(
            text=text, reply_markup=start_keyboard_inline, parse_mode=ParseMode.HTML
        )


@router.message(Reg.threshold)
async def porog(message: Message, state: FSMContext):
    if message.from_user.id in LISTOFADMINS:

        # Обновляем данные состояния
        await state.update_data(threshold=message.text)

        # Получаем данные состояния
        data = await state.get_data()

        # Извлекаем значение по ключу 'threshold'
        number_str = data.get("threshold", "").replace(",", ".")
        product_id = data.get("product_id", "")

        # Преобразуем строку в число с плавающей точкой
        try:
            number_rub = round(float(number_str), 2)
            print(number_rub)
            number_kop = int(number_rub * 100)
            print(number_kop)

            await add_threshold(message.from_user.id, product_id, number_kop)
            await message.answer(
                f"Порог цены установлен в {number_rub:.2f} BYN",
                reply_markup=await key_under_threshold(product_id, 2),
                parse_mode=ParseMode.HTML,
            )
        except ValueError:
            await message.answer("Попробуйте еще раз", parse_mode=ParseMode.HTML)

        await state.clear()


@router.message()
async def all_message(message: Message, state: FSMContext):
    if message.from_user.id in LISTOFADMINS:
        await state.clear()
        try:
            text = str(message.text)
            result = await is_link_belongs_to_site(text)

            if result and result[0] and result[1]:
                current_time = int(time.time())

                await add_new_product(
                    result[1],
                    result[0],
                    result[2],
                    result[3],
                    result[4],
                    current_time,
                    0,
                    message.from_user.id,
                    result[5],
                )

                texttg = f"Товар <i><b>'{result[0]}'</b></i> добавлен и отслеживается."
                await update_redis_user_list_products_keyboard()
                await redis_user_list_products_keyboard(message.from_user.id)
                await message.answer(
                    texttg,
                    reply_markup=start_keyboard_inline,
                    parse_mode=ParseMode.HTML,
                )

            else:
                await message.answer(
                    "Что-то пошло не так, например Вы прислали некоректную ссылку. Попробуйте прислать другую ссылку",
                    parse_mode=ParseMode.HTML,
                )
        except Exception as e:
            logging.exception(
                f"Ошибка при обработке ссылки и записи нового товара в базу : {e}"
            )
            await message.answer(
                f"Ошибка при обработке ссылки и записи нового товара в базу : {e}",
                parse_mode=ParseMode.HTML,
            )


@router.callback_query()
async def callback_query(callback: CallbackQuery, state: FSMContext):
    if callback.message.chat.id in LISTOFADMINS:
        data = callback.data
        if data == "Мои товары":

            await state.clear()
            reply_markup_check = await get_redis_user_list_products_keyboard(
                callback.message.chat.id
            )

            if str(reply_markup_check) != "inline_keyboard=[]":
                text = (
                    "<b>Список отслеживаемых товаров:</b>\n"
                    "🌟 - В наличии.\n"
                    "❌ - Нет в наличии.\n"
                    "✅ - В наличии и цена супер!"
                )
                reply_markup = reply_markup_check
            else:
                text = "🔅 <b>Вы еще не добавили ни одного товара</b>"
                reply_markup = start_keyboard_inline
            await callback.message.answer(
                text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
            )

        elif data.startswith("id_"):
            await state.clear()
            product_id = data.split("_")[1]
            product_info = await get_product_from_id(product_id)
            product_price = await check_price_product(product_id)
            min_max = await min_max_price_product(product_id)
            print(min_max)

            if min_max:
                min_max_str = f"<b>Мин. / Макс. цена:</b> {round(float(min_max[0])/100, 2)} / {round(float(min_max[1])/100, 2)} BYN\n"
                if product_price[3] == min_max[0]:
                    super_price = "✅ Самая низкая цена\n"
                else:
                    super_price = ""

            else:
                if product_price[3]:
                    min_max_str = f"<b>Мин. / Макс. цена:</b> {round(float(product_price[3])/100, 2)} BYN\n"
                else:
                    min_price = await min_price_product(product_id)
                    if min_price:
                        min_max_str = f"<b>Мин. / Макс. цена:</b> {round(float(min_price)/100, 2)} BYN\n"
                    else:
                        min_max_str = ""
                super_price = ""

            photo = product_info[3]
            timeadd = product_price[4]
            timestr = await convert_date_to_str(timeadd, 3)

            if product_price[3]:
                text_price = (
                    f"<b>Цена:</b> {round(float(product_price[3])/100, 2)} BYN\n"
                )
            else:
                text_price = ""

            caption = (
                f"<b>Магазин:</b> {product_info[5]}\n"
                f'<b>Товар:</b> <a href="{product_info[1]}">{product_info[2]}</a>\n'
                f"<b>Статус:</b> {product_price[2]}\n\n"
                f"{text_price}"
                f"{super_price}"
                f"{min_max_str}"
                f"Последнее изменение: {timestr}"
            )
            try:
                await callback.message.answer_photo(
                    photo=photo,
                    caption=caption,
                    reply_markup=await user_info_product(
                        callback.message.chat.id, product_id
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                await callback.message.answer(
                    text=caption,
                    reply_markup=await user_info_product(
                        callback.message.chat.id, product_id
                    ),
                    parse_mode=ParseMode.HTML,
                )  # Сообщаем пользователю об ошибке

        elif data.startswith("delete_"):  # Исправлено
            product_id = data.split("_")[1]
            await callback.message.answer(
                "Вы действительно хотите удалить товар",
                reply_markup=await product_delete_yes(product_id),
                parse_mode=ParseMode.HTML,
            )
            await update_redis_user_list_products_keyboard()
            await redis_user_list_products_keyboard(callback.message.chat.id)

        elif data.startswith("createpool_"):  # Исправлено
            product_id = data.split("_")[1]
            if await check_pool_product(callback.message.chat.id, product_id) is False:
                await add_to_pool(callback.message.chat.id, product_id)
                await update_redis_user_list_products_keyboard()
                await callback.message.answer(
                    "Cоздан новый пул из этого товара",
                    reply_markup=main_menu_my_products_keyboard_inline,
                    parse_mode=ParseMode.HTML,
                )

        elif data.startswith("addpool_"):  # Исправлено
            product_id = data.split("_")[1]

            if await check_pool_product(callback.message.chat.id, product_id) is False:
                await callback.message.answer(
                    "Выберите пул в который добавить товар",
                    reply_markup=await user_list_pool_add_keyboard(
                        callback.message.chat.id, product_id
                    ),
                    parse_mode=ParseMode.HTML,
                )
            await update_redis_user_list_products_keyboard()

        elif data.startswith("appendpool_"):  # Исправлено
            pool_id = data.split("_")[1]
            product_id = data.split("_")[2]

            if await check_pool_product(callback.message.chat.id, product_id) is False:
                await append_product_to_pool(
                    callback.message.chat.id, pool_id, product_id
                )
                await update_redis_user_list_products_keyboard()

                await callback.message.answer(
                    "Товар добавлен в пул",
                    reply_markup=main_menu_my_products_keyboard_inline,
                    parse_mode=ParseMode.HTML,
                )

        elif data.startswith("pool_"):
            await state.clear()  # Исправлено
            pool_id = data.split("_")[1]

            await callback.message.answer(
                "товары в пуле",
                reply_markup=await user_list_product_from_pool_keyboard(
                    callback.message.chat.id, pool_id
                ),
                parse_mode=ParseMode.HTML,
            )  # Сообщаем пользователю об ошибке
            await redis_user_list_products_keyboard(callback.message.chat.id)

        elif data.startswith("delpool_"):
            await state.clear()  # Исправлено
            product_id = data.split("_")[1]
            await delete_product_from_pool(callback.message.chat.id, product_id)
            await update_redis_user_list_products_keyboard()

            await callback.message.answer(
                "Товар удален из пула",
                reply_markup=main_menu_my_products_keyboard_inline,
                parse_mode=ParseMode.HTML,
            )

        elif data.startswith("deleteyes_"):
            await state.clear()  # Исправлено
            product_id = data.split("_")[1]
            await delete_product_from_user(callback.message.chat.id, product_id)
            await callback.message.answer(
                "Товар удален",
                reply_markup=start_keyboard_inline,
                parse_mode=ParseMode.HTML,
            )
            await update_redis_user_list_products_keyboard()

        elif data.startswith("graph_"):  # Исправлено
            await state.clear()
            product_id = data.split("_")[1]

            create_check = await create_image_graph(product_id)

            if create_check:
                # Путь к сохраненному изображению
                image_path = f"export/graphs/{product_id}.png"

                # Проверяем, существует ли файл
                if pathlib.Path(image_path).exists():
                    # Создаем объект для фотографии

                    photo = FSInputFile(image_path)

                    # Отправляем фотографию с текстом
                    await callback.message.answer_photo(
                        photo=photo,
                        reply_markup=await key_under_graph(product_id),
                        parse_mode=ParseMode.HTML,
                    )

                else:
                    await callback.message.answer(
                        "Извините, график не найден. Попробуйте позже.",
                        reply_markup=await key_under_graph(product_id),
                        parse_mode=ParseMode.HTML,
                    )
                await delete_file(image_path)

            else:
                await callback.message.answer(
                    "Извините, не удалось создать график. Попробуйте позже.",
                    reply_markup=await key_under_graph(product_id),
                    parse_mode=ParseMode.HTML,
                )

        elif data.startswith("exel_"):
            await state.clear()  # Исправлено
            product_id = data.split("_")[1]
            create_check = await create_exel(product_id)
            if create_check:
                # Путь к сохраненному файлу exel
                exel_path = f"export/exels/{product_id}.xlsx"

                # Проверяем, существует ли файл
                if pathlib.Path(exel_path).exists():
                    # Создаем объект для файла exel

                    exel = FSInputFile(exel_path)

                    # Отправляем документ
                    await callback.message.answer_document(
                        exel,
                        reply_markup=await key_under_exel(product_id),
                        parse_mode=ParseMode.HTML,
                    )

                else:
                    await callback.message.answer(
                        "Извините, файл Exel не найден. Попробуйте позже.",
                        reply_markup=await key_under_exel(product_id),
                        parse_mode=ParseMode.HTML,
                    )
                await delete_file(exel_path)

            else:
                await callback.message.answer(
                    "Извините, не удалось создать файл Exel. Попробуйте позже.",
                    reply_markup=await key_under_exel(product_id),
                    parse_mode=ParseMode.HTML,
                )

        elif data.startswith("threshold_"):

            product_id = data.split("_")[1]
            await state.set_state(Reg.product_id)
            await state.update_data(product_id=product_id)

            await state.set_state(Reg.threshold)
            threshold = await get_threshold(callback.message.chat.id, product_id)
            if threshold:
                text_threshold = (
                    f"Сейчас порог цены установлен в {float(threshold)/100} BYN\n"
                    f"Для установки нового порога цены отправьте сообщение содержащее цену "
                    f"или нажмите сброс, чтобы сбросить порог цены"
                )
                version = 1
            else:
                text_threshold = (
                    "Для установки порога цены отправьте сообщение содержащее цену"
                )
                version = 2
            await callback.message.answer(
                f"{text_threshold}",
                reply_markup=await key_under_threshold(product_id, version),
                parse_mode=ParseMode.HTML,
            )

        elif data.startswith("delthreshold_"):
            product_id = data.split("_")[1]
            await state.set_state(Reg.product_id)
            await state.update_data(product_id=product_id)

            await state.set_state(Reg.threshold)

            await add_threshold(callback.message.chat.id, product_id, None)
            text_threshold = (
                "Порог цены сброшен. \n"
                "Для установки нового порога цены отправьте сообщение содержащее цену."
            )
            await callback.message.answer(
                f"{text_threshold}",
                reply_markup=await key_under_threshold(product_id, 2),
                parse_mode=ParseMode.HTML,
            )

        elif data == "Помощь":  # Исправлено
            text_help = (
                f"Помощь\n\n"
                f"🔅 С помощью этого бота вы сможете отследить изменение цены на понравившиеся товары в Интернет-магазинах:\n"
                f"21vek.by\n"
                f"onliner.by\n"
                f"remzona.by\n"
                f"shate-mag.by\n"
                f"wildberries.by\n"
                f"\n"
                f"1️⃣ Для начала отслеживания цены на товар отправьте боту ссылку на товар.\n"
                f"2️⃣ Если после отправки ссылки товар не добавился, то изучите саму ссылку и попробуйте удалить лишние символы в ссылке.\n"
                f"3️⃣ После успешного добавления товара, он начинает отслеживаться, как только измениться стоимость или статус (например статус  'Нет в наличии' сменится на 'В наличии'), Вы получите уведомление.\n"
            )
            await callback.message.answer(
                text_help, reply_markup=start_keyboard_inline, parse_mode=ParseMode.HTML
            )

        elif data == "Главное меню":  # Исправлено
            text = (
                "<b>☑️ Главное меню</b>\n\n"
                "🔅 Мои товары - <i>список отслеживаемых товаров</i>\n\n"
                "🔅 Помощь - <i>полезная информация о боте</i>\n\n"
                "🔅 Настройки - <i>глобальные настройки для всех отслеживаемых товаров</i>"
            )

            await callback.message.answer(
                text=text, reply_markup=start_keyboard_inline, parse_mode=ParseMode.HTML
            )
