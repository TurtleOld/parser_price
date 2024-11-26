
import logging
import os

import telebot
from dotenv import load_dotenv
from telebot.async_telebot import AsyncTeleBot

load_dotenv()
logger = telebot.logger
if os.getenv('DEBUG'):
    telebot.logger.setLevel(logging.DEBUG)
else:
    telebot.logger.setLevel(logging.INFO)
token = os.getenv('TOKEN_TELEGRAM_BOT')
bot = AsyncTeleBot(token, parse_mode='html')