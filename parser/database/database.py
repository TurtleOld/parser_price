import json
from datetime import datetime
from schedule import every, repeat, run_pending
import time
from pymongo import errors

from parser.database.config import messages
from parser.scripts.parser_dictionary import DictionaryParser
from parser.scripts.product_data import get_product_data
from parser.services import clean_and_extract_price


def insert_data(available, product_name, price, price_ozon, original_price, user_id=None, url=None, ):
    try:
        messages.insert_one({
            'telegram_user_id': user_id,
            'products': [{
                'available': available,
                'url': url,
                'product_name': product_name,
                'prices_history': [{
                    'price': price,
                    'price_ozon': price_ozon,
                    'original_price': original_price,
                    'updated_at': datetime.now()
                }],
                'latest_price': price,
                'latest_price_ozon': price_ozon,
                'original_price': original_price
            }]
        })
        return 'Товар был добавлен на отслеживание'
    except errors.DuplicateKeyError:
        existing_document = messages.find_one({'telegram_user_id': user_id})

        if existing_document is not None:
            existing_urls = [p['url'] for p in existing_document.get('products', [])]
            if url in existing_urls:
                return 'Такой товар уже был добавлен'

        messages.update_one(
            {'telegram_user_id': user_id},
            {'$addToSet': {'products': {
                'available': available,
                'url': url,
                'product_name': product_name,
                'prices_history': [{
                    'price': price,
                    'price_ozon': price_ozon,
                    'original_price': original_price,
                    'updated_at': datetime.now()
                }],
                'latest_price': price,
                'latest_price_ozon': price_ozon,
                'original_price': original_price
            }}},
        )
        return 'Товар был добавлен на отслеживание'


@repeat(every(5).hours)
def update_price():
    results = messages.find({}, {'_id': 0})
    for result in results:
        user_id = result['telegram_user_id']
        products = result.get('products', [])

        for product in products:
            url = product['url']

            # Получение актуальных данных о товаре
            data = get_product_data(url)
            parse = DictionaryParser(data)
            product_name_data = parse.find_key(
                'webProductHeading-3385933-default-1')
            product_name_dict = json.loads(product_name_data[0])

            f_key = parse.find_key('webPrice-3121879-default-1')
            data_dict = json.loads(f_key[0])
            available = data_dict['isAvailable']
            price = clean_and_extract_price(data_dict['price'])
            card_price = clean_and_extract_price(data_dict['cardPrice'])
            original_price = clean_and_extract_price(data_dict['originalPrice'])

            # Обновляем данные в базе данных
            filter_query = {'telegram_user_id': user_id, 'products.url': url}
            update_query = {
                '$push': {
                    'products.$.prices_history': {
                        'price': price,
                        'price_ozon': card_price,
                        'original_price': original_price,
                        'updated_at': datetime.now()
                    }
                },
                '$set': {
                    'products.$.latest_price': price,
                    'products.$.latest_price_ozon': card_price,
                    'products.$.original_price': original_price
                }
            }

            result = messages.update_one(filter_query, update_query)

            if result.modified_count > 0:
                print(f'Цена для товара с URL {url} была успешно обновлена.')
            else:
                print(
                    f'Не удалось найти товар с URL {url} для обновления цены.')



def get_data(user_id):
    results = messages.find({'telegram_user_id': user_id}, {'_id': 0})
    all_products = []

    for result in results:
        for product in result.get('products'):
            formatted_info = format_product_info(product)
            all_products.append(formatted_info)
    return all_products


def format_product_info(product):
    availability = "Доступен" if product["available"] else "Недоступен"
    product_name = product["product_name"]
    price = product["price"]
    ozon_price = product["price_ozon"]
    original_price = product["original_price"]

    formatted_string = f"""
Доступность: {availability}
Наименование товара: {product_name}
Цена: {price} ₽
Цена по карте: {ozon_price} ₽
Первоначальная цена: {original_price} ₽
"""

    return formatted_string
