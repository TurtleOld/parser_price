import asyncio
import os

from aiohttp import web

from parser.bot.config import app, WEBHOOK_PORT
from parser.scripts.services import update_product_to_monitoring


async def run_every_minute(func):
    time_update = int(os.environ.get("TIME", 60))
    while True:
        await func()
        await asyncio.sleep(time_update)


async def main():
    asyncio.create_task(run_every_minute(update_product_to_monitoring))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()

    print(f"Server started at http://0.0.0.0:{WEBHOOK_PORT}")

    while True:
        await asyncio.sleep(3600)


asyncio.run(main())