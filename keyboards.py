import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    check_pool_product, check_price_product, get_list_pools,
    get_list_product_from_pools, get_min_pool_price, get_product_from_id,
    get_user_list_product, min_max_price_product,)


# -----------------------------------------------------------------------------------------------------------------------кнопки
button_main_menu = InlineKeyboardButton(
    text="☑️ Главное меню", callback_data="Главное меню"
)
button_my_products = InlineKeyboardButton(
    text="🛍 Мои товары", callback_data="Мои товары"
)
button_help = InlineKeyboardButton(text="ℹ️ Помощь", callback_data="Помощь")
button_settings = InlineKeyboardButton(text="⚙️ Настройки", callback_data="Настройки")


# -----------------------------------------------------------------------------------------------------------------------клавиатура на старте
start_keyboard_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [button_my_products],
        [button_help],
    ]
)


# -----------------------------------------------------------------------------------------------------------------------клавиатура главное меню

main_menu_my_products_keyboard_inline = InlineKeyboardMarkup(
    inline_keyboard=[[button_my_products], [button_main_menu]]
)

# -----------------------------------------------------------------------------------------------------------------------клавиатура мои товары + главное меню

main_menu_keyboard_inline = InlineKeyboardMarkup(inline_keyboard=[[button_main_menu]])


# -----------------------------------------------------------------------------------------------------------------------клавиатура списка пулов + товары
async def user_list_products_keyboard(user_id):
    keyboard = []

    try:
        pools = await get_list_pools(user_id)
        # Проверка на получение пулов
        if not pools:
            keyboard = []
        else:
            for pool in pools:
                title = pool[3]
                pool_id = pool[0]
                pool_min_price_list = await get_min_pool_price(user_id, pool_id)
                pool_min_price = pool_min_price_list[0]

                product_min_price = pool_min_price_list[1]

                if pool_min_price:
                    pool_min_price_str = str(round(float(pool_min_price) / 100, 2))
                    if pool_min_price == product_min_price and pool_min_price is not None:
                        circle = "✅ "
                    elif pool_min_price > product_min_price:
                        circle = "🌟 "
                    else:
                        circle = ""
                else:

                    circle = "❌ "
                    pool_min_price_str = ""

                pool_id = f"pool_{pool_id!s}"

                text_keyboard = f"{circle}ПУЛ - {pool_min_price_str} -{title}"
                button = InlineKeyboardButton(text=text_keyboard, callback_data=pool_id)
                keyboard.append([button])  # Каждая кнопка в отдельной строке

        products = await get_user_list_product(user_id)

        # Проверка на получение продуктов
        if not products:
            return InlineKeyboardMarkup(
                inline_keyboard=[]
            )  # Возвращаем пустую клавиатуру, если нет продуктов

        for product in products:
            if await check_pool_product(user_id, product[0]) == False:
                title = product[2]

                price = await check_price_product(product[0])

                min_max = await min_max_price_product(product[0])
                product_id = "id_" + str(product[0])  # Преобразуем product_id в строку
                # print(product_id)
                try:
                    if round(price[3], 2) == None or round(price[3], 2) == 0:
                        circle = "❌ "
                    elif min_max:
                        if round(price[3], 2) == round(min_max[0], 2):
                            circle = "✅ "
                        else:
                            circle = "🌟 "
                    else:
                        circle = "🌟 "
                except:
                    circle = "❌ "
                try:
                    text_keyboard = (
                        f"{circle} {round(float(price[3])/100,2)} - {product[5]} - {title}"
                        )
                except:
                    logging.exception('ошибка text_keyboard')
                    text_keyboard = (
                        f"{circle} - {product[5]} - {title}"
                        )
                button = InlineKeyboardButton(
                    text=text_keyboard, callback_data=product_id
                )
                keyboard.append([button])  # Каждая кнопка в отдельной строке

    except Exception as e:
        logging.exception(f"An error occurred - user_list_products_keyboard: {e}")  # Логирование ошибки
        return InlineKeyboardMarkup(
            inline_keyboard=[]
        )  # Возвращаем пустую клавиатуру при ошибке

    keyboard.append([button_main_menu])
    # Возвращаем созданную клавиатуру
    return keyboard


