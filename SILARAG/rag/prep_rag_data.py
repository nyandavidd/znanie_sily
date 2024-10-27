import sqlite3
import os
import json
from typing import List

import sqlite_vec
from sqlite_vec import serialize_float32
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from docling.document_converter import DocumentConverter
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from md_conv import file_to_md  

SOURCE_DIR = "data/"
OUTPUT_DIR = "md_output/"
DB_NAME = "../SILA.sqlite3"
EMBEDDING_MODEL = 'deepvk/USER-bge-m3'

def generate_chunks(md_data: str) -> List[str]:
    """
    Разделяет текст из markdown-документа на части.

    Параметры:
        md_data (str): Исходный текст в формате markdown.

    Возвращает:
        List[str]: Список из частей текста.
    """
    headers = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers, strip_headers=False)
    header_splits = markdown_splitter.split_text(md_data)

    chunk_size = 2048
    chunk_overlap = 512
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    text_chunks = text_splitter.split_documents(header_splits)
    return text_chunks

def init_database(db_connection):
    """
    Инициализирует структуру базы данных, создавая необходимые таблицы.

    Параметры:
        db_connection: Объект подключения к базе данных.
    """
    db_connection.enable_load_extension(True)
    sqlite_vec.load(db_connection)
    db_connection.enable_load_extension(False)

    db_connection.execute("""
    CREATE TABLE IF NOT EXISTS documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        meta_data_h TEXT,
        meta_data_source TEXT
    );
    """
    )

    db_connection.execute("""
    CREATE TABLE IF NOT EXISTS chunks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        text TEXT,
        meta_data_h TEXT,
        meta_data_source TEXT,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    );
    """
    )
    db_connection.commit()

