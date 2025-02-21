import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram import executor
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

# Отримуємо токен із змінної середовища
TOKEN = os.getenv("7421379071:AAEu0-FZdi1KBzpusgFc4Ipe2e3oCqoPiZ8")

if not TOKEN:
    print("TOKEN не знайдено!")
    exit(1)

# Ініціалізація бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Функція для читання EPUB
def read_epub(file_path):
    book = epub.read_epub(file_path)
    content = []
    
    # Переглядаємо всі елементи книги (наприклад, <body> з HTML)
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_body(), 'html.parser')
            # Додаємо лише текст з HTML елементів
            content.append(soup.get_text())
    
    return "\n".join(content)  # Повертатимемо весь текст книги як один рядок

# Хендлер для команди /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Привіт! Я бот для обробки книг у форматі EPUB. Надішліть мені файл EPUB!")

# Хендлер для отримання файлів
@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_epub(message: types.Message):
    # Перевірка чи це файл EPUB
    file_name = message.document.file_name
    if file_name.endswith('.epub'):
        # Завантаження файлу
        file_info = await bot.get_file(message.document.file_id)
        file_path = file_info.file_path
        file = await bot.download_file(file_path)
        
        # Збереження файлу
        with open('temp_book.epub', 'wb') as f:
            f.write(file)
        
        # Читання вмісту книги
        book_content = read_epub('temp_book.epub')
        
        # Відправка частини тексту (щоб не перевантажити Telegram)
        await message.reply(f"Ось частина вмісту книги:\n\n{book_content[:4096]}")  # Обмеження 4096 символів
    else:
        await message.reply("Це не EPUB файл. Будь ласка, надішліть EPUB файл.")

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
