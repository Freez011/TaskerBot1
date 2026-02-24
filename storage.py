import json
import os
import requests
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Переменные окружения
GIST_ID = os.getenv("GIST_ID")
GIST_TOKEN = os.getenv("GIST_TOKEN")
GIST_FILENAME = 'tasks.json'

def _save_to_gist(data: Dict[str, Any]):
    """Сохраняет данные в Gist."""
    url = f'https://api.github.com/gists/{GIST_ID}'
    headers = {'Authorization': f'token {GIST_TOKEN}'}
    payload = {
        "files": {
            GIST_FILENAME: {
                "content": json.dumps(data, ensure_ascii=False, indent=2)
            }
        }
    }
    try:
        response = requests.patch(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"✅ Данные сохранены в Gist. Всего задач: {len(data['tasks'])}")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка при сохранении в Gist: {e}")
        raise

def _load_from_gist() -> Dict[str, Any]:
    """Загружает данные из Gist и приводит к нужной структуре."""
    if not GIST_ID or not GIST_TOKEN:
        raise ValueError("GIST_ID и GIST_TOKEN должны быть заданы в переменных окружения")
    
    url = f'https://api.github.com/gists/{GIST_ID}'
    headers = {'Authorization': f'token {GIST_TOKEN}'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при загрузке из Gist: {e}")
        raise
    
    files = response.json().get('files', {})
    
    if GIST_FILENAME not in files:
        logger.info("Файл tasks.json не найден в Gist, создаём новый")
        new_data = {"tasks": [], "counter": 1}
        _save_to_gist(new_data)
        return new_data
    
    content = files[GIST_FILENAME].get('content')
    if not content:
        logger.info("Файл tasks.json пуст, создаём новый")
        new_data = {"tasks": [], "counter": 1}
        _save_to_gist(new_data)
        return new_data
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}, создаём новую структуру")
        new_data = {"tasks": [], "counter": 1}
        _save_to_gist(new_data)
        return new_data
    
    if not isinstance(data, dict) or "tasks" not in data or "counter" not in data:
        logger.warning("⚠️ Неверная структура данных в Gist, создаём новую и сохраняем")
        new_data = {"tasks": [], "counter": 1}
        _save_to_gist(new_data)
        return new_data
    
    return data

def init_storage():
    """Инициализация хранилища (проверяет доступность Gist)."""
    try:
        _load_from_gist()
        logger.info("✅ Подключение к Gist успешно")
    except Exception as e:
        logger.exception("❌ Ошибка подключения к Gist")
        raise

async def add_task(user_id: int, text: str, remind_time: datetime) -> int:
    data = _load_from_gist()
    task_id = data["counter"]
    data["counter"] += 1
    task = {
        "id": task_id,
        "user_id": user_id,
        "text": text,
        "remind_time": remind_time.isoformat(),
        "notified": False,
        "created_at": datetime.now().isoformat()
    }
    data["tasks"].append(task)
    _save_to_gist(data)
    logger.info(f"➕ Задача {task_id} добавлена для пользователя {user_id}")
    return task_id

async def get_pending_tasks(limit: int = 100) -> List[Tuple[int, int, str, str]]:
    data = _load_from_gist()
    now = datetime.utcnow().isoformat()
    pending = []
    for task in data["tasks"]:
        if not task["notified"] and task["remind_time"] <= now:
            pending.append((
                task["id"],
                task["user_id"],
                task["text"],
                task["remind_time"]
            ))
        if len(pending) >= limit:
            break
    logger.info(f"🔍 Найдено {len(pending)} задач для отправки")
    return pending

async def mark_notified(task_id: int):
    data = _load_from_gist()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["notified"] = True
            break
    _save_to_gist(data)
    logger.info(f"✅ Задача {task_id} отмечена как уведомлённая")

async def get_user_tasks(user_id: int, only_active: bool = True) -> List[tuple]:
    data = _load_from_gist()
    result = []
    for task in data["tasks"]:
        if task["user_id"] != user_id:
            continue
        if only_active and task["notified"]:
            continue
        result.append((task["id"], task["text"], task["remind_time"]))
    # Сортировка по времени (ближайшие сверху)
    result.sort(key=lambda x: x[2])
    return result

async def delete_task(task_id: int, user_id: int) -> bool:
    data = _load_from_gist()
    initial_len = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if not (t["id"] == task_id and t["user_id"] == user_id)]
    if len(data["tasks"]) < initial_len:
        _save_to_gist(data)
        logger.info(f"🗑️ Задача {task_id} удалена пользователем {user_id}")
        return True
    return False
