import re
import json
from datetime import datetime
from parser.bot.config import bot
from parser.database.config import AsyncSessionLocal
from parser.database.config import Message, PriceHistory, Product
from parser.scripts.parser_dictionary import DictionaryParser
from parser.scripts.product_data import get_product_data
from sqlalchemy import select
from sqlalchemy.orm import selectinload


def clean_and_extract_price(price_string):
    # Удаляем тонкие пробелы (\u2009)
    cleaned_string = price_string.replace("\u2009", "")

    # Извлекаем числовую часть
    number_part = "".join(re.findall(r"\d+", cleaned_string))

    # Преобразуем в число
    return int(number_part)


async def add_product_to_monitoring(
    available,
    product_name,
    price,
    price_ozon,
    original_price,
    picture,
    store,
    user_id=None,
    url=None,
):
    async with AsyncSessionLocal() as session:
        try:
            existing_product = await session.execute(
                select(Message).where(
                    (Message.url == url) & (Message.telegram_user_id == user_id)
                )
            )
            existing_product = existing_product.scalars().first()
            if existing_product:
                return "Этот продукт уже добавлен на отслеживание."

            new_message = Message(
                telegram_user_id=user_id,
                url=url,
            )
            session.add(new_message)
            await session.flush()

            new_product = Product(
                available=available,
                url=url,
                product_name=product_name,
                latest_price=price,
                latest_price_ozon=price_ozon,
                original_price=original_price,
                picture=picture,
                messages=new_message,
                store=store,
            )
            session.add(new_product)
            await session.commit()
            return (
                f"<pre>{product_name}</pre> успешно добавлен на отслеживание."
            )
        except Exception as e:
            await session.rollback()
            return f"Произошла ошибка добавления товара {e}"


async def update_product_to_monitoring():
    try:
        async with AsyncSessionLocal() as session:
            results = await session.execute(
                select(Message).options(
                    selectinload(Message.products).selectinload(
                        Product.prices_history
                    )
                )
            )
            messages = results.scalars().all()

            for message in messages:
                user_id = message.telegram_user_id
                for product in message.products:
                    url = message.url
                    data = await get_product_data(url)
                    parse = DictionaryParser(data)
                    product_name_data = parse.find_key(
                        "webProductHeading-3385933-default-1"
                    )
                    image = parse.find_key("webGallery-3311629-default-1")

                    picture_dict = json.loads(image[0])
                    picture = picture_dict["images"][0]["src"]
                    product_name_dict = json.loads(product_name_data[0])
                    f_key = parse.find_key("webPrice-3121879-default-1")
                    data_dict = json.loads(f_key[0])
                    available = data_dict["isAvailable"]
                    price = clean_and_extract_price(data_dict["price"])
                    card_price = clean_and_extract_price(data_dict["cardPrice"])
                    original_price = clean_and_extract_price(
                        data_dict["originalPrice"]
                    )

                    if product.latest_price > price:
                        decrease_price = product.latest_price - price
                        percentage_decrease = (
                            decrease_price / product.latest_price
                        ) * 100
                        message_text = (
                            f'<b>Товар:</b> <a href="https://www.ozon.ru{product.url}">{product_name_dict['title']}</a>\n\n'
                            f'Цена по карте Ozon: {card_price} ₽\n'
                            f'Обычная цена: {price} ₽\n\n'
                            f'Стал дешевле на {abs(decrease_price)} ₽ (&#9660; {abs(percentage_decrease):.2f}%)\n'
                        )
                        await bot.send_photo(
                            user_id,
                            photo=product.picture,
                            caption=message_text,
                            show_caption_above_media=True,
                        )
                    elif product.latest_price < price:
                        increase_price = product.latest_price - price
                        percentage_increase = (
                            increase_price / product.latest_price
                        ) * 100
                        message_text = (
                            f'<b>Товар:</b> <a href="https://www.ozon.ru{product.url}">{product_name_dict['title']}</a>\n\n'
                            f'Цена по карте Ozon: {card_price} ₽\n'
                            f'Обычная цена: {price} ₽\n\n'
                            f'Стал дороже на {abs(increase_price)} ₽ (&#9650; {abs(percentage_increase):.2f}%)\n'
                        )
                        await bot.send_photo(
                            user_id,
                            photo=product.picture,
                            caption=message_text,
                            show_caption_above_media=True,
                        )

                    product.latest_price = price
                    product.latest_price_ozon = card_price
                    product.original_price = original_price
                    product.available = available
                    product.picture = picture

                    new_price_history_entry = PriceHistory(
                        price=price,
                        price_ozon=card_price,
                        original_price=original_price,
                        updated_at=datetime.now(),
                    )
                    product.prices_history.append(new_price_history_entry)

            await session.commit()
    except Exception as err:
        print(f'Error update product{err}')


def format_product_info(product):
    # Проверка наличия необходимых данных о продукте
    product_name = (
        product.product_name if product.product_name else "Неизвестный товар"
    )
    price = (
        product.latest_price
        if product.latest_price is not None
        else "Неизвестная цена"
    )
    ozon_price = (
        product.latest_price_ozon
        if product.latest_price_ozon is not None
        else "Неизвестная цена"
    )
    original_price = (
        product.original_price
        if product.original_price is not None
        else "Неизвестная цена"
    )

    # Форматируем информацию о продукте
    return f"""
<b>Товар:</b> <a href="https://www.ozon.ru{product.url}">{product_name}</a>

<b>Обычная цена:</b> {price} ₽
<b>Цена по карте Ozon:</b> {ozon_price} ₽
<b>Первоначальная цена:</b> {original_price} ₽
"""