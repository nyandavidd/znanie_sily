import sqlite3
import hashlib
"""
Файл создает базу данных пользователей с таблицей, содержащей информацию о пользователях, включая:
- Электронная почта (уникальный идентификатор)
- Хэш пароля
- Уровень доступа
- Регион, отдел, позицию
- Доступные документы

Используемая база данных - SQLite.
"""
# Подключение к базе данных
connection = sqlite3.connect('users.db')
cursor = connection.cursor()

# Создаем таблицу пользователей
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    access_level INTEGER DEFAULT 0,
    region TEXT NOT NULL,
    department TEXT NOT NULL,
    position TEXT NOT NULL,
    accessed_docs TEXT DEFAULT ""
)''')

# Применяем изменения и закрываем соединение с базой данных
connection.commit()
connection.close()


