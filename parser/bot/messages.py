import json
from io import BytesIO

import icecream

from parser.bot.config import bot
from parser.database.config import AsyncSessionLocal, Message
from parser.database.database import (
    format_product_info,
    insert_data,
)
from parser.parse_url import parse_url
from parser.scripts.parser_dictionary import DictionaryParser
from parser.scripts.product_data import get_product_data
from parser.services import clean_and_extract_price
from typing import Any

from matplotlib import pyplot as plt
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


@bot.message_handler(commands=['start'])
async def start_command_bot(message):
    await bot.send_message(message.chat.id, 'Бот запущен!')


def create_product_keyboard(product_id):
    keyboard = InlineKeyboardMarkup()
    button_view_graph = InlineKeyboardButton(
        text='Посмотреть график изменения цены',
        callback_data=f'view_graph_{product_id}',
    )
    keyboard.add(button_view_graph)
    return keyboard


def create_return_to_card_keyboard(product_id):
    keyboard = InlineKeyboardMarkup()
    button_return_to_card = InlineKeyboardButton(
        text='Вернуться к карточке товара', callback_data=f'return_to_card_{product_id}'
    )
    keyboard.add(button_return_to_card)
    return keyboard


def get_price_history(product):
    return [
        (entry.updated_at, entry.price, entry.price_ozon)
        for entry in product.prices_history
    ]

async def send_price_graph(chat_id, product_name, price_history, product_id):
    dates = [d.strftime('%d-%m-%Y %H:%M') for d, _, _ in price_history]
    prices = [p for _, p, _ in price_history]
    prices_ozon = [p for _, _, p in price_history]
    plt.figure(figsize=(10, 5))
    plt.plot(dates, prices, marker='o', label='Обычная цена')
    plt.plot(dates, prices_ozon, marker='x', label='Цена по карте Озон')
    plt.title(f'Изменение цен для {product_name}')
    plt.xlabel('Дата')
    plt.ylabel('Цена (₽)')
    plt.xticks(rotation=45)
    plt.grid()
    plt.legend()
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()

    keyboard = InlineKeyboardMarkup()
    back_button = InlineKeyboardButton(
        text='Вернуться', callback_data=f'return_to_card_{product_id}'
    )
    keyboard.add(back_button)
    await bot.send_photo(chat_id, photo=buf, reply_markup=keyboard)


from telebot import types  # Убедитесь, что вы импортировали необходимые классы


@bot.message_handler(commands=['get_prices'])
async def handle_get_prices(message):
    user_id = message.chat.id
    async with AsyncSessionLocal() as session:
        # Извлекаем сообщения пользователя
        results = session.query(Message).filter(
            Message.telegram_user_id == user_id).all()
        keyboard = types.InlineKeyboardMarkup()
        if results:
            for result in results:
                for index, product in enumerate(result.products):
                    product_name = product.product_name
                    button = types.InlineKeyboardButton(
                        text=product_name,
                        callback_data=f'product_{result.id}_{index}'
                        # Добавляем ID сообщения для уникальности
                    )
                    keyboard.add(button)

            await bot.send_message(
                chat_id=user_id, text='Выберите товар:', reply_markup=keyboard
            )
        else:
            await bot.send_message(chat_id=user_id,
                                   text='Нет доступных товаров.')


