import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
import storage as st
from handlers import register_handlers
from scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- HTTP-сервер для Render ---
async def handle_health(request):
    """Обработчик для проверки здоровья (health check)"""
    return web.Response(text="Bot is running")

async def run_http_server():
    """Запускает aiohttp сервер на порту из переменной окружения PORT"""
    app = web.Application()
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)

    port = int(os.environ.get('PORT', 10000))  # Render передаёт PORT
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"HTTP server started on port {port}")

    # Оставляем сервер работать бесконечно
    await asyncio.Event().wait()

# --- Команды бота ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="add", description="Добавить задачу"),
        BotCommand(command="tasks", description="Мои задачи"),
        BotCommand(command="delete", description="Удалить задачу"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="cancel", description="Отменить действие"),
    ]
    await bot.set_my_commands(commands)

# --- Главная функция ---
async def main():
    # Инициализация хранилища
    st.init_storage()
    logger.info("Хранилище инициализировано")

    # Создаём бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    # Регистрируем обработчики команд
    register_handlers(dp)
    await set_commands(bot)

    # Запускаем планировщик напоминаний
    scheduler = setup_scheduler(bot)

    # Запускаем HTTP-сервер как фоновую задачу
    asyncio.create_task(run_http_server())

    # Запускаем поллинг бота
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()
        scheduler.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