def create_embeddings_table(db_connection, embedding_dim):
    """
    Создаёт таблицу для хранения векторных представлений слов.

    Параметры:
        db_connection: Объект подключения к базе данных.
        embedding_dimension (int): Размерность векторных представлений слов.
    """
    db_connection.execute(f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
        id INTEGER PRIMARY KEY,
        embedding FLOAT[{embedding_dim}]
    );
    """
    )
    db_connection.commit()

def save_chunks(db_connection, chunks: List[str], meta_data: List[dict], model, doc_id: int):
    """
    Сохраняет части текста и их векторные представления слов в базе данных.

    Параметры:
        db_connection: Объект подключения к базе данных.
        chunks (List[str]): Список частей текста.
        meta_data (List[dict]): Список метаданных для каждой части текста.
        model: Модель для генерации векторных представлений слов.
        doc_id (int): ID документа в базе данных.
    """
    try:
        chunk_embeddings = list(model.encode(chunks, normalize_embeddings=True))
        for chunk, embedding, meta in zip(chunks, chunk_embeddings, meta_data):
            if len(list(meta.values())) < 2:
                continue
            result = db_connection.execute(
                "INSERT INTO chunks(document_id, text, meta_data_h, meta_data_source) VALUES(?, ?, ?, ?)", 
                [doc_id, chunk, *list(meta.values())]
            )
            chunk_id = result.lastrowid
            db_connection.execute(
                "INSERT INTO chunk_embeddings(id, embedding) VALUES (?, ?)",
                [chunk_id, serialize_float32(embedding)],
            )
        db_connection.commit()
    except Exception:
        pass

def main():
    """
        Основная функция для выполнения преобразования файлов, создания эмбеддингов и сохранения данных в базу данных.
    """
    input_dir = SOURCE_DIR
    output_dir = OUTPUT_DIR

    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Initialize SentenceTransformer model
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Setup database
    db_path = os.path.abspath(DB_NAME)
    db_connection = sqlite3.connect(DB_NAME)
    init_database(db_connection)
    # Process each file in the input directory
    for root, _, files in os.walk(input_dir):
        print(1111111111)
        for file in tqdm(files, desc="Processing files"):

            input_path = os.path.join(root, file)
            print(input_path)
            relative_path = os.path.relpath(root, input_dir)
            output_path_dir = os.path.join(output_dir, relative_path)
            if not os.path.exists(output_path_dir):
                os.makedirs(output_path_dir)

            output_file = os.path.splitext(file)[0] + '.md'
            output_path = os.path.join(output_dir, output_file)
            
            # Convert file to markdown
            try:
                file_to_md(input_path, output_path)
            except Exception:
                print('Данные не конвертировались')

                continue

            # Read markdown file
            try:
                with open(output_path, "r", encoding='utf-8') as f:
                    data = f.read()
            except Exception:
                print('Данные не открылись')

                continue

            # Create chunks
            splits = generate_chunks(data)

            # Create embeddings
            try:
                embeddings = model.encode([chunk.page_content for chunk in splits], normalize_embeddings=True)
            except Exception:
                continue

            # Create embeddings table if not exists
            if root == input_dir and file == files[0]:  # Assuming embedding size is consistent
                if len(embeddings) > 0 and hasattr(embeddings[0], 'shape'):
                    embedding_size = embeddings[0].shape[0]
                else:
                    embedding_size = len(embeddings[0])
                create_embeddings_table(db_connection, embedding_size)

            # Insert document and get document_id
            meta_document = {
                "source": input_path,
                "description": "Full Document"
            }
            try:
                cursor = db_connection.execute(
                    "INSERT INTO documents(text, meta_data_h, meta_data_source) VALUES(?, ?, ?)", 
                    [data, *list(meta_document.values())]
                )
                document_id = cursor.lastrowid
                db_connection.commit()
                print('Данные добавились в таблицу')

            except Exception:
                print('Данные не добавились в таблицу')
                continue

            # Prepare metadata for chunks
            try:
                chunks_text = [chunk.page_content for chunk in splits]
                chunks_meta = [{"source": input_path, **chunk.metadata} for chunk in splits]
            except Exception:
                print('Данные не добавились в таблицу')

                continue

            # Save chunks and their embeddings
            save_chunks(db_connection, chunks_text, chunks_meta, model, document_id)
            print('Успешно.')

    if 'db_connection' in locals():
        db_connection.close()

if __name__ == "__main__":
    main()
    '''
    input_dir = SOURCE_DIR
    output_dir = OUTPUT_DIR

    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Initialize SentenceTransformer model
    model = SentenceTransformer(EMBEDDING_MODEL)
    output_path = 'md_output/data.md'
    # Setup database
    db_path = os.path.abspath(DB_NAME)
    db_connection = sqlite3.connect(DB_NAME)
    init_database(db_connection)
    with open(output_path, "r", encoding='utf-8') as f:
        data = f.read()
        splits = generate_chunks(data[1000:3000])
        embeddings = model.encode([chunk.page_content for chunk in splits], normalize_embeddings=True)
        if len(embeddings) > 0 and hasattr(embeddings[0], 'shape'):
            embedding_size = embeddings[0].shape[0]
        else:
            embedding_size = len(embeddings[0])
        create_embeddings_table(db_connection, embedding_size)

        meta_document = {
            "source": SOURCE_DIR,
            "description": "Full Document"
        }
        cursor = db_connection.execute(
            "INSERT INTO documents(text, meta_data_h, meta_data_source) VALUES(?, ?, ?)", 
                [data, *list(meta_document.values())]
        )
        document_id = cursor.lastrowid
        db_connection.commit()
        print('Данные добавились в таблицу')
        print('Данные не добавились в таблицу')
        

            # Prepare metadata for chunks
        chunks_text = [chunk.page_content for chunk in splits]
        chunks_meta = [{"source": SOURCE_DIR, **chunk.metadata} for chunk in splits]
       

            # Save chunks and their embeddings
        save_chunks(db_connection, chunks_text, chunks_meta, model, document_id)

    if 'db_connection' in locals():
        db_connection.close()
    '''