@bot.callback_query_handler(func=lambda call: call.data.startswith('product_'))
async def callback_product(call):
    # Извлекаем идентификатор сообщения и индекс продукта из callback_data
    message_id, product_index = map(int, call.data.split('_')[1:3])
    user_id = call.message.chat.id

    async with AsyncSessionLocal() as session:
        # Извлекаем сообщение по telegram_user_id
        result = session.query(Message).filter(Message.telegram_user_id == user_id).first()

        if result and product_index < len(result.products):
            product = result.products[product_index]
            formatted_info = format_product_info(product)
            keyboard = create_product_keyboard(product_index)
            image_url = product.picture

            await bot.send_photo(
                chat_id=user_id,
                photo=image_url,
                caption=formatted_info,
                reply_markup=keyboard,
            )
        else:
            await bot.send_message(user_id, 'Не удалось найти товар.')


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('view_graph_'))
async def callback_view_graph(call):
    # Извлекаем индекс продукта из callback_data
    product_index = int(call.data.split('_')[2])
    user_id = call.message.chat.id

    async with AsyncSessionLocal() as session:
        # Извлекаем сообщение по telegram_user_id
        result = session.query(Message).filter(
            Message.telegram_user_id == user_id).first()

        if result and product_index < len(result.products):
            product = result.products[product_index]
            price_history = get_price_history(product)

            await bot.delete_message(user_id, call.message.id)

            await send_price_graph(
                user_id, product.product_name, price_history, product_index
            )
        else:
            await bot.send_message(user_id, 'Не удалось найти товар.')


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('return_to_card_'))
async def callback_return_to_card(call):
    # Извлекаем идентификатор продукта из callback_data
    product_id = int(call.data.split('_')[3])
    user_id = call.message.chat.id

    async with AsyncSessionLocal() as session:
        # Извлекаем сообщение пользователя по его ID
        result = session.query(Message).filter(
            Message.telegram_user_id == user_id).first()

        if result and product_id < len(result.products):
            product = result.products[product_id]
            price_history = get_price_history(
                product)  # Получаем историю цен (если это необходимо)
            formatted_info = format_product_info(
                product)  # Форматируем информацию о продукте

            await bot.delete_message(user_id,
                                     call.message.id)  # Удаляем предыдущее сообщение

            keyboard = create_product_keyboard(
                product_id)  # Создаем клавиатуру для продукта

            image_url = product.picture  # Извлекаем URL изображения
            await bot.send_photo(
                chat_id=user_id,
                photo=image_url,
                caption=formatted_info,
                reply_markup=keyboard,
            )
        else:
            await bot.send_message(user_id, 'Не удалось найти товар.')


@bot.message_handler(content_types=['text'])
async def get_url(message):
    user_id = message.chat.id
    result_parse_url = parse_url(message.text)
    icecream.ic(result_parse_url)

    # Получаем данные о продукте
    data = await get_product_data(result_parse_url)


    if not data:
        await bot.send_message(user_id, "Не удалось получить данные о продукте.",)
        return

    parse = DictionaryParser(data)

    product_name_data = parse.find_key('webProductHeading-3385933-default-1')
    icecream.ic(product_name_data)
    if not product_name_data:
        await bot.send_message(user_id, "Не удалось найти название продукта.")
        return
    product_name_dict = json.loads(product_name_data[0])

    # Извлекаем изображение продукта
    image_data = parse.find_key('webGallery-3311629-default-1')
    if not image_data:
        await bot.send_message(user_id,
                               "Не удалось найти изображение продукта.")
        return
    picture_dict = json.loads(image_data[0])
    picture = picture_dict['images'][0]['src']

    # Извлекаем информацию о цене
    price_data = parse.find_key('webPrice-3121879-default-1')
    if not price_data:
        await bot.send_message(user_id, "Не удалось найти информацию о цене.")
        return
    data_dict = json.loads(price_data[0])

    available = data_dict['isAvailable']
    price = clean_and_extract_price(data_dict['price'])
    card_price = clean_and_extract_price(data_dict['cardPrice'])
    original_price = clean_and_extract_price(data_dict['originalPrice'])

    result_insert_data = await insert_data(
        available=available,
        user_id=user_id,
        url=result_parse_url,
        product_name=product_name_dict['title'],
        price=price,
        price_ozon=card_price,
        original_price=original_price,
        picture=picture,
    )

    await bot.send_message(user_id, result_insert_data)


async def start_bot() -> Any:
    """Function for start telegram bot"""
    return await bot.infinity_polling()
