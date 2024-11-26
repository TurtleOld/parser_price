import json
import time
from io import BytesIO
from typing import Any

import schedule
from matplotlib import pyplot as plt
from schedule import run_pending
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from parser.bot.config import bot
from parser.database.config import messages
from parser.database.database import insert_data, get_data, update_price, \
    format_product_info
from parser.parse_url import parse_url
from parser.scripts.parser_dictionary import DictionaryParser
from parser.scripts.product_data import get_product_data
from parser.services import clean_and_extract_price


@bot.message_handler(commands=['start'])
async def start_command_bot(message):
    await bot.send_message(message.chat.id, 'Бот запущен!')


@bot.message_handler(commands=['get'])
async def get_data_user(message):
    results = get_data(message.chat.id)
    for result in results:
        await bot.send_message(message.chat.id, result)


def create_product_keyboard(product_id):
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Посмотреть график отслеживания цены", callback_data=f"view_graph_{product_id}")
    keyboard.add(button)
    return keyboard


def get_price_history(product):
    return [(entry['updated_at'], entry['price'], entry['price_ozon']) for entry in product['prices_history']]


async def send_price_graph(chat_id, product_name, price_history):
    dates = [entry[0] for entry in price_history]
    prices = [entry[1] for entry in price_history]
    prices_ozon = [entry[2] for entry in price_history]
    plt.figure(figsize=(10, 5))
    plt.plot(dates, prices, marker='o', label='Цена')  # Линия для обычной цены
    plt.plot(dates, prices_ozon, marker='x',
             label='Цена по ОЗОНу')  # Линия для цены по ОЗОНу
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
    await bot.send_photo(chat_id, photo=buf)


@bot.message_handler(commands=['get_prices'])
async def handle_get_prices(message):
    user_id = message.chat.id
    results = messages.find({'telegram_user_id': user_id}, {'_id': 0})
    for result in results:
        for index, product in enumerate(result.get('products', [])):
            product_name = product['product_name']
            formatted_info = format_product_info(product)
            keyboard = create_product_keyboard(index)  # Используем индекс как уникальный идентификатор
            await bot.send_message(user_id, formatted_info, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('view_graph_'))
async def callback_view_graph(call):
    product_index = int(call.data.split('_')[2])
    user_id = call.message.chat.id
    result = messages.find_one({'telegram_user_id': user_id}, {'_id': 0})
    if result:
        product = result['products'][product_index]
        price_history = get_price_history(product)
        await send_price_graph(user_id, product['product_name'], price_history)
    else:
        await bot.send_message(user_id, "Не удалось найти товар.")


@bot.message_handler(content_types=['text'])
async def get_url(message):
    user_id = message.chat.id
    result_parse_url = parse_url(message.text)
    data = get_product_data(result_parse_url)
    parse = DictionaryParser(data)
    product_name_data = parse.find_key('webProductHeading-3385933-default-1')
    product_name_dict = json.loads(product_name_data[0])

    f_key = parse.find_key('webPrice-3121879-default-1')
    data_dict = json.loads(f_key[0])
    available = data_dict['isAvailable']
    price = clean_and_extract_price(data_dict['price'])
    card_price = clean_and_extract_price(data_dict['cardPrice'])
    original_price = clean_and_extract_price(data_dict['originalPrice'])
    result_insert_data = insert_data(available, user_id, result_parse_url, product_name_dict['title'], price, card_price, original_price,)
    schedule.every(2).seconds.do(update_price, result_parse_url, price, card_price, original_price)
    await bot.send_message(message.chat.id, result_insert_data)


def scheduler():
    while True:
        run_pending()
        time.sleep(1)




def start_bot() -> Any:
    """Function for start telegram bot"""
    return bot.infinity_polling()