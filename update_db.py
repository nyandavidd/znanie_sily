import sqlite3
import os
from typing import List

import sqlite_vec
from sqlite_vec import serialize_float32
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from SILARAG.rag.md_conv import file_to_md  

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
SOURCE_DIR = "./SILARAG/rag/data"
OUTPUT_DIR = "./SILARAG/rag/md_output"
DB_NAME = "SILA.sqlite3"
EMBEDDING_MODEL = 'deepvk/USER-bge-m3'


def split_into_chunks(text: str) -> List[dict]:
    """
    Разделяет текст на части, используя заголовки и размер частей.

    Параметры:
    text (str): Исходный текст для разделения.

    Возвращает:
    List[dict]: Список частей текста с метаданными.
    """
    headers = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers, strip_headers=False)
    header_splits = markdown_splitter.split_text(text)

    chunk_size = 2048
    chunk_overlap = 512
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_documents(header_splits)
    
    return chunks

def initialize_database(db_connection):
    """
    Инициализирует базу данных, загружая расширения и создавая необходимые таблицы.

    Параметры:
    db_connection (sqlite3.Connection): Соединение с базой данных.
    """
    try:
        db_connection.enable_load_extension(True)
        sqlite_vec.load(db_connection)
        db_connection.enable_load_extension(False)
        logging.info("Расширения SQLite успешно загружены.")
    except sqlite3.OperationalError as error:
        logging.error(f"Ошибка загрузки расширений SQLite: {error}")
        raise

    try:
        db_connection.execute("""
        CREATE TABLE IF NOT EXISTS documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            meta_data_h TEXT,
            meta_data_source TEXT
        );
        """)

        db_connection.execute("""
        CREATE TABLE IF NOT EXISTS chunks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            text TEXT,
            meta_data_h TEXT,
            meta_data_source TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        );
        """)
        db_connection.commit()
        logging.info("Таблицы успешно созданы.")
    except sqlite3.Error as e:
        logging.error(f"Таблицы не созданы: {e}")
        db_connection.rollback()
        raise


def create_embeddings_table(db_connection, embedding_dim: int):
    """
    Создает таблицу для хранения векторных представлений, если она еще не создана.

    Параметры:
    db_connection (sqlite3.Connection): Соединение с базой данных.
    embedding_dim (int): Размерность векторных представлений.
    """

    try:
        db_connection.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
            id INTEGER PRIMARY KEY,
            embedding FLOAT[{embedding_dim}]
        );
        """)
        db_connection.commit()
        logging.info("Таблица 'embeddings' успешно создана или уже существует.")
    except sqlite3.Error as e:
        logging.error(f"Ошибка создания таблицы 'embeddings': {e}")
        db_connection.rollback()
        raise


def save_chunks(db_connection, chunks: List[str], meta_data: List[dict], model, document_id: int):
    """
    Сохраняет текст, разделённый на части, в базе данных.

    Параметры:
    db_connection (sqlite3.Connection): Соединение с базой данных.
    chunks (List[str]): текст, разделённый на части
    meta_data (List[dict]): метаданные текста
    model (SentenceTransformer): Модель для создания векторных представлений.
    document_id (int): 
    """
    
    try:
        chunk_embeddings = list(model.encode(chunks, normalize_embeddings=True))
        for chunk, embedding, meta in zip(chunks, chunk_embeddings, meta_data):
            if len(list(meta.values())) < 2:
                continue
            cursor = db_connection.execute(
                "INSERT INTO chunks(document_id, text, meta_data_h, meta_data_source) VALUES(?, ?, ?, ?)", 
                (document_id, chunk, meta.get("header", ""), meta.get("source", ""))
            )
            chunk_id = cursor.lastrowid
            db_connection.execute(
                "INSERT INTO chunk_embeddings(id, embedding) VALUES (?, ?)",
                (chunk_id, serialize_float32(embedding)),
            )
        db_connection.commit()
        logging.info(f"Saved {len(chunks)} chunks and their embeddings.")
    except Exception as e:
        logging.error(f"Error saving chunks: {e}")
        db_connection.rollback()


def process_file(db_connection, model, in_path: str, out_path: str):
    """
    Обрабатывает файл, конвертирует его в Markdown, разделяет на части и сохраняет в базу данных.

    Параметры:
    db_connection (sqlite3.Connection): Соединение с базой данных.
    model (SentenceTransformer): Модель для создания векторных представлений.
    in_path (str): Путь к входному файлу.
    output_filepath (str): Путь для сохранения конвертированного файла.
    """
    try:
        file_to_md(in_path, out_path)
        logging.info(f"{in_path} конвертирован в .md")
    except Exception as e:
        logging.error(f"Ошибка конвертации {in_path} в .md: {e}")
        return

    try:
        with open(out_path, "r", encoding='utf-8') as f:
            data = f.read()
        logging.info(f"Прочитан .md {out_path}.")
    except Exception as e:
        logging.error(f"Ошибка чтения .md {out_path}: {e}")
        return

    splits = split_into_chunks(data)
    if not splits:
        logging.warning(f"Нет разделённого текста для {in_path}.")
        return
    meta_document = {
        "source": in_path,
        "description": "Full Document"
    }
    try:
        cursor = db_connection.execute(
            "INSERT INTO documents(text, meta_data_h, meta_data_source, file_path) VALUES(?, ?, ?, ?)", 
            (data, meta_document.get("description", ""), meta_document.get("source", ""), in_path)
        )
        document_id = cursor.lastrowid
        db_connection.commit()
        logging.info(f"Добавлен документ {in_path} с ID {document_id}.")
    except sqlite3.IntegrityError:
        logging.warning(f"Файл {in_path} уже обработан.")
        db_connection.rollback()
        return
    except Exception as e:
        logging.error(f"Ошибка добавления документа {in_path}: {e}")
        db_connection.rollback()
        return

    # Подготовка метаданных для частей текста
    try:
        chunks_text = [chunk.page_content for chunk in splits]
        chunks_meta = [{"source": in_path, "header": chunk.metadata.get("header", "Unknown")} for chunk in splits]
        logging.info(f"Подготовлены метаданные для {len(chunks_text)} частей текста.")
    except Exception as e:
        logging.error(f"Ошибка подготовки метаданных частей текста {in_path}: {e}")
        return

    # Сохранение частей текста и их векторных представлений
    save_chunks(db_connection, chunks_text, chunks_meta, model, document_id)


class FileHandler(FileSystemEventHandler):
    """
    Обработчик событий для отслеживания новых файлов в директории.
    """
    def __init__(self, db_connection, model):
        super().__init__()
        self.db = db_connection
        self.model = model

    def on_created(self, event):
        if not event.is_directory:
            in_path = event.src_path
            relative_path = os.path.relpath(os.path.dirname(in_path), SOURCE_DIR)
            out_path_dir = os.path.join(OUTPUT_DIR, relative_path)
            if not os.path.exists(out_path_dir):
                os.makedirs(out_path_dir)
                logging.info(f"Создана папка {out_path_dir}.")
            out_file = os.path.splitext(os.path.basename(in_path))[0] + '.md'
            out_path = os.path.join(out_path_dir, out_file)
            logging.info(f"Обрабатывается новый файл: {in_path}")
            process_file(self.db, self.model, in_path, out_path)


def main():
    """
    Главная функция для настройки модели, базы данных и отслеживания файлов.
    """
    try:
        logging.info(f"Загрузка модели SentenceTransformer '{EMBEDDING_MODEL}'...")
        model = SentenceTransformer(EMBEDDING_MODEL)
        logging.info("Модель успешно загружена.")

        db_path = os.path.abspath(DB_NAME)
        logging.info(f"Подключение к базе данных по пути {db_path}...")
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
        initialize_database(db_connection)

        sample_embedding = model.encode("Пример текста", normalize_embeddings=True)
        embedding_dimension = sample_embedding.shape[0] if hasattr(sample_embedding, 'shape') else len(sample_embedding)
        logging.info(f"Размерность векторных представлений: {embedding_dimension}.")

        create_embeddings_table(db_connection, embedding_dimension)

        event_handler = FileHandler(db_connection, model)
        observer = Observer()
        observer.schedule(event_handler, path=SOURCE_DIR, recursive=True)
        observer.start()
        logging.info("Начато отслеживание директории. Нажмите Ctrl+C для остановки.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Остановка отслеживания из-за KeyboardInterrupt.")
            observer.stop()
        observer.join()

    except Exception as error:
        logging.error(f"Произошла ошибка в главной функции: {error}")
    finally:
        if 'db_connection' in locals():
            db_connection.close()
            logging.info("Соединение с базой данных закрыто.")


if __name__ == "__main__":
    main()