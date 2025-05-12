import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, StateFilter
import asyncio
from datetime import datetime, timedelta
from aiogram.filters import StateFilter
from aiogram.types import ContentType
from random import randint


# Токен бота
TOKEN = ''

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

# Создание таблицы для заданий
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    teacher_id INTEGER,
                    task_text TEXT,
                    deadline TEXT,
                    status TEXT,
                    media_id TEXT,
                    media_type TEXT)''')
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

class TaskAssignment(StatesGroup):
    task_text = State()
    task_deadline = State()

class DeleteAccount(StatesGroup):
    confirm_code = State()


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

# Начальная команда /start для регистрации
@dp.message(Command('start'))
async def start_handler(message: Message, state: FSMContext):
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (message.from_user.id,))
    user = cursor.fetchone()
    if user:
      if user[0]=="Учитель":
        await message.answer(f"✖️Вы уже зарегистрированы как {user[0]}. 💻*Ваши доступные команды:*\n/students - Посмотреть список учеников, которых вы курируете.\n/delete - Удалить ваш аккаунт.", parse_mode='Markdown'"")
      elif user[0]=="Ученик":
        await message.answer(f"✖️Вы уже зарегистрированы как {user[0]}. 💻*Ваши доступные команды:*\n/curator - Отправить запрос на кураторство учителю.\n/delete - Удалить ваш аккаунт.", parse_mode='Markdown'"")
    else:
        await message.answer("👋Привет! Я помогаю с ведением ИП (индивидуальных проектов). \nВыберите свою роль:", reply_markup=role_inline_keyboard)
        await state.set_state(Registration.choosing_role)
      
# Регистрация для ученика (110 - 135)
@dp.callback_query(lambda c: c.data == 'role_student')
async def student_role_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍Введите своё Имя и Фамилию:")
    await state.set_state(Registration.student_name)

@dp.message(StateFilter(Registration.student_name))
async def student_name_handler(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🎓Введите свой класс (например, 10В):")
    await state.set_state(Registration.student_class)

@dp.message(StateFilter(Registration.student_class))
async def student_class_handler(message: Message, state: FSMContext):
    await state.update_data(grade=message.text)
    await message.answer("🔎Введите тему вашего индивидуального проекта:")
    await state.set_state(Registration.student_project_topic)

@dp.message(StateFilter(Registration.student_project_topic))
async def student_project_topic_handler(message: Message, state: FSMContext):
    user_data = await state.get_data()
    name_parts = user_data['name'].split()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, role, first_name, last_name, grade, project_topic) VALUES (?, ?, ?, ?, ?, ?)',
                   (message.from_user.id, 'Ученик', name_parts[0], name_parts[1], user_data['grade'], message.text))
    conn.commit()
    await message.answer("🥳Вы успешно зарегистрированы как Ученик!\n💻*Ваши доступные команды:*\n/curator - Отправить запрос на кураторство учителю.\n/delete - Удалить ваш аккаунт.", parse_mode='Markdown')
    await state.clear()
  
# Регистрация для учителя (138 - 158)
@dp.callback_query(lambda c: c.data == 'role_teacher')
async def teacher_role_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍Введите свою Фамилию, Имя и Отчество:")
    await state.set_state(Registration.teacher_name)

@dp.message(StateFilter(Registration.teacher_name))
async def teacher_name_handler(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🔐Введите пароль для учеников при заявки на курирование:")
    await state.set_state(Registration.teacher_password)

@dp.message(StateFilter(Registration.teacher_password))
async def teacher_password_handler(message: Message, state: FSMContext):
    user_data = await state.get_data()
    name_parts = user_data['name'].split()
    password = message.text
    cursor.execute('INSERT OR IGNORE INTO users (user_id, role, first_name, last_name, middle_name, password, username) VALUES (?, ?, ?, ?, ?, ?, ?)',
               (message.from_user.id, 'Учитель', name_parts[1], name_parts[0], name_parts[2], password, message.from_user.username))
    conn.commit()
    await message.answer("🥳Вы успешно зарегистрированы как Учитель!\n💻*Ваши доступные команды:*\n/students - Посмотреть список учеников, которых вы курируете.\n/delete - Удалить ваш аккаунт.", parse_mode='Markdown')
    await state.clear()
  
# Команда на назначение куратора (161 - 311)
@dp.message(Command('curator'))
async def curator_request(message: Message, state: FSMContext):
    await message.answer("📋 Введите Фамилию, Имя и Отчество учителя:")
    await state.set_state(CuratorRequest.teacher_fio)


@dp.message(StateFilter(CuratorRequest.teacher_fio))
async def curator_fio_handler(message: Message, state: FSMContext):
    await state.update_data(teacher_fio=message.text)
    await message.answer("🔑 Введите пароль учителя:")
    await state.set_state(CuratorRequest.teacher_password)


@dp.message(StateFilter(CuratorRequest.teacher_password))
async def curator_password_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    fio = data['teacher_fio'].split()
    password = message.text

    cursor.execute('SELECT user_id FROM users WHERE role=? AND last_name=? AND first_name=? AND middle_name=? AND password=?',
                   ('Учитель', fio[0], fio[1], fio[2], password))
    teacher = cursor.fetchone()

    if teacher:
        teacher_id = teacher[0]

        cursor.execute('SELECT first_name, last_name, grade, project_topic FROM users WHERE user_id=?',
                       (message.from_user.id,))
        student = cursor.fetchone()

        if student:
            student_first_name, student_last_name, student_grade, student_project = student

            cursor.execute('UPDATE users SET curator_id=?, curator_request_status=? WHERE user_id=?',
                           (teacher_id, 'pending', message.from_user.id))
            conn.commit()

            await bot.send_message(
                teacher_id,
                f"🔔 *Заявка на кураторство*\n"
                f"*{student_first_name} {student_last_name}* из *{student_grade}* хочет, чтобы вы его курировали.\n"
                f"📚 Тема проекта: *{student_project}*",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text='✅ Принять', callback_data=f'curator_accept_{message.from_user.id}')],
                        [InlineKeyboardButton(text='❌ Отклонить', callback_data=f'curator_decline_{message.from_user.id}')]
                    ]
                ),
                parse_mode='Markdown'
            )

            await message.answer("✅ Запрос отправлен учителю.")
        else:
            await message.answer("❌ Не удалось найти ваши данные. Пройдите регистрацию заново.")
    else:
        await message.answer("❌ Некорректные данные учителя.")

    await state.clear()



@dp.callback_query(lambda c: c.data.startswith('curator_accept_'))
async def curator_accept_handler(callback: types.CallbackQuery):
    student_id = int(callback.data.split('_')[2])  # ID ученика из callback_data
    teacher_id = callback.from_user.id

    # Проверяем статус заявки
    cursor.execute('SELECT curator_request_status FROM users WHERE user_id=?', (student_id,))
    status = cursor.fetchone()

    if status and status[0] != 'pending':
        await callback.answer("❌ Заявка уже обработана.")
        return

    # Обновляем статус
    cursor.execute('UPDATE users SET curator_request_status=? WHERE user_id=?', ('accepted', student_id))
    conn.commit()

    # Удаляем инлайн-клавиатуру
    await callback.message.edit_text(
        f"✅ Заявка ученика подтверждена.",
        parse_mode='Markdown'
    )

    # Получаем данные
    cursor.execute('SELECT first_name, last_name FROM users WHERE user_id=?', (student_id,))
    student = cursor.fetchone()

    cursor.execute('SELECT first_name, last_name, middle_name FROM users WHERE user_id=?', (teacher_id,))
    teacher = cursor.fetchone()

    if student and teacher:
        student_name = f"{student[0]} {student[1]}"
        teacher_name = f"{teacher[1]} {teacher[0]} {teacher[2]}"

        # Сообщение ученику
        await bot.send_message(
            student_id,
            f"✅ *Ваш куратор подтвердил запрос!*\n"
            f"👤 *Куратор:* {teacher_name}",
            parse_mode='Markdown'
        )

        # Сообщение учителю
        await callback.answer("✅ Вы подтвердили запрос.")


@dp.callback_query(lambda c: c.data.startswith('curator_decline_'))
async def curator_decline_handler(callback: types.CallbackQuery):
    student_id = int(callback.data.split('_')[2])  # ID ученика из callback_data
    teacher_id = callback.from_user.id

    # Проверяем статус заявки
    cursor.execute('SELECT curator_request_status FROM users WHERE user_id=?', (student_id,))
    status = cursor.fetchone()

    if status and status[0] != 'pending':
        await callback.answer("❌ Заявка уже обработана.")
        return

    # Обновляем статус
    cursor.execute('UPDATE users SET curator_id=NULL, curator_request_status=? WHERE user_id=?', ('declined', student_id))
    conn.commit()

    # Удаляем инлайн-клавиатуру
    await callback.message.edit_text(
        f"❌ Заявка ученика отклонена.",
        parse_mode='Markdown'
    )

    # Получаем данные
    cursor.execute('SELECT first_name, last_name FROM users WHERE user_id=?', (student_id,))
    student = cursor.fetchone()

    cursor.execute('SELECT first_name, last_name, middle_name FROM users WHERE user_id=?', (teacher_id,))
    teacher = cursor.fetchone()

    if student and teacher:
        student_name = f"{student[0]} {student[1]}"
        teacher_name = f"{teacher[1]} {teacher[0]} {teacher[2]}"

        # Сообщение ученику
        await bot.send_message(
            student_id,
            f"❌ *Ваш куратор отклонил запрос.*\n"
            f"👤 *Куратор:* {teacher_name}",
            parse_mode='Markdown'
        )

        # Сообщение учителю
        await callback.answer("❌ Вы отклонили запрос.")


# Команда /students для кураторов
@dp.message(Command('students'))
async def teacher_students_handler(message: Message):
    cursor.execute('SELECT user_id, first_name, last_name, grade FROM users WHERE curator_id = ?', (message.from_user.id,))
    students = cursor.fetchall()
    if students:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f'{student[1]} {student[2]} ({student[3]})', callback_data=f'student_{student[0]}')] for student in students
        ])
        await message.answer("👩‍🎓 *Ваши ученики:*", reply_markup=keyboard, parse_mode='Markdown')
    else:
        await message.answer("❌ *У вас нет учеников.*", parse_mode='Markdown')

# Обработчик выбора ученика
@dp.callback_query(lambda c: c.data.startswith('student_') and not c.data.startswith('student_remove_'))
async def student_info_handler(callback: types.CallbackQuery):
    try:
        student_id = int(callback.data.split('_')[1])  # Теперь уверены, что это ID ученика
        cursor.execute('SELECT first_name, last_name, grade, project_topic FROM users WHERE user_id = ?', (student_id,))
        student = cursor.fetchone()
        if student:
            await callback.message.edit_text(
                f"👤 *Ученик:* {student[0]} {student[1]}\n"
                f"🏫 *Класс:* {student[2]}\n"
                f"📚 *Тема проекта:* {student[3]}",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text='📝 Задать задание', callback_data=f'task_assign_{student_id}')],
                        [InlineKeyboardButton(text='❌ Удалить ученика', callback_data=f'student_remove_{student_id}')],
                        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_students')]
                    ]
                )
            )
    except (IndexError, ValueError) as e:
        await callback.answer("❌ Произошла ошибка при обработке данных.")
        print(f"Ошибка: {e}")

    await callback.answer()

# Обработчик удаления ученика
@dp.callback_query(lambda c: c.data.startswith('student_remove_'))
async def student_remove_handler(callback: types.CallbackQuery):
    try:
        student_id = int(callback.data.split('_')[2])
        teacher_id = callback.from_user.id

        cursor.execute('SELECT curator_id FROM users WHERE user_id = ?', (student_id,))
        curator = cursor.fetchone()

        if curator and curator[0] == teacher_id:
            cursor.execute('UPDATE users SET curator_id = NULL WHERE user_id = ?', (student_id,))
            conn.commit()

            await callback.message.edit_text(
                "✅ *Ученик был успешно удален из вашего списка.*",
                parse_mode='Markdown'
            )

            await bot.send_message(
                student_id,
                "❌ *Вы были удалены из списка учеников вашего куратора.*",
                parse_mode='Markdown'
            )

            await callback.answer("✅ Ученик удалён.")
        else:
            await callback.answer("❌ Этот ученик не принадлежит вашему списку.")
    except (IndexError, ValueError) as e:
        await callback.answer("❌ Произошла ошибка при обработке запроса.")
        print(f"Ошибка: {e}")

# Возвращение к списку всех учеников
@dp.callback_query(lambda c: c.data == 'back_to_students')
async def back_to_students_handler(callback: types.CallbackQuery):
    cursor.execute('SELECT user_id, first_name, last_name, grade FROM users WHERE curator_id = ?', (callback.from_user.id,))
    students = cursor.fetchall()
    if students:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f'{student[1]} {student[2]} ({student[3]})', callback_data=f'student_{student[0]}')]
                for student in students
            ]
        )
        await callback.message.edit_text("👩‍🎓 *Ваши ученики:*", reply_markup=keyboard, parse_mode='Markdown')
    else:
        await callback.message.edit_text("❌ *У вас нет учеников.*", parse_mode='Markdown')
    await callback.answer()

# Обработка заданий со стороны куратора (404 - 550)
@dp.callback_query(lambda c: c.data.startswith('task_assign_'))
async def task_assign_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Попытка получить ID ученика
        student_id = int(callback.data.split('_')[2])
        await state.update_data(student_id=student_id)
        await callback.message.answer("📝 Введите текст задания для ученика:")
        await state.set_state('task_text')
    except (IndexError, ValueError):
        await callback.answer("❌ Произошла ошибка. Некорректные данные ученика.")


@dp.message(StateFilter('task_text'))
async def task_text_handler(message: types.Message, state: FSMContext):
    await state.update_data(task_text=message.text)
    await message.answer("📅 Укажите срок выполнения задания (например 31.12):")
    await state.set_state('task_deadline')

# Установка дедлайна 
@dp.message(StateFilter('task_deadline'))
async def task_deadline_handler(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    student_id = user_data['student_id']
    task_text = user_data['task_text']
    deadline = message.text  # В формате ДД.ММ (например, 31.12)

    try:
        # Добавляем текущий год к введённой дате
        current_year = datetime.now().year
        deadline_date = datetime.strptime(f"{deadline}.{current_year}", "%d.%m.%Y")
        
        # Если дата уже в следующем году (например, сейчас декабрь, а указано 01.01)
        if deadline_date < datetime.now():
            deadline_date = deadline_date.replace(year=current_year + 1)
        
        deadline_str = deadline_date.strftime("%Y-%m-%d")  # Сохраняем в БД в формате ГГГГ-ММ-ДД

        # Сохраняем задание в базе данных
        cursor.execute('INSERT INTO tasks (student_id, teacher_id, task_text, deadline, status) VALUES (?, ?, ?, ?, ?)',
                       (student_id, message.from_user.id, task_text, deadline_str, 'active'))
        conn.commit()

        # Отправка задания ученику
        cursor.execute('SELECT first_name, last_name FROM users WHERE user_id = ?', (student_id,))
        student = cursor.fetchone()
        if student:
            await bot.send_message(
                student_id,
                f"📚 *Новое задание от вашего куратора!*\n\n"
                f"📝 *Задание:* {task_text}\n"
                f"📅 *Срок выполнения:* {deadline_date.strftime('%d.%m.%Y')}",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text='✅ Выполнил задание', callback_data='task_done')],
                        [InlineKeyboardButton(text='❗ Возникают трудности', callback_data='task_problem')]
                    ]
                )
            )
            await message.answer(
                f"✅ Задание успешно отправлено ученику *{student[0]} {student[1]}*.\n"
                f"📚 *Текст:* {task_text}\n📅 *Срок:* {deadline_date.strftime('%d.%m.%Y')}",
                parse_mode='Markdown'
            )

        # Планируем уведомления и проверку дедлайна
        asyncio.create_task(schedule_task_notifications(student_id, message.from_user.id, task_text, deadline_date))

        await state.clear()
    except ValueError:
        await message.answer("❌ Неправильный формат даты. Введите дату в формате *ДД.ММ* (например, 31.12).", parse_mode='Markdown')

async def schedule_task_notifications(student_id, teacher_id, task_text, deadline_date):
    now = datetime.now()
    mid_date = now + (deadline_date - now) / 2
    last_day = deadline_date - timedelta(days=1)

    # Напоминание посередине срока
    delay_mid = (mid_date - now).total_seconds()
    cursor.execute('SELECT status FROM tasks WHERE id = ?', (task_id,))
    task_status = cursor.fetchone()
    if task_status and task_status[0] != "done":
      if delay_mid > 0:
          await asyncio.sleep(delay_mid)
          await bot.send_message(
              student_id,
              f"🔔 *Напоминание!* До окончания срока выполнения задания осталось половина времени.\n\n"
              f"📝 *Задание:* {task_text}\n"
              f"📅 *Дедлайн:* {deadline_date.strftime('%d.%m.%Y')}",
              parse_mode='Markdown'
          )

    # Напоминание за день до дедлайна
    cursor.execute('SELECT status FROM tasks WHERE id = ?', (task_id,))
    task_status = cursor.fetchone()
    if task_status and task_status[0] != "done":
      delay_last = (last_day - datetime.now()).total_seconds()
      if delay_last > 0:
          await asyncio.sleep(delay_last)
          await bot.send_message(
              student_id,
              f"⚠️ *Напоминание!* Завтра истекает срок выполнения задания.\n\n"
              f"📝 *Задание:* {task_text}\n"
              f"📅 *Дедлайн:* {deadline_date.strftime('%d.%m.%Y')}",
              parse_mode='Markdown'
          )

    # Проверка дедлайна
    delay_deadline = (deadline_date - datetime.now()).total_seconds()
    if delay_deadline > 0:
        await asyncio.sleep(delay_deadline)
    
    # Проверка статуса задания
    cursor.execute('SELECT status FROM tasks WHERE id = ?', (task_id,))
    task_status = cursor.fetchone()
    
    if task_status and task_status[0] != 'done':
        # Обновляем статус задания
        cursor.execute('UPDATE tasks SET status = ? WHERE id = ?', ('missed', task_id))
        conn.commit()

        # Уведомление ученику
        await bot.send_message(
            student_id,
            f"❌ *Вы не успели выполнить задание в срок.*\n\n"
            f"📝 *Задание:* {task_text}\n"
            f"📅 *Дедлайн был:* {deadline_date.strftime('%d.%m.%Y')}",
            parse_mode='Markdown'
        )

        cursor.execute('SELECT first_name, last_name, username FROM users WHERE user_id = ?', (student_id,))
        student = cursor.fetchone()
        student_username = f"@{student[2]}" if student[2] else "не указан"

        # Уведомление учителю
        await bot.send_message(
            teacher_id,
            f"❌ *Ученик не выполнил задание в срок!*\n\n"
            f"👤 *Ученик:* {student[0]} {student[1]} ({student_username})\n"
            f"📝 *Задание:* {task_text}\n"
            f"📅 *Дедлайн был:* {deadline_date.strftime('%d.%m.%Y')}",
            parse_mode='Markdown'
        )

# Обработка заданий со стороны ученика (553 - 689)
@dp.callback_query(lambda c: c.data == 'task_done')
async def task_done_handler(callback: types.CallbackQuery):
    student_id = callback.from_user.id

    # Получаем активное задание с учетом teacher_id
    cursor.execute('SELECT id, task_text FROM tasks WHERE student_id = ? AND status = ?', 
                  (student_id, 'active'))
    task = cursor.fetchone()
    
    if task:
        task_id, task_text = task
        
        # Обновляем статус задания
        cursor.execute('UPDATE tasks SET status = ? WHERE id = ?', ('done', task_id))
        conn.commit()
        
        # Оповещение учителя
        cursor.execute('SELECT curator_id FROM users WHERE user_id = ?', (student_id,))
        curator = cursor.fetchone()
        if curator:
            cursor.execute('SELECT first_name, last_name, username FROM users WHERE user_id = ?', (student_id,))
            student = cursor.fetchone()
            student_username = f"@{student[2]}" if student[2] else "не указан"
            
            await bot.send_message(
                curator[0],
                f"✅ *Ученик выполнил задание!*\n"
                f"📝 *Задание:* {task_text}\n"
                f"👤 *Ученик:* {student[0]} {student[1]} ({student_username})",
                parse_mode='Markdown'
            )
        
        await callback.message.edit_reply_markup()  # Удаляем кнопки
        await callback.message.answer("✅ Вы отметили задание как выполненное.")
    else:
        await callback.message.answer("❌ У вас нет активных заданий.")

# Возникновение трудностей у ученика
@dp.callback_query(lambda c: c.data == 'task_problem')
async def task_problem_handler(callback: types.CallbackQuery):
    student_id = callback.from_user.id

    # Проверяем активное задание
    cursor.execute('SELECT id, task_text FROM tasks WHERE student_id = ? AND status = ?', (student_id, 'active'))
    task = cursor.fetchone()
    
    if task:
        task_id, task_text = task
      
        # Обновляем статус задания
        cursor.execute('UPDATE tasks SET status = ? WHERE id = ?', ('problem', task_id))
        conn.commit()

        cursor.execute('SELECT first_name, last_name, username FROM users WHERE user_id = ?', (student_id,))
        student = cursor.fetchone()
        student_username = student[2]
        
        # Оповещение учителя
        cursor.execute('SELECT curator_id FROM users WHERE user_id = ?', (student_id,))
        curator = cursor.fetchone()
        if curator:
            await bot.send_message(
                curator[0],
                f"❗ *Ученик сообщил о трудностях при выполнении задания.*\n"
                f"📝 *Задание:* {task_text}\n"
                f"👤 *Ученик:* {student[0]} {student[1]} (@{student_username})",
                parse_mode='Markdown'
            )
        cursor.execute('SELECT u.username FROM users u WHERE u.user_id = ?', (curator[0],))
        teacher_username = cursor.fetchone()[0] or "не указан"
        
        # Сообщение ученику
        await callback.message.edit_reply_markup()
        await callback.message.answer(
            f"✉️ Свяжитесь с вашим куратором: @{teacher_username}\n"
            "Опишите ему все возникшие трудности.")
    else:
        await callback.message.answer("❌ У вас нет активных заданий.")

@dp.callback_query(lambda c: c.data == 'task_upload')
async def task_upload_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📸 Отправьте фото или видео выполненного задания.")
    await state.set_state("waiting_for_task_media")

@dp.message(StateFilter("waiting_for_task_media"))
async def task_media_handler(message: Message, state: FSMContext):
    if not (message.photo or message.video):
        await message.answer("❌ Отправьте фото или видео!")
        return

    student_id = message.from_user.id
    media_id = message.photo[-1].file_id if message.photo else message.video.file_id
    media_type = "photo" if message.photo else "video"

    cursor.execute('SELECT task_text FROM tasks WHERE student_id = ? AND status = ?', (student_id, 'active'))
    task = cursor.fetchone()

    cursor.execute('SELECT first_name, last_name, grade FROM users WHERE user_id = ?', (student_id,))
    student = cursor.fetchone()
    
    if task and student:
        task_text = task[0]
        first_name, last_name, grade = student

        # Добавляем столбцы, если их нет
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        if "media_id" not in columns:
            cursor.execute('ALTER TABLE tasks ADD COLUMN media_id TEXT')
        if "media_type" not in columns:
            cursor.execute('ALTER TABLE tasks ADD COLUMN media_type TEXT')

        cursor.execute('UPDATE tasks SET status = ?, media_id = ?, media_type = ? WHERE student_id = ?',
                       ('done', media_id, media_type, student_id))
        conn.commit()
        
        # Оповещение учителя
        cursor.execute('SELECT curator_id FROM users WHERE user_id = ?', (student_id,))
        curator = cursor.fetchone()
        if curator:
            teacher_id = curator[0]
            caption = (
                f"✅ *Ученик выполнил задание!*\n\n"
                f"👤 *Имя:* {first_name} {last_name}\n"
                f"🏫 *Класс:* {grade}\n"
                f"📝 *Задание:* {task_text}"
            )
            if media_type == "photo":
                await bot.send_photo(teacher_id, media_id, caption=caption, parse_mode='Markdown')
            else:
                await bot.send_video(teacher_id, media_id, caption=caption, parse_mode='Markdown')
        
        await message.answer("✅ Задание отправлено учителю.")
        await state.clear()
    else:
        await message.answer("❌ У вас нет активных заданий.")


# Команда /delete для удаления аккаунта
@dp.message(Command('delete'))
async def delete_account_command(message: Message, state: FSMContext):
    code = randint(1000, 9999)
    await state.update_data(confirm_code=code)
    await message.answer(
        f"⚠️ Для удаления аккаунта введите код: `{code}`\n"
        "Это действие нельзя отменить! Все ваши данные будут удалены.",
        parse_mode='Markdown'
    )
    await state.set_state(DeleteAccount.confirm_code)

@dp.message(StateFilter(DeleteAccount.confirm_code))
async def confirm_delete_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        if int(message.text) == data['confirm_code']:
            user_id = message.from_user.id
            
            # Удаляем все связанные данные
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM curator_requests WHERE student_id = ? OR teacher_id = ?', (user_id, user_id))
            cursor.execute('DELETE FROM tasks WHERE student_id = ? OR teacher_id = ?', (user_id, user_id))
            conn.commit()
            
            await message.answer("✅ Аккаунт и все данные успешно удалены!", reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer("❌ Неверный код. Удаление отменено.")
    except ValueError:
        await message.answer("❌ Введите число!")
    await state.clear()



if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))
