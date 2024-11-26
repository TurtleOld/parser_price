import json
import time
from typing import Any

import schedule
from schedule import run_pending

from parser.bot.config import bot
from parser.database.database import insert_data, get_data, update_price
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