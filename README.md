# znanie_sily
## Разработка Q&A бота для помощи в работе с приложением
В качестве LLM используется YandexGPT

Для запуска необходимо:
1. Установить зависимости:
   ``` cd SILARAG/rag```
  ```pip install -r requirements.txt ```
 
2. Запустить файл конфигурации БД пользователей: python3 prep_users_db.py
3. Запустить модуль мониторинга обновления БД: python3 update_db.py
4. Запустите телеграм-бота: python3 bot.py
