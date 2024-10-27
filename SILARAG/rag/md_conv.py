import os
import subprocess
import argparse
from docling.document_converter import DocumentConverter

converter = DocumentConverter()

def pdf_to_md(source: str, output: str):
    """
    Конвертирует PDF файл в Markdown.

    Args:
        source (str): Путь к исходному PDF файлу.
        output (str): Путь, где будет сохранен файл в формате Markdown.
    """
    global converter
    result = converter.convert_single(source)
    data = result.render_as_markdown()
    with open(output, "w") as f:
        f.write(data)


def file_to_md(input_file, output_file):
    print(1)
    """
    Конвертирует указанный файл в Markdown с использованием Pandoc (кроме PDF).

    Args:
        input_file (str): Путь к входному файлу.
        output_file (str): Путь, где будет сохранен файл в формате Markdown.
    """
    if input_file.lower().endswith('.pdf'):
        pdf_to_md(input_file, output_file)
    else:
        # Определяем формат входного файла на основе его расширения
        _, file_extension = os.path.splitext(input_file)
        
        input_format = file_extension[1:] if file_extension else 'txt'

        subprocess.run([
            'pandoc',
            '-f', input_format,
            '-t', 'pdf',
            '--pdf-engine', 'weasyprint',
            input_file,
            '-o', input_file + '.pdf'
        ], check=True)
        pdf_to_md(input_file + '.pdf', output_file)

    print(f"Файл '{input_file}' конвертирован в '{output_file}'")


def dir_to_md(input_dir, output_dir):
    """
    Обрабатывает все файлы в указанной директории, конвертируя их в Markdown.

    Args:
        input_dir (str): Директория с входными файлами.
        output_dir (str): Директория, где будут сохранены файлы в формате Markdown.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for root, _, files in os.walk(input_dir):
        for file in files:
            input_path = os.path.join(root, file)
            relative_path = os.path.relpath(root, input_dir)
            output_path_dir = os.path.join(output_dir, relative_path)
            if not os.path.exists(output_path_dir):
                os.makedirs(output_path_dir)
            output_file = os.path.splitext(file)[0] + '.md'
            output_path = os.path.join(output_path_dir, output_file)
            file_to_md(input_path, output_path)


def main():
    """
    Основная функция для запуска скрипта, обрабатывающего конвертацию файлов или директорий.
    """
    parser = argparse.ArgumentParser(description="Конвертация файлов в Markdown с использованием Pandoc (кроме PDF).")
    parser.add_argument('input', help="Путь к входному файлу или директории.")
    parser.add_argument('output', help="Путь к выходному Markdown файлу или директории.")
    args = parser.parse_args()

    if os.path.isfile(args.input):
        if args.input.lower().endswith('.pdf'):
            print("Конвертация PDF обрабатывается отдельно. Пропускаем этот файл.")
            return
        file_to_md(args.input, args.output)
    elif os.path.isdir(args.input):
        dir_to_md(args.input, args.output)
    else:
        print("Недопустимый путь. Пожалуйста, укажите корректный файл или директорию.")


if __name__ == "__main__":
    main()
