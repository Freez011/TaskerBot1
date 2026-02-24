import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
from datetime import datetime
import storage as st

logger = logging.getLogger(__name__)

async def check_reminders(bot: Bot):
    tasks = await st.get_pending_tasks()
    for task_id, user_id, text, remind_time_str in tasks:
        try:
            remind_time = datetime.fromisoformat(remind_time_str)
            await bot.send_message(
                user_id,
                f"⏰ <b>Напоминание!</b>\n\n"
                f"{text}\n"
                f"Установлено на: {remind_time.strftime('%d.%m.%Y %H:%M')}",
                parse_mode='HTML'
            )
            await st.mark_notified(task_id)
            logger.info(f"Уведомление отправлено пользователю {user_id} (задача {task_id})")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления для задачи {task_id}: {e}")
            await st.mark_notified(task_id)

def setup_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")  # При необходимости смените часовой пояс
    scheduler.add_job(
        check_reminders,
        trigger=IntervalTrigger(seconds=30),
        args=[bot],
        id='check_reminders',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Планировщик запущен (интервал 30 сек)")
    return scheduler