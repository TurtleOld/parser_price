from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


def create_product_keyboard(product_id):
    button_view_graph = InlineKeyboardButton(
        text='Посмотреть график изменения цены',
        callback_data=f'view_graph_{product_id}',
    )
    remove_product_button = InlineKeyboardButton(
        text='Удалить товар', callback_data=f'remove_product_{product_id}'
    )
    keyboard = InlineKeyboardMarkup(
        [[button_view_graph, remove_product_button]]
    )
    return keyboard


def create_return_to_card_keyboard(product_id):
    keyboard = InlineKeyboardMarkup()
    button_return_to_card = InlineKeyboardButton(
        text='Вернуться к карточке товара',
        callback_data=f'return_to_card_{product_id}',
    )
    keyboard.add(button_return_to_card)
    return keyboard
