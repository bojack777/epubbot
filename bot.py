import os
import threading
import asyncio
import logging
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from ebooklib import epub
from bs4 import BeautifulSoup
print(f"TOKEN: {TOKEN}")  # Друкуємо токен у логах
# Налаштування логування
logging.basicConfig(level=logging.INFO)
TOKEN = "7421379071:AAEu0-FZdi1KBzpusgFc4Ipe2e3oCqoPiZ8"

# Отримання токена з середовища
TOKEN = os.getenv("7421379071:AAEu0-FZdi1KBzpusgFc4Ipe2e3oCqoPiZ8")

# Ініціалізація бота з новими параметрами
from aiogram.enums import ParseMode

...
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher(bot)

# Простий Flask сервер для відкриття порту (Render потребує відкритого порту)
app = Flask(__name__)

@app.route('/')
def index():
    return "Бот працює!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Запускаємо Flask у окремому потоці
threading.Thread(target=run_flask).start()

# Словник для збереження книг по користувачам
user_books = {}

# Обробка команди /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привіт! Надішли мені книгу у форматі EPUB 📚")

# Обробка отриманого файлу EPUB
@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message):
    if not message.document.file_name.endswith(".epub"):
        await message.answer("Будь ласка, надішли файл у форматі EPUB 📖")
        return

    file_id = message.document.file_id
    file_path = f"downloads/{file_id}.epub"
    os.makedirs("downloads", exist_ok=True)
    await message.document.download(destination=file_path)
    await message.answer("Книга отримана! Обробляю...")

    try:
        book = epub.read_epub(file_path)
        text = ""
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_body_content(), "html.parser")
                text += soup.get_text() + "\n\n"
        user_books[message.chat.id] = text
        await message.answer("Книга готова до читання! Напиши /read, щоб почати.")
    except Exception as e:
        await message.answer("Виникла помилка при обробці книги.")
        logging.error(f"Error reading EPUB: {e}")

# Команда /read – відправка тексту частинами
@dp.message_handler(commands=['read'])
async def send_book(message: types.Message):
    user_id = message.chat.id
    if user_id not in user_books:
        await message.answer("Спочатку надішли книгу!")
        return

    text = user_books[user_id]
    chunk_size = 1000  # можна налаштувати
    for i in range(0, len(text), chunk_size):
        await message.answer(text[i:i+chunk_size])
        await asyncio.sleep(1)
    await message.answer("Це кінець книги!")

# Асинхронна функція для запуску polling
async def main():
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())


