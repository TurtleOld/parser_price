import asyncio
import os

from parser.bot.messages import start_bot
from parser.database.config import init_db
from parser.database.database import update_price


async def run_every_minute(func):
    time_update = int(os.environ.get('TIME'))
    while True:
        await func()
        await asyncio.sleep(time_update)


async def main():
    await init_db()
    await asyncio.gather(run_every_minute(update_price), start_bot())


asyncio.run(main())
