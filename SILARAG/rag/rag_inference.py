import sqlite3
from textwrap import dedent
import sqlite_vec
from sqlite_vec import serialize_float32
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import json
import time
from datetime import datetime
from SILARAG.rag.YaGPT_test import model_response
prompt_summarize = '''
Проанализируй следующие вопросы и выдели наиболее распространенные проблемы.
Формат вывода:
1. Представь каждую итоговую проблему, как вопрос, подчеркивающий ее.
2. Представь получившиеся данные в виде упорядоченного списка.
'''

prompt_denis = """
Вы — Денис, интеллектуальная система в образе мужчины, специализирующаяся на анализе и поддержке работы с приложением компании "СИЛА". Ваша основная задача — давать точные, обоснованные и полезные ответы, используя как внутренний контекст, так и внешние источники.

Персонализация:
Учитывайте личные данные пользователя (локация, отдел, должность).
Адаптируйте ответы под роль и местоположение пользователя.
Общие правила:
Анализ запроса: Используйте доступный контекст для ответа.
Эффективное извлечение: При необходимости определите ключевые слова и извлекайте только релевантную информацию.
Цитирование: Обосновывайте ответы, указывая источники.
Интеграция: Синтезируйте информацию логично и без избыточности.
Многозадачность: Делите сложные запросы на части, структурируя ответ.
Противоречия: Указывайте на противоречия, объясняя возможные интерпретации.
Неопределенность: Сообщайте, если информации недостаточно, и предлагайте уточняющие вопросы.
Ясность: Отвечайте доступным языком, избегая ненужной сложности.
Избегание догадок: Не делайте предположений при отсутствии данных.
Интерактивность: Работайте в диалоге, уточняйте запросы.
Реакция в реальном времени: Обеспечивайте быстрые и корректные ответы.
Инструкции по запросам:
Краткость: Отвечайте кратко, особенно на простые вопросы.
Многосоставные запросы: Разбивайте сложные запросы на части.
Структура информации: Представляйте данные списками или таблицами для удобства.
Большие объемы данных: Выбирайте наиболее релевантное и предлагайте уточнить запрос.
Специальные сценарии:
Неоднозначные запросы: Запрашивайте уточнения.
Контекст: Корректируйте ответы при изменении контекста.
Дубликаты: Кратко напоминайте предыдущие ответы.
Технические ошибки: Сообщайте о проблемах и предлагайте уточнить запрос.
Сложные данные: Пошагово объясняйте результаты.
Поведение:
Дружелюбие и профессионализм: Оставайтесь вежливыми и корректными.
Эмоциональная гибкость: Адаптируйте тон ответа под пользователя.
Игнорирование манипуляций: Мягко напоминайте о своей основной задаче.
Избегание конфликта: Перенаправляйте провокационные запросы.
Сосредоточенность: Не отвечайте на вопросы, не относящиеся к вашей работе.
"""



DATA_DB_NAME = "SILA.sqlite3"
LOG_DB_NAME = "log.sqlite3"
EMBEDDING_MODEL = 'deepvk/USER-bge-m3'
LLM_MODEL = 'vikhr'


def setup_database():
    db_connection = sqlite3.connect(DATA_DB_NAME)
    db_connection.enable_load_extension(True)
    sqlite_vec.load(db_connection)
    db_connection.enable_load_extension(False)
    return db_connection

def setup_log_database():
    log_db = sqlite3.connect(LOG_DB_NAME)
    log_db.execute('''CREATE TABLE IF NOT EXISTS logs
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       timestamp TEXT,
                       chat_id TEXT,
                       question TEXT,
                       answer TEXT,
                       context TEXT)''')
    return log_db

def retrieve_context(query: str, db_connection, embedding_model, k: int = 5) -> str:
    query_embedding = list(embedding_model.encode([query], normalize_embeddings=True))[0]
    results = db_connection.execute(
        """
    SELECT
        chunk_embeddings.id,
        distance,
        text, 
        meta_data_h,
        meta_data_source
    FROM chunk_embeddings
    LEFT JOIN chunks ON chunks.id = chunk_embeddings.id
    WHERE embedding MATCH ? AND k = ? AND distance <= 1.01
    ORDER BY distance
        """,
        [serialize_float32(query_embedding), k],
    ).fetchall()
    return "\n\nКонтекст:\n" + "\n-----\n".join([item[2] for item in results]), [item[3] for item in results], [item[4] for item in results]

