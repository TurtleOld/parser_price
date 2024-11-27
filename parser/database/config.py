from pymongo import MongoClient

client = MongoClient('localhost', 27017)

telegram_user_db = client['telegram_user']

messages = telegram_user_db.messages

messages.create_index('telegram_user_id', unique=True)
messages.create_index('url', unique=True)
messages.create_index('urls', unique=True)
messages.create_index('product_name', unique=True)
messages.create_index('product_names', unique=True)
