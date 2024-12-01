import re


def clean_and_extract_price(price_string):
    # Удаляем тонкие пробелы (\u2009)
    cleaned_string = price_string.replace("\u2009", "")

    # Извлекаем числовую часть
    number_part = "".join(re.findall(r"\d+", cleaned_string))

    # Преобразуем в число
    return int(number_part)
