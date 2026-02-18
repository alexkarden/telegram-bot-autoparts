import os
import pathlib

import matplotlib.pyplot as plt
import pandas as pd

from database import get_all_price_times, get_product_from_id
from script import convert_date_to_str


async def create_image_graph(product_id):
    x = []
    y = []
    output_dir = "export/graphs"

    # Получаем данные цен
    xy = await get_all_price_times(product_id)

    # Проверка на наличие данных
    if not xy or len(xy) == 0:

        return False

    # Получаем информацию о продукте
    info_product = await get_product_from_id(product_id)

    # Проверяем наличие информации о продукте
    if not info_product or len(info_product) < 6:

        return False

    title = info_product[2]
    legenda = f"Изменение цены в магазине {info_product[5]} с "
    # print(xy)

    # Преобразуем дату
    start_time = str(await convert_date_to_str(xy[0][2], 3))

    # Формируем данные для графика
    for item in xy:
        x.append(item[0])
        y.append(item[1]/100)

    # Строим график
    plt.plot(x, y, color="blue", marker="o", markersize=3)
    plt.xticks([])  # Убираем метки оси X
    plt.xlabel(legenda + start_time, fontsize=10)  # Подпись для оси X
    plt.ylabel("Цена, BYN")  # Подпись для оси Y
    plt.title(title, fontsize=7)

    # Создаем директорию, если она не существует
    os.makedirs(output_dir, exist_ok=True)

    # Сохраняем график в файл
    try:
        file_path = os.path.join(output_dir, f"{product_id}.png")
        plt.savefig(
            file_path, format="png", dpi=300
        )  # Сохранение в формате PNG с разрешением 300 dpi
        # print(f"График успешно сохранен: {file_path}")  # Успешная запись файла
        return True
    except Exception:

        return False
    finally:
        plt.close()  # Закрываем график, чтобы освободить ресурсы


async def create_exel(product_id):
    a1 = []
    a2 = []
    a3 = []
    output_dir = "export/exels"

    # Получаем данные цен
    a1a2a3 = await get_all_price_times(product_id)

    # Проверка на наличие данных
    if not a1a2a3 or len(a1a2a3) == 0:

        return False

    # Получаем информацию о продукте
    info_product = await get_product_from_id(product_id)

    # Проверяем наличие информации о продукте
    if not info_product or len(info_product) < 6:

        return False

    # Формируем данные для excel
    for item in a1a2a3:
        a1.append(item[0])
        # Преобразуем дату
        start_time = str(await convert_date_to_str(item[2], 3))
        a2.append(start_time)
        if item[1]:
            a3.append(float(item[1])/100)
        else:
            a3.append('')

    data = {"№п.п": a1, "Дата": a2, "Цена": a3}
    df = pd.DataFrame(data)

    # Убедимся, что директория для сохранения существует
    os.makedirs(output_dir, exist_ok=True)
    output_file_path = os.path.join(output_dir, f"{product_id}.xlsx")

    try:
        df.to_excel(output_file_path, index=False)  # Сохраняем файл Excel без индексов

    except Exception:

        return False

    return True  # Возвращаем True для успешного завершения


async def delete_file(file_path):
    try:
        pathlib.Path(file_path).unlink()
        return True
    except Exception:
        return False
