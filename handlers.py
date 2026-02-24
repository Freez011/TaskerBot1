import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime
import storage as st

class TaskStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_time = State()

def get_cancel_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("❌ Отмена"))
    return keyboard

async def cmd_start(message: types.Message):
    text = (
        "👋 Привет! Я бот-напоминалка.\n\n"
        "Команды:\n"
        "/add – добавить новую задачу\n"
        "/tasks – показать мои активные задачи\n"
        "/delete – удалить задачу\n"
        "/help – помощь\n"
        "/cancel – отменить текущее действие"
    )
    await message.answer(text)

async def cmd_help(message: types.Message):
    text = (
        "📌 <b>Как пользоваться:</b>\n\n"
        "1. Отправь /add\n"
        "2. Введи текст задачи\n"
        "3. Введи дату и время в формате: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
        "   Например: <code>25.12.2024 15:30</code>\n\n"
        "Я напомню тебе в указанное время."
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

async def cmd_add(message: types.Message):
    await TaskStates.waiting_for_text.set()
    await message.answer("Введите текст задачи:", reply_markup=get_cancel_keyboard())

async def process_text(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if len(text) > 500:
        await message.answer("Текст слишком длинный (макс. 500 символов). Попробуйте снова.")
        return
    await state.update_data(text=text)
    await TaskStates.next()
    await message.answer(
        "Введите дату и время в формате:\n"
        "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
        "Пример: <code>25.12.2024 15:30</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )

async def process_time(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    try:
        remind_time = datetime.strptime(time_str, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("❌ Неправильный формат. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")
        return

    now = datetime.now()
    if remind_time < now:
        await message.answer("⚠️ Указанное время уже прошло. Напоминание может не сработать, но задача будет сохранена.")

    data = await state.get_data()
    text = data['text']
    user_id = message.from_user.id

    task_id = await st.add_task(user_id, text, remind_time)
    await state.finish()
    await message.answer(
        f"✅ Задача добавлена!\n\n"
        f"ID: {task_id}\n"
        f"Текст: {text}\n"
        f"Напомню: {remind_time.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=ReplyKeyboardRemove()
    )

async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.", reply_markup=ReplyKeyboardRemove())
        return
    await state.finish()
    await message.answer("❌ Отменено.", reply_markup=ReplyKeyboardRemove())

async def cmd_tasks(message: types.Message):
    user_id = message.from_user.id
    tasks = await st.get_user_tasks(user_id, only_active=True)
    if not tasks:
        await message.answer("У вас нет активных задач.")
        return

    text = "📋 <b>Ваши активные задачи:</b>\n\n"
    for task_id, task_text, remind_time_str in tasks:
        remind_dt = datetime.fromisoformat(remind_time_str)
        text += f"🔹 <b>ID {task_id}</b>: {task_text}\n"
        text += f"   ⏰ {remind_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

async def cmd_delete(message: types.Message):
    args = message.get_args()
    if not args:
        await message.answer("Использование: /delete <ID задачи>")
        return
    try:
        task_id = int(args)
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    user_id = message.from_user.id
    success = await st.delete_task(task_id, user_id)
    if success:
        await message.answer(f"✅ Задача ID {task_id} удалена.")
    else:
        await message.answer(f"❌ Задача ID {task_id} не найдена или не принадлежит вам.")

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_help, commands=['help'])
    dp.register_message_handler(cmd_add, commands=['add'])
    dp.register_message_handler(cmd_tasks, commands=['tasks'])
    dp.register_message_handler(cmd_delete, commands=['delete'])
    dp.register_message_handler(cmd_cancel, state='*', text='❌ Отмена')
    dp.register_message_handler(cmd_cancel, commands=['cancel'], state='*')
    dp.register_message_handler(process_text, state=TaskStates.waiting_for_text)
    dp.register_message_handler(process_time, state=TaskStates.waiting_for_time)