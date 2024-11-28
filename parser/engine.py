import asyncio
from parser.bot.messages import start_bot
from parser.database.database import update_price

async def run_every_minute(func):
    while True:
        await func()
        await asyncio.sleep(60)
        
async def main():
    await asyncio.gather(run_every_minute(update_price), start_bot())


asyncio.run(main())
