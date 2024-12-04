import logging
import os

import telebot
from aiohttp import web
from dotenv import load_dotenv
from telebot.async_telebot import AsyncTeleBot

load_dotenv()
logger = telebot.logger
if os.getenv("DEBUG"):
    telebot.logger.setLevel(logging.DEBUG)
else:
    telebot.logger.setLevel(logging.INFO)
token = os.getenv("TOKEN_TELEGRAM_BOT")
bot = AsyncTeleBot(token, parse_mode="html")

WEBHOOK_URL = 'https://webhook.pavlovteam.ru/webhook'
WEBHOOK_PATH = '/webhook'
WEBHOOK_PORT = 8443

async def handle_webhook(request):
    if request.match_info.get('path') == WEBHOOK_PATH:
        json_str = await request.json()
        update = telebot.types.Update.de_json(json_str)
        await bot.process_new_updates([update])
        return web.Response(status=200)
    return web.Response(status=404)


async def set_webhook():
    webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.remove_webhook()
    await bot.set_webhook(url=webhook_url)


app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)