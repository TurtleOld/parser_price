import datetime
import json
from io import BytesIO
from parser.bot.config import bot
from parser.database.config import AsyncSessionLocal, Message, PriceHistory
from parser.database.database import format_product_info, insert_data
from parser.parse_url import parse_url
from parser.scripts.parser_dictionary import DictionaryParser
from parser.scripts.product_data import get_product_data
from parser.services import clean_and_extract_price
from typing import Any

from matplotlib import pyplot as plt
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


@bot.message_handler(commands=['start'])
async def start_command_bot(message):
    welcome_message = 'Добро пожаловать!\nПросто отправь ссылку с Ozon\nПосмотреть товары можно командной /my_products'
    await bot.send_message(message.chat.id, welcome_message)


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
        text='Вернуться к карточке товара',
        callback_data=f'return_to_card_{product_id}',
    )
    keyboard.add(button_return_to_card)
    return keyboard


async def get_price_history(session: AsyncSessionLocal, product):
    # Получаем историю цен из БД асинхронно
    result = await session.execute(
        select(PriceHistory).filter(PriceHistory.product_id == product.id)
    )
    price_history_entries = result.scalars().all()

    # Возвращаем историю цен
    return [
        (entry.updated_at, entry.price, entry.price_ozon)
        for entry in price_history_entries
    ]


async def send_price_graph(chat_id, product_name, price_history, product_id):
    if price_history:
        start_date = price_history[0][0].strftime('%d.%m.%Y')
        end_date = price_history[-1][0].strftime('%d.%m.%Y')
    else:
        start_date = datetime.datetime.now().strftime('%d.%m.%Y')
        end_date = datetime.datetime.now().strftime('%d.%m.%Y')

    period_text = f"Период отслеживания с {start_date} по {end_date}"

    dates = [d.strftime('%d-%m-%Y %H:%M') for d, _, _ in price_history]
    prices = [p for _, p, _ in price_history]
    prices_ozon = [p for _, _, p in price_history]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, prices, marker='o', label='Обычная цена')
    plt.plot(dates, prices_ozon, marker='x', label='Цена по карте Озон')
    plt.title(product_name)
    plt.xlabel(period_text)
    plt.ylabel('Цена (₽)')
    plt.xticks(dates, [''] * len(dates))
    plt.grid()
    plt.legend()
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()

    keyboard = InlineKeyboardMarkup()
    back_button = InlineKeyboardButton(
        text='Вернуться',
        callback_data=f'return_to_card_{product_id}',
    )
    keyboard.add(back_button)
    await bot.send_photo(chat_id, photo=buf, reply_markup=keyboard)


@bot.message_handler(commands=['my_products'])
async def handle_get_prices(message):
    user_id = message.chat.id
    async with AsyncSessionLocal() as session:
        # Используем SQLAlchemy 2.x API для выполнения асинхронного запроса
        results = await session.execute(
            select(Message)
            .options(
                selectinload(Message.products)
            )  # Предзагрузка связанных продуктов
            .filter(Message.telegram_user_id == user_id)
        )
        messages = results.scalars().all()  # Получение всех результатов

        keyboard = InlineKeyboardMarkup()

        if messages:
            for msg in messages:
                for product in msg.products:
                    product_name = product.product_name or 'Без названия'
                    button = InlineKeyboardButton(
                        text=product_name,
                        callback_data=f'product_{msg.id}',
                    )
                    keyboard.add(button)

            # Отправляем сообщение с клавиатурой
            await bot.send_message(
                chat_id=user_id, text='Выберите товар:', reply_markup=keyboard
            )
        else:
            # Если товаров нет, отправляем уведомление
            await bot.send_message(
                chat_id=user_id, text='Нет доступных товаров.'
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith('product_'))
async def callback_product(call):
    message_id = int(call.data.split('_')[1])
    user_id = call.message.chat.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message)
            .options(selectinload(Message.products))
            .filter(
                Message.telegram_user_id == user_id,
                Message.id == message_id,
            )
        )
        message = result.scalars().first()

        if message:
            for product in message.products:
                formatted_info = format_product_info(product)
                keyboard = create_product_keyboard(message_id)
                await bot.send_photo(
                    chat_id=user_id,
                    photo=product.picture,
                    caption=formatted_info,
                    reply_markup=keyboard,
                    show_caption_above_media=True,
                )
        else:
            await bot.send_message(user_id, 'Не удалось найти товар.')


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('view_graph_')
)
async def callback_view_graph(call):
    product_id = int(call.data.split('_')[2])
    user_id = call.message.chat.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message)
            .options(selectinload(Message.products))
            .filter(
                Message.telegram_user_id == user_id,
                Message.id == product_id,
            )
        )
        message = result.scalars().first()
        if message:
            for product in message.products:
                price_history = await get_price_history(session, product)

                await bot.delete_message(user_id, call.message.id)

                await send_price_graph(
                    user_id,
                    product.product_name,
                    price_history,
                    product_id,
                )
        else:
            await bot.send_message(user_id, 'Не удалось найти товар.')


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('return_to_card_')
)
async def callback_return_to_card(call):
    product_id = int(call.data.split('_')[3])
    user_id = call.message.chat.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message)
            .options(selectinload(Message.products))
            .filter(
                Message.telegram_user_id == user_id,
                Message.id == product_id,
            )
        )
        message = result.scalars().first()
        if message:
            for product in message.products:

                # Форматирование информации о продукте
                formatted_info = format_product_info(product)

                # Удаление предыдущего сообщения
                await bot.delete_message(user_id, call.message.id)

                # Создание клавиатуры для продукта
                keyboard = create_product_keyboard(product_id)

                # Отправка карточки с продуктом
                await bot.send_photo(
                    chat_id=user_id,
                    photo=product.picture,
                    caption=formatted_info,
                    reply_markup=keyboard,
                    show_caption_above_media=True,
                )
        else:
            await bot.send_message(user_id, 'Не удалось найти товар.')


@bot.message_handler(content_types=['text'])
async def get_url(message):
    user_id = message.chat.id
    result_parse_url = parse_url(message.text)

    data = await get_product_data(result_parse_url)
    if not data:
        await bot.send_message(
            user_id,
            'Не удалось получить данные о продукте.',
        )
        return

    parse = DictionaryParser(data)

    product_name_data = parse.find_key('webProductHeading-3385933-default-1')
    if not product_name_data:
        await bot.send_message(user_id, 'Не удалось найти название продукта.')
        return
    product_name_dict = json.loads(product_name_data[0])

    image_data = parse.find_key('webGallery-3311629-default-1')
    if not image_data:
        await bot.send_message(
            user_id,
            'Не удалось найти изображение продукта.',
        )
        return
    picture_dict = json.loads(image_data[0])
    picture = picture_dict['images'][0]['src']

    price_data = parse.find_key('webPrice-3121879-default-1')
    if not price_data:
        await bot.send_message(user_id, 'Не удалось найти информацию о цене.')
        return
    data_dict = json.loads(price_data[0])
    name_store = parse.find_key(
        "webStickyProducts-726428-default-1",
    )
    store = json.loads(name_store['name'])
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
        store=store,
    )
    await bot.send_message(user_id, result_insert_data)


async def start_bot() -> Any:
    """Function for start telegram bot"""
    return await bot.infinity_polling()
