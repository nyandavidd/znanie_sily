from aiogram import Bot, Dispatcher, html
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import os
import asyncio
import logging
import sqlite3
from textwrap import dedent
import sqlite_vec
from sqlite_vec import serialize_float32
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import json
import time
from datetime import datetime

from handlers import common
from SILARAG.rag.prompt import prompt_denis
from SILARAG.rag.rag_inference import setup_database, setup_log_database, retrieve_context, call_model, ask_question

# Константы с именами баз данных и моделями
DATABASE_NAME = "SILA.sqlite3"
LOG_DATABASE_NAME = "log.sqlite3"
EMBEDDING_MODEL_NAME = 'deepvk/USER-bge-m3'
LANGUAGE_MODEL_NAME = 'vikhr'

# Настройка базы данных и моделей
database_connection = setup_database()
log_database_connection = setup_log_database()
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
conversation_history = [{"role": "system", "content": prompt_denis}]
chat_session_id = datetime.now().strftime("%Y%m%d%H%M%S")

# Получение токена бота из переменных окружения
bot_token = '7955673018:AAFGZwb915WA6iXRiwzYzPDT1KTGdstSBYk'

# Создание объектов бота и диспетчера
bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()

async def start_bot():
    """
    Основная функция запуска бота.
    Настраивает логирование, включает роутеры и начинает опрос для обработки событий.
    """
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    # Подключение обработчиков (роутеров)
    dispatcher.include_routers(common.router)

    # Удаление вебхука и запуск опроса событий
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(start_bot())