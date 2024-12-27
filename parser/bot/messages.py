import json
from parser.bot.config import bot
from parser.bot.keyboards import create_product_keyboard
from parser.bot.services import get_price_history, send_price_graph
from parser.database.config import AsyncSessionLocal, PriceHistory, Product
from parser.scripts.services import (
    format_product_info,
    add_product_to_monitoring,
)
from parser.database.config import Message
from parser.scripts.parse_url import parse_url
from parser.scripts.parser_dictionary import DictionaryParser
from parser.scripts.product_data import get_product_data
from parser.scripts.services import clean_and_extract_price
from typing import Any
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)


@bot.message_handler(commands=['start'])
async def start_command_bot(message):
    welcome_message = 'Добро пожаловать!\nПросто отправь ссылку с Ozon\nПосмотреть товары можно командной /my_products'
    await bot.send_message(message.chat.id, welcome_message)


@bot.message_handler(commands=['my_products'])
async def handle_get_prices(message):
    user_id = message.chat.id
    async with AsyncSessionLocal() as session:
        results = await session.execute(
            select(Message)
            .options(selectinload(Message.products))
            .filter(Message.telegram_user_id == user_id)
        )
        messages = results.scalars().all()

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

            await bot.send_message(
                chat_id=user_id,
                text='Выберите товар:',
                reply_markup=keyboard,
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text='Нет доступных товаров.',
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
                formatted_info = format_product_info(product)
                await bot.delete_message(user_id, call.message.id)
                keyboard = create_product_keyboard(product_id)
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
    func=lambda call: call.data.startswith('remove_product_')
)
async def callback_remove_product(call: CallbackQuery):
    product_id = int(call.data.split('_')[2])
    user_id = call.message.chat.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product)
            .join(Message)
            .filter(
                Message.telegram_user_id == user_id,
                Product.id == product_id,
            )
        )

        product = result.scalars().first()

        if product is not None:
            await session.execute(
                delete(PriceHistory).where(
                    PriceHistory.product_id == product_id
                )
            )

            await session.delete(product)
            await bot.delete_message(user_id, call.message.id)
            await session.commit()
            await bot.answer_callback_query(
                callback_query_id=call.id,
                text='Товар удален.',
            )
        else:
            await bot.answer_callback_query(
                callback_query_id=call.id,
                text='Не удалось найти товар.',
            )


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
        await bot.send_message(
            user_id,
            'Товар не был добавлен, так как закончился или отсутствует на маркетплейсе Ozon.',
        )
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
    name_store = parse.find_key('webStickyProducts-726428-default-1')
    store = json.loads(name_store[0]).get('seller', None).get('name', None)
    available = data_dict.get('isAvailable', None)
    price = clean_and_extract_price(data_dict.get('price', None))
    card_price = clean_and_extract_price(data_dict.get('cardPrice', None))
    original_price = clean_and_extract_price(
        data_dict.get(
            'originalPrice',
            None,
        )
    )

    result_insert_data = await add_product_to_monitoring(
        available=available,
        user_id=user_id,
        url=result_parse_url,
        product_name=product_name_dict.get('title', None),
        price=price,
        price_ozon=card_price,
        original_price=original_price,
        picture=picture,
        store=store,
    )
    await bot.send_message(user_id, result_insert_data)


async def start_bot() -> Any:
    """Function for start telegram bot"""
    return await bot.infinity_polling(
        timeout=90,
        request_timeout=90,
    )