# -----------------------------------------------------------------------------------------------------------------------клавиатура списков пулов
async def user_list_pool_add_keyboard(user_id, product_id):
    keyboard = []
    try:
        pools = await get_list_pools(user_id)
        # print(f"Список пулов {pools}")

        # Проверка на получение пулов
        if not pools:
            return InlineKeyboardMarkup(
                inline_keyboard=[]
            )  # Возвращаем пустую клавиатуру, если нет продуктов

        for pool in pools:
            title = pool[3]
            pool_id = pool[0]
            append_id = f"appendpool_{pool_id!s}_{product_id!s}"  # Преобразуем pool_id и product_id в строку

            text_keyboard = f"{title}"
            button = InlineKeyboardButton(text=text_keyboard, callback_data=append_id)
            keyboard.append([button])  # Каждая кнопка в отдельной строке

    except Exception as e:
        logging.exception(f"An error occurred - user_list_pool_add_keyboard: {e}")  # Логирование ошибки
        return InlineKeyboardMarkup(
            inline_keyboard=[]
        )  # Возвращаем пустую клавиатуру при ошибке

    keyboard.append([button_my_products])
    keyboard.append([button_main_menu])
    # Возвращаем созданную клавиатуру
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# -----------------------------------------------------------------------------------------------------------------------клавиатура товаров в пуле
async def user_list_product_from_pool_keyboard(user_id, poll_id):
    keyboard = []
    try:
        products = await get_list_product_from_pools(user_id, poll_id)


        # Проверка на получение продуктов из пулов
        if not products:
            return InlineKeyboardMarkup(
                inline_keyboard=[]
            )  # Возвращаем пустую клавиатуру, если продуктов нет

        # print(f"Вызов из функции клавиатуры {products}")

        for product in products:
            product_id = product[2]
            product_info = await get_product_from_id(product_id)
            product_title = product_info[2]
            market = product_info[5]

            price = await check_price_product(product[2])

            min_max = await min_max_price_product(product[2])
            if price[3] == None or price[3] == 0:
                circle = "❌ "
                text_keyboard = f"{circle} - {market} - {product_title}"
            elif min_max and price[3]:
                if price[3] == min_max[0]:
                    circle = "✅ "
                    text_keyboard = f"{circle} {round(float(price[3]) / 100, 2)} - {market} - {product_title}"
                else:
                    circle = "🌟 "
                    text_keyboard = f"{circle} {round(float(price[3]) / 100, 2)} - {market} - {product_title}"
            elif price[3]:
                circle = "🌟 "
                text_keyboard = f"{circle} {round(float(price[3]) / 100, 2)} - {market} - {product_title}"


            button = InlineKeyboardButton(
                text=text_keyboard, callback_data=f"id_{product_id!s}"
            )
            keyboard.append([button])  # Каждая кнопка в отдельной строке

        # Добавляем кнопки для "Мои продукты" и "Главное меню"

        keyboard.append([button_my_products])
        keyboard.append([button_main_menu])

        # Возвращаем созданную клавиатуру

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    except Exception as e:
        logging.exception(f"An error occurred: ошибка тут {e}")  # Логирование ошибки
        return InlineKeyboardMarkup(
            inline_keyboard=[]
        )  # Возвращаем пустую клавиатуру при ошибке


# -----------------------------------------------------------------------------------------------------------------------клавиатура в карточке товара
async def user_info_product(user_id, product_id):
    if await check_pool_product(user_id, product_id) == False:
        pool_key = [
            InlineKeyboardButton(
                text="Создать новый пул", callback_data=f"createpool_{product_id}"
            ),
            InlineKeyboardButton(
                text="Добавить в пул", callback_data=f"addpool_{product_id}"
            ),
        ]
    else:
        pool_key = [
            InlineKeyboardButton(
                text="Удалить из пула", callback_data=f"delpool_{product_id}"
            )
        ]

    user_info_product_key = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="График цены", callback_data=f"graph_{product_id}"
                ),
                InlineKeyboardButton(
                    text="История цен в Exel", callback_data=f"exel_{product_id!s}"
                ),
            ],
            pool_key,
            [
                InlineKeyboardButton(
                    text="Порог цены", callback_data=f"threshold_{product_id}"
                ),
                InlineKeyboardButton(
                    text="Удалить товар", callback_data=f"delete_{product_id}"
                ),
            ],
            [button_my_products],
            [button_main_menu],
        ]
    )
    return user_info_product_key


# -----------------------------------------------------------------------------------------------------------------------клавиатура под графиком
async def key_under_graph(product_id):

    user_under_graph_key = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Карточка товара", callback_data=f"id_{product_id!s}"
                ),
                InlineKeyboardButton(
                    text="История цен в Exel", callback_data=f"exel_{product_id!s}"
                ),
            ],
            [button_my_products],
            [button_main_menu],
        ]
    )
    return user_under_graph_key


# -----------------------------------------------------------------------------------------------------------------------клавиатура под exel
async def key_under_exel(product_id):

    user_under_exel_key = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Карточка товара", callback_data=f"id_{product_id!s}"
                ),
                InlineKeyboardButton(
                    text="График цены", callback_data=f"graph_{product_id}"
                ),
            ],
            [button_my_products],
            [button_main_menu],
        ]
    )
    return user_under_exel_key


# -----------------------------------------------------------------------------------------------------------------------клавиатура под порогом цен
async def key_under_threshold(product_id, version):
    if version == 1:
        user_under_threshold_key = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Назад", callback_data=f"id_{product_id!s}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Сброс", callback_data=f"delthreshold_{product_id!s}"
                    )
                ],
                [button_my_products],
                [button_main_menu],
            ]
        )
    elif version == 2:
        user_under_threshold_key = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Назад", callback_data=f"id_{product_id!s}"
                    )
                ],
                [button_my_products],
                [button_main_menu],
            ]
        )

    return user_under_threshold_key


# -----------------------------------------------------------------------------------------------------------------------клавиатура под рассылкой
async def key_under_rassilka(product_id):

    user_under_rassilka_key = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="График цены", callback_data=f"graph_{product_id}"
                ),
                InlineKeyboardButton(
                    text="История цен в Exel", callback_data=f"exel_{product_id!s}"
                ),
            ],
            [button_my_products],
            [button_main_menu],
        ]
    )
    return user_under_rassilka_key


# -----------------------------------------------------------------------------------------------------------------------клавиатура подтверждения удаления товаров
async def product_delete_yes(product_id):
    user_delete_product_key = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Нет", callback_data="Мои товары"),
                InlineKeyboardButton(
                    text="Да", callback_data=f"deleteyes_{product_id}"
                ),
            ],
            [button_main_menu],
        ]
    )
    return user_delete_product_key
