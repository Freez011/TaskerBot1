import json
import os
import requests
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Переменные окружения (должны быть заданы на Render)
GIST_ID = os.getenv("GIST_ID")           # ID вашего Gist (например, "3b546069d2856e6051bbe3c1080f1b5d")
GIST_TOKEN = os.getenv("GIST_TOKEN")     # Токен GitHub с правами gist
GIST_FILENAME = 'tasks.json'             # Имя файла внутри Gist

def _load_from_gist() -> Dict[str, Any]:
    """Загружает данные из Gist."""
    if not GIST_ID or not GIST_TOKEN:
        raise ValueError("GIST_ID и GIST_TOKEN должны быть заданы в переменных окружения")
    
    url = f'https://api.github.com/gists/{GIST_ID}'
    headers = {'Authorization': f'token {GIST_TOKEN}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    files = response.json().get('files', {})
    if GIST_FILENAME not in files:
        # Если файла ещё нет, возвращаем пустую структуру
        return {"tasks": [], "counter": 1}
    
    content = files[GIST_FILENAME].get('content')
    if content:
        return json.loads(content)
    else:
        return {"tasks": [], "counter": 1}

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
    response = requests.patch(url, json=payload, headers=headers)
    response.raise_for_status()

def init_storage():
    """Инициализация хранилища (проверяет доступность Gist)."""
    try:
        _load_from_gist()
    except Exception as e:
        print(f"Ошибка подключения к Gist: {e}")
        raise

async def add_task(user_id: int, text: str, remind_time: datetime) -> int:
    """Добавляет новую задачу и возвращает её ID."""
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
    return task_id

async def get_pending_tasks(limit: int = 100) -> List[Tuple[int, int, str, str]]:
    """
    Возвращает список задач, у которых время наступило и notified=False.
    Каждый элемент кортеж: (id, user_id, text, remind_time_str)
    """
    data = _load_from_gist()
    now = datetime.now().isoformat()
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
    return pending

async def mark_notified(task_id: int):
    """Отмечает задачу как уведомлённую."""
    data = _load_from_gist()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["notified"] = True
            break
    _save_to_gist(data)

async def get_user_tasks(user_id: int, only_active: bool = True) -> List[tuple]:
    """
    Возвращает задачи пользователя.
    Если only_active=True, только не уведомлённые.
    Возвращает список кортежей (id, text, remind_time_str[, notified])
    """
    data = _load_from_gist()
    result = []
    for task in data["tasks"]:
        if task["user_id"] != user_id:
            continue
        if only_active and task["notified"]:
            continue
        dt = datetime.fromisoformat(task["remind_time"])
        if only_active:
            result.append((task["id"], task["text"], dt.isoformat()))
        else:
            result.append((task["id"], task["text"], dt.isoformat(), task["notified"]))
    # Сортировка по времени (ближайшие сверху)
    result.sort(key=lambda x: x[2])
    return result

async def delete_task(task_id: int, user_id: int) -> bool:
    """Удаляет задачу, если она принадлежит пользователю."""
    data = _load_from_gist()
    initial_len = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if not (t["id"] == task_id and t["user_id"] == user_id)]
    if len(data["tasks"]) < initial_len:
        _save_to_gist(data)
        return True
    return False



