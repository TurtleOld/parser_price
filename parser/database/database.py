import json
from datetime import datetime
from parser.bot.config import bot
from parser.database.config import (
    AsyncSessionLocal,
    Message,
    PriceHistory,
    Product,
)
from parser.scripts.parser_dictionary import DictionaryParser
from parser.scripts.product_data import get_product_data
from parser.services import clean_and_extract_price

from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def insert_data(
    available,
    product_name,
    price,
    price_ozon,
    original_price,
    picture,
    user_id=None,
    url=None,
):
    async with AsyncSessionLocal() as session:
        try:
            # Проверка существования продукта по URL и telegram_user_id
            existing_product = await session.execute(
                select(Message).where(
                    (Message.url == url) & (Message.telegram_user_id == user_id)
                )
            )
            existing_product = existing_product.scalars().first()
            if existing_product:
                return "Этот продукт уже добавлен на отслеживание."

            # Создаём новое сообщение
            new_message = Message(
                telegram_user_id=user_id,
                url=url,
            )
            session.add(new_message)
            await session.flush()

            # Добавляем новый продукт к сообщению
            new_product = Product(
                available=available,
                url=url,
                product_name=product_name,
                latest_price=price,
                latest_price_ozon=price_ozon,
                original_price=original_price,
                picture=picture,
                message=new_message,
            )
            session.add(new_product)
            await session.commit()
            return (
                f"<pre>{product_name}</pre> успешно добавлен на отслеживание."
            )
        except Exception as e:
            await session.rollback()
            return f"Произошла ошибка добавления товара {e}"


async def update_price():
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

                product.latest_price = price
                product.latest_price_ozon = card_price
                product.original_price = original_price
                product.available = available
                product.picture = picture

                if product.latest_price != price:
                    message_text = (
                        f"Цена на товар '{product_name_dict['title']}' изменилась!\n"
                        f"Старая цена: {product.latest_price}₽\n"
                        f"Новая цена: {price}₽\n"
                        f"Ссылка на товар: https://www.ozon.ru/{url}"
                    )
                    await bot.send_message(user_id, message_text)

                new_price_history_entry = PriceHistory(
                    price=price,
                    price_ozon=card_price,
                    original_price=original_price,
                    updated_at=datetime.now(),
                )
                product.prices_history.append(new_price_history_entry)

        await session.commit()


async def get_data(user_id):
    async with AsyncSessionLocal() as session:
        results = (
            session.query(Message)
            .filter(Message.telegram_user_id == user_id)
            .all()
        )

        all_products = []

        for result in results:
            for product in result.products:
                formatted_info = format_product_info(product)
                all_products.append(formatted_info)

        return all_products


def format_product_info(product):
    # Проверка наличия необходимых данных о продукте
    availability = "Доступен" if product.available else "Недоступен"
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
    formatted_string = f"""
Доступность: {availability}
Наименование товара: {product_name}
Цена: {price} ₽
Цена по карте: {ozon_price} ₽
Первоначальная цена: {original_price} ₽
"""

    return formatted_string
