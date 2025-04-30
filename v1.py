import sqlite3
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio


# Токен бота
TOKEN = '7634171130:AAHOvDeDe8ywaqgGZHAU4n8JzFdEC_u0zDU'

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Создание базы данных
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    role TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    middle_name TEXT,
                    grade TEXT,
                    username TEXT,
                    project_topic TEXT,
                    password TEXT,
                    curator_id INTEGER,
                    curator_request_status TEXT DEFAULT 'pending')''')
conn.commit()
cursor.execute('''CREATE TABLE IF NOT EXISTS curator_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    teacher_id INTEGER,
                    status TEXT DEFAULT 'pending')''')
conn.commit()

# Создание таблицы для заданий
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    teacher_id INTEGER,
                    task_text TEXT,
                    deadline TEXT,
                    status TEXT)''')
conn.commit()

cursor.execute('''ALTER TABLE tasks ADD COLUMN media_id TEXT''')
cursor.execute('''ALTER TABLE tasks ADD COLUMN media_type TEXT''')
conn.commit()

# Состояния для FSM
class Registration(StatesGroup):
    choosing_role = State()
    student_name = State()
    student_class = State()
    student_project_topic = State()
    teacher_name = State()
    teacher_password = State()

class CuratorRequest(StatesGroup):
    teacher_fio = State()
    teacher_password = State()

# Inline-клавиатура для выбора роли
role_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='🧑‍🎓Ученик', callback_data='role_student')],
        [InlineKeyboardButton(text='👨‍🏫Учитель', callback_data='role_teacher')]
    ]
)

# Inline-клавиатура для подтверждения кураторства
curator_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='✅Согласен', callback_data='curator_accept')],
        [InlineKeyboardButton(text='❌Отказ', callback_data='curator_decline')]
    ]
)

# Inline-клавиатура для студентов
students_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Вернуться назад', callback_data='back_to_students')]
    ]
)