def call_model(prompt: str, messages=[], temp=0.2):
    print("#"*10)
    print('messages',messages)
    print("#"*10)

    max_retries = 3
    retry_delay = 1  # в сек

    for attempt in range(max_retries):
        try:
            ans = model_response(*messages.values())
            return ans
        except:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return "Извините, произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз позже."

def ask_question(query: str, db_connection, embedding_model, conversation_history, log_db, chat_id) -> str:
    context, meta_datas, sources = retrieve_context(query, db_connection, embedding_model)
    prompt = dedent(f"""
    Используй следующую информацию:

    ```
    {context}
    ```

    чтобы ответить на вопрос:
    {query}
    """)
    print("#"*10)
    print('conversation_history',conversation_history)

    print("#"*10)
    conversation_history.append({"role": "user", "content": prompt})
    if len(sources) > 0 or len(query) < 2:
        response = call_model(prompt, conversation_history, temp=0.2)
    else:
        response = "Мне очень хочется помочь вам с вашим вопросом, но, к сожалению, я не нашёл нужную информацию в предоставленных документах. Возможно, запрос можно переформулировать или уточнить детали, чтобы я мог более точно и эффективно обработать его. Буду рад, если вы подскажете, что именно вас интересует, и я постараюсь найти подходящий ответ!"
    conversation_history.append({"role": "assistant", "content": response})
    
    log_db.execute('INSERT INTO logs (timestamp, chat_id, question, answer, context) VALUES (?, ?, ?, ?, ?)',
                   (datetime.now().isoformat(), chat_id, query, response, json.dumps(context)))
    log_db.commit()
    
    return response, context, meta_datas, sources


def ask_question_creative(query: str, db_connection, embedding_model, conversation_history, log_db, chat_id) -> str:
    context, meta_datas, sources = retrieve_context(query, db_connection, embedding_model)
    prompt = dedent(f"""
    Используй следующую информацию:

    ```
    {context}
    ```

    чтобы креативно ответить на вопрос:
    {query}
    """)
    conversation_history.append({"role": "user", "content": prompt})
    if len(sources) > 0 or len(query) < 2:
        response = call_model(prompt, conversation_history, temp=0.5)
    else:
        response = "Мне очень хочется помочь вам с вашим вопросом, но, к сожалению, я не нашла нужную информацию в предоставленных документах. Возможно, запрос можно переформулировать или уточнить детали, чтобы я могла более точно и эффективно обработать его. Буду рада, если вы подскажете, что именно вас интересует, и я постараюсь найти подходящий ответ!"
    conversation_history.append({"role": "assistant", "content": response})
    
    log_db.execute('INSERT INTO logs (timestamp, chat_id, question, answer, context) VALUES (?, ?, ?, ?, ?)',
                   (datetime.now().isoformat(), chat_id, query, response, json.dumps(context)))
    log_db.commit()
    
    return response, context, meta_datas, sources


def get_relevant_problems(questions):
    user_prompt = '\n'.join(questions)
    prompt = prompt_summarize + '\n' + user_prompt
    relevant_problems = call_model(prompt, [])
    return relevant_problems.splitlines()
def get_uncertain_questions(problems, db_connection, embedding_model, thr = 0.5):
    need_clarification = []
    for problem in problems:
        q_data = retrieve_context(retrieve_context(problem, db_connection, embedding_model))
        if q_data['distances'][0] < thr:
            need_clarification.append(problem)
    return need_clarification




def main():
    db_connection = setup_database()
    log_db = setup_log_database()
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    conversation_history = [{"role": "system", "content": prompt_denis}]
    chat_id = datetime.now().strftime("%Y%m%d%H%M%S")

    print("Добро пожаловать! Меня зовут Денис, я ваш помощник, готовый ответить на все вопросы.")
    print("Для очистки диалога введите 'очистка'.\nДля выхода введите 'выход'.")

    while True:
        query = input("\nВаш вопрос: ")
        if query.lower() == 'выход':
            break
        elif query.lower() == 'очистка диалога':
            conversation_history = [{"role": "system", "content": prompt_denis}]
            chat_id = datetime.now().strftime("%Y%m%d%H%M%S")
            print("Диалог очищен.")
            continue

        response, context, meta_datas, sources = ask_question(query, db_connection, embedding_model, conversation_history, log_db, chat_id)
        print('\nОтвет:')
        print(response)
        print('\nОткуда взята информация:')
        print(', '.join(set(meta_datas)))
        print('\nИсточники:')
        print(', '.join(set(sources)))

    db_connection.close()
    log_db.close()
    print("Спасибо за использование нашей системы. Хорошего дня!")

if __name__ == "__main__":
    main()
