from pymongo import MongoClient

username = 'mydbuser'
password = 'mydbpass'

# Подключаемся к MongoDB с использованием URI подключения
client = MongoClient(f'mongodb://{username}:{password}@mongodb:27017/mydatabase')

telegram_user_db = client['telegram_user']

messages = telegram_user_db.messages

messages.create_index('telegram_user_id', unique=True)
messages.create_index('url', unique=True)
messages.create_index('urls', unique=True)
messages.create_index('product_name', unique=True)
messages.create_index('product_names', unique=True)
