import aiohttp


async def get_product_data(url):
    base_url = 'https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2'
    params = {'url': url}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f'Ошибка: Статус код {response.status_code}')
                    return None
    except Exception as e:
        print(f'Ошибка при выполнении запроса: {e}')
        return None
    
