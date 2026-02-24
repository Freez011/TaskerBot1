import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any

STORAGE_FILE = 'tasks.json'
lock = asyncio.Lock()

def _load_tasks() -> Dict[str, Any]:
    if not os.path.exists(STORAGE_FILE):
        return {"tasks": [], "counter": 1}
    with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

async def _save_tasks(data: Dict[str, Any]):
    async with lock:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_save, data)

def _sync_save(data: Dict[str, Any]):
    with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_storage():
    if not os.path.exists(STORAGE_FILE):
        _sync_save({"tasks": [], "counter": 1})

async def add_task(user_id: int, text: str, remind_time: datetime) -> int:
    data = _load_tasks()
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
    await _save_tasks(data)
    return task_id

async def get_pending_tasks(limit: int = 100) -> List[tuple]:
    data = _load_tasks()
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
    data = _load_tasks()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["notified"] = True
            break
    await _save_tasks(data)

async def get_user_tasks(user_id: int, only_active: bool = True) -> List[tuple]:
    data = _load_tasks()
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
    result.sort(key=lambda x: x[2])
    return result

async def delete_task(task_id: int, user_id: int) -> bool:
    data = _load_tasks()
    initial_len = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if not (t["id"] == task_id and t["user_id"] == user_id)]
    if len(data["tasks"]) < initial_len:
        await _save_tasks(data)
        return True
    return False