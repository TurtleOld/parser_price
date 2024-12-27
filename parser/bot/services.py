import datetime
from io import BytesIO
from parser.bot.config import bot
from parser.bot.keyboards import create_return_to_card_keyboard
from parser.database.config import AsyncSessionLocal
from parser.database.config import PriceHistory
from typing import List

from matplotlib import pyplot as plt
from sqlalchemy import select


async def get_price_history(session: AsyncSessionLocal, product) -> List[tuple]:
    result = await session.execute(
        select(PriceHistory).filter(PriceHistory.product_id == product.id)
    )
    price_history_entries = result.scalars().all()

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

    period_text = f'Период отслеживания с {start_date} по {end_date}'

    dates = [d.strftime('%d-%m-%Y %H:%M') for d, _, _ in price_history]
    prices = [p for _, p, _ in price_history]
    prices_ozon = [p for _, _, p in price_history]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, prices, marker='o', label='Обычная цена')
    plt.plot(dates, prices_ozon, marker='o', label='Цена по карте Озон')
    plt.title(product_name)
    plt.xlabel(period_text)
    plt.ylabel('Цена (₽)')
    plt.xticks(dates, [''] * len(dates))

    # Включаем сетку, показывающую только горизонтальные линии
    plt.grid(axis='y', which='major')

    plt.legend()
    plt.tight_layout()

    plt.gca().set_facecolor('none')
    plt.gcf().patch.set_facecolor('none')
    plt.tick_params(
        axis='x', which='both', bottom=False, top=False, labelbottom=False
    )

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='none')
    buf.seek(0)
    plt.close()

    keyboard = create_return_to_card_keyboard(product_id)
    await bot.send_photo(chat_id, photo=buf, reply_markup=keyboard)
