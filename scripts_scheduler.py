import logging

from aiogram import Bot

from database import (change_status_product, check_last_two_price_times,
                      check_price_product, get_list_product,
                      get_list_product_for_rassilka, get_list_users_for_rassilka,
                      min_max_price_product,)
from database_redis import update_redis_user_list_products_keyboard
from keyboards import user_info_product
from script import check_price, convert_date_to_str


async def price_update_interval():
    product_list = await get_list_product()

    product_list_interval =[]
    for product in product_list:
        if product[2] in ['onliner', 'wb']:
            product_list_interval.append(product)

    await check_price(product_list_interval)
    await update_redis_user_list_products_keyboard()



async def price_update_cron():
    product_list = await get_list_product()

    product_list_interval =[]
    for product in product_list:
        if product[2] in ['remzona', 'shate-mag', '21vek']:
            product_list_interval.append(product)

    await check_price(product_list_interval)
    await update_redis_user_list_products_keyboard()



async def rassilka_for_users(bot: Bot):
    try:
        product_list = await get_list_product_for_rassilka(1)
        # print(product_list)
        if product_list:
            for item in product_list:
                product_id = int(item[0])
                # print(item)
                result = await check_price_product(product_id)
                # print(result)
                timeadd = result[4]
                timestr = await convert_date_to_str(timeadd, 3)
                result2 = await check_last_two_price_times(product_id)
                min_max = await min_max_price_product(product_id)
                if min_max:
                    min_max_str = f"<b>Мин. / Макс. цена:</b> {round(float(min_max[0])/100,2)} / {round(float(min_max[1])/100,2)} BYN\n"
                    if result[3] == min_max[0]:
                        super_price = "🟢🟢🟢 Самая низкая цена\n"
                    else:
                        super_price = ""

                else:
                    if result[3]:
                        min_max_str = f"<b>Мин. / Макс. цена:</b> {round(float(result[3]/100), 2)} BYN\n"
                    else:
                        min_max_str = ""
                    super_price = ""

                # (result2)
                if result2[0] and result2[1]:
                    delta = round(float(result2[0]) / 100 - float(result2[1]) / 100, 2)
                else:
                    delta = 0

                if delta < 0:
                    deltamodul = 0 - delta
                    procent = deltamodul / float(result2[1]) * 10000
                    textdelta = f"🟢 Цена снизилась на {deltamodul} BYN  ( -{round(procent, 1)} %)"
                elif delta > 0:
                    deltamodul = delta
                    procent = deltamodul / float(result2[1]) * 10000
                    textdelta = f"🔴 Цена повысилась на {deltamodul} BYN  ( +{round(procent, 1)} %)"
                else:
                    textdelta = "Изменилось наличие"

                list_of_users = await get_list_users_for_rassilka(product_id)

                for user in list_of_users:
                    if result2[0] and result2[0] is not None:
                        cenatxt = f"<b>Цена:</b> {round(float(result2[0])/100,2)} BYN\n"
                    else:
                        cenatxt = ""

                    text = (
                        f"<b>Магазин:</b> {item[5]}\n"
                        f'<b>Товар:</b> <a href="{item[1]}">{item[2]}</a>\n'
                        f"<b>Статус:</b> {result[2]}\n\n"
                        f"{cenatxt}"
                        f"{super_price}"
                        f"{min_max_str}"
                        f"{textdelta}\n"
                        f"Обновлено: {timestr}"
                    )

                    threshold = user[3]

                    try:

                        if threshold and result2[0] < threshold:

                            await bot.send_photo(
                                chat_id=user[1],
                                photo=item[3],
                                caption=text,
                                reply_markup=await user_info_product(
                                    user[1], product_id
                                ),
                                parse_mode="HTML",
                            )
                        elif threshold and result2[0] >= threshold:
                            continue

                        else:

                            await bot.send_photo(
                                chat_id=user[1],
                                photo=item[3],
                                caption=text,
                                reply_markup=await user_info_product(
                                    user[1], product_id
                                ),
                                parse_mode="HTML",
                            )

                    except Exception as e:
                        logging.exception(
                            f"Ошибка при рассылке сообщения пользователю {user[1]}: {e}"
                        )  # Более конкретное сообщение

                await change_status_product(0, product_id)

    except Exception as e:
        logging.exception(f"Ошибка при рассылке: {e}")
