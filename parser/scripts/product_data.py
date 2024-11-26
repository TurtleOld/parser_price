import niquests
from urllib.parse import quote

def get_product_data(url):
    # Кодируем название товара для URL


    # Формируем URL запроса
    base_url = "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2"
    params = {"url": url}

    try:
        # Выполняем GET-запрос
        response = niquests.get(base_url, params=params)

        # Проверяем статус ответа
        if response.status_code == 200:
            # Возвращаем данные в формате JSON
            return response.json()
        else:
            print(f"Ошибка: Статус код {response.status_code}")
            return None

    except Exception as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None