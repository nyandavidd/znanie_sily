import requests
from SILARAG.rag.prompt import prompt_denis
# URL для API
MODEL_URL = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'

# Заголовки
MODEL_HEADERS = {
    'Authorization': 'Bearer t1.9euelZrIyJyPnorMmM2dlJWTjsjMiu3rnpWamsuXns-Tjo_NzI2Sy5HLmsbl8_cHTQtH-e8tXUhl_t3z90d7CEf57y1dSGX-zef1656VmouTicyQyJrGkJmTzZKQmZjH7_zF656VmouTicyQyJrGkJmTzZKQmZjH.q8Bc_vdYqGgQJLW21ai0OJODRePA5SQH89wQGUvktLIB0WaCyMt6g7U4boPnjMPsLq-C6T0ZjOIsw8Z2kkMDAA', 'expiresAt': '2024-10-26T21:57:39.833436920Z',
    'Content-Type': 'application/json'
}

# Данные запроса


def model_response(text: str) -> str:
    """
    Отправляет запрос модели и возвращает ответ.

    Параметры:
        text (str): Исходный текст в формате markdown.

    Возвращает:
        text_ans (str): Ответ модели.
    """
    MODEL_CONN_DATA = {
    "modelUri": "gpt://b1gjp5vama10h4due384/yandexgpt/latest",
    "completionOptions": {
        "stream": False,
        "temperature": 0.6,
        "maxTokens": 10000
    },
    "messages": [
        {
            "role": "system",
            "text": prompt_denis
        },
        {
            "role": "user",
            "text": text
        }
    ]
    }




    response = requests.post(MODEL_URL, headers=MODEL_HEADERS, json=MODEL_CONN_DATA)

    # Печать результата
    text_ans = response.json()['result']['alternatives'][0]['message']['text']
    return text_ans


def model_response2(text: str) -> str:
    """
    Отправляет запрос модели и возвращает ответ.

    Параметры:
        text (str): Исходный текст в формате markdown.

    Возвращает:
        text_ans (str): Ответ модели.
    """
    MODEL_CONN_DATA = {
    "modelUri": "gpt://b1gjp5vama10h4due384/yandexgpt/latest",
    "completionOptions": {
        "stream": False,
        "temperature": 0.6,
        "maxTokens": 10000
    },
    "messages": [
        {
            "role": "system",
            "text": prompt_denis
        },
        {
            "role": "user",
            "text": text
        }
    ]
    }




    response = requests.post(MODEL_URL, headers=MODEL_HEADERS, json=MODEL_CONN_DATA)

    # Печать результата
    text_ans = response.json()['result']['alternatives'][0]['message']['text']
    return text_ans




