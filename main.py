import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
import storage as st
from handlers import register_handlers
from scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def main():
    st.init_storage()
    logger.info("Хранилище инициализировано")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    register_handlers(dp)
    await set_commands(bot)

    scheduler = setup_scheduler(bot)

    try:
        await dp.start_polling()
    finally:
        await bot.session.close()
        scheduler.shutdown()

if __name__ == '__main__':
    asyncio.run(main())