import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from ebooklib import epub
from bs4 import BeautifulSoup

# 🔹 Логування
logging.basicConfig(level=logging.INFO)

# 🔹 Встав свій Telegram токен
TOKEN = "7421379071:AAEu0-FZdi1KBzpusgFc4Ipe2e3oCqoPiZ8"

# 🔹 Ініціалізація бота
from aiogram.client.default import DefaultBotProperties

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# 📌 Словник для збереження стану користувачів
user_data = {}

# 🔹 Стан для обробки книги
class BookState(StatesGroup):
    waiting_for_file = State()
    selecting_chapter = State()
    reading = State()

# 🔹 Обробник команди /start
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(BookState.waiting_for_file)
    await message.answer("Привіт! Надішліть мені файл у форматі EPUB, і я його прочитаю.")

# 🔹 Обробка прийнятого EPUB файлу
@dp.message(lambda message: message.document and message.document.mime_type == "application/epub+zip")
async def handle_epub(message: types.Message, state: FSMContext):
    document = message.document
    file_path = f"books/{document.file_id}.epub"

    # 🔹 Створюємо папку для збереження книг
    os.makedirs("books", exist_ok=True)
    await bot.download(document, file_path)

    await message.answer("Файл отримано! Обробляю книгу...")

    # 🔹 Читаємо текст з книги
    chapters = extract_chapters_from_epub(file_path)

    if not chapters:
        await message.answer("Не вдалося прочитати книгу.")
        return

    # 🔹 Зберігаємо дані про книгу
    user_data[message.chat.id] = {
        "file_path": file_path,
        "chapters": chapters,
        "current_chapter": 0,
        "message_length": 2000  # Значення за замовчуванням
    }

    # 🔹 Відправляємо меню вибору глави
    await send_chapter_selection(message.chat.id, chapters)

# 🔹 Функція отримання глав з EPUB
def extract_chapters_from_epub(file_path):
    try:
        book = epub.read_epub(file_path)
        chapters = []
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_body_content(), "html.parser")
                text = soup.get_text()
                chapters.append(text.strip())
        return chapters
    except Exception as e:
        logging.error(f"Помилка при зчитуванні EPUB: {e}")
        return None

# 🔹 Відправка меню вибору глави
async def send_chapter_selection(chat_id, chapters):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📖 Глава {i+1}", callback_data=f"chapter_{i}")]
        for i in range(len(chapters))
    ])
    await bot.send_message(chat_id, "Оберіть главу:", reply_markup=keyboard)

# 🔹 Обробка натискання кнопки вибору глави
@dp.callback_query(F.data.startswith("chapter_"))
async def select_chapter(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    chapter_index = int(callback.data.split("_")[1])

    user_data[chat_id]["current_chapter"] = chapter_index

    await callback.message.answer(f"📖 Ви обрали главу {chapter_index + 1}. Починаємо читання!")
    await send_text_in_parts(chat_id)

# 🔹 Відправка частини тексту
async def send_text_in_parts(chat_id):
    data = user_data.get(chat_id)
    if not data:
        return

    chapter_index = data["current_chapter"]
    message_length = data["message_length"]
    text = data["chapters"][chapter_index]

    for i in range(0, len(text), message_length):
        await bot.send_message(chat_id, text[i:i + message_length])
        await asyncio.sleep(1)  # Запобігаємо обмеженням Telegram

    # 🔹 Відправляємо кнопки навігації
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Попередня", callback_data="prev_chapter"),
         InlineKeyboardButton(text="➡️ Наступна", callback_data="next_chapter")],
        [InlineKeyboardButton(text="⚙️ Довжина повідомлень", callback_data="set_length")]
    ])
    await bot.send_message(chat_id, "📚 Що далі?", reply_markup=keyboard)

# 🔹 Обробка кнопок навігації
@dp.callback_query(F.data == "prev_chapter")
async def prev_chapter(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if user_data[chat_id]["current_chapter"] > 0:
        user_data[chat_id]["current_chapter"] -= 1
        await send_text_in_parts(chat_id)
    else:
        await callback.answer("Це перша глава.")

@dp.callback_query(F.data == "next_chapter")
async def next_chapter(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if user_data[chat_id]["current_chapter"] < len(user_data[chat_id]["chapters"]) - 1:
        user_data[chat_id]["current_chapter"] += 1
        await send_text_in_parts(chat_id)
    else:
        await callback.answer("Це остання глава.")

# 🔹 Обробка зміни довжини повідомлень
@dp.callback_query(F.data == "set_length")
async def set_message_length(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1000 символів", callback_data="length_1000")],
        [InlineKeyboardButton(text="2000 символів", callback_data="length_2000")],
        [InlineKeyboardButton(text="4096 символів (макс)", callback_data="length_4096")]
    ])
    await bot.send_message(callback.message.chat.id, "🔧 Виберіть довжину повідомлень:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("length_"))
async def change_message_length(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    length = int(callback.data.split("_")[1])
    user_data[chat_id]["message_length"] = length
    await callback.message.answer(f"✅ Довжина повідомлень встановлена на {length} символів.")

# 🔹 Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
