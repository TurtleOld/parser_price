import asyncio
import os
from parser.bot.messages import start_bot
from parser.scripts.services import update_product_to_monitoring


async def run_every_minute(func):
    time_update = int(os.environ.get('TIME'))
    while True:
        await func()
        await asyncio.sleep(time_update)


async def main():
    await asyncio.gather(
        run_every_minute(update_product_to_monitoring), start_bot()
    )


asyncio.run(main())
