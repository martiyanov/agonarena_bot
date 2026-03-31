#!/usr/bin/env python3
"""
Task Monitor — отслеживает активные задачи и предупреждает о зависших.

Запускается по cron каждые 10 минут.
- Если задача в статусе >30 мин → warning PM
- Если >60 мин → эскалация пользователю
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/home/openclaw/.openclaw/workspace/agonarena_bot")
TRACKER_FILE = WORKSPACE / "state/task-tracker.json"
LOG_FILE = WORKSPACE / "state/task-monitor.log"

def log(message: str):
    """Логирование с timestamp."""
    timestamp = datetime.now().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def load_tracker():
    """Загрузить трекер задач."""
    if not TRACKER_FILE.exists():
        return {"activeTasks": [], "completedTasks": [], "config": {}}
    with open(TRACKER_FILE) as f:
        return json.load(f)

def save_tracker(data):
    """Сохранить трекер задач."""
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def check_stuck_tasks():
    """Проверить задачи на зависание."""
    tracker = load_tracker()
    now = datetime.utcnow()
    config = tracker.get("config", {
        "checkIntervalMinutes": 10,
        "warnAfterMinutes": 30,
        "escalateAfterMinutes": 60
    })
    
    warnings = []
    escalations = []
    
    # Проверка активных задач
    for task in tracker.get("activeTasks", []):
        waiting_since = datetime.fromisoformat(task.get("waitingSince", now.isoformat()))
        waiting_minutes = (now - waiting_since).total_seconds() / 60
        
        task_id = task.get("id", "UNKNOWN")
        waiting_for = task.get("waitingFor", "unknown")
        reason = task.get("waitingReason", "Неизвестно")
        
        if waiting_minutes >= config["escalateAfterMinutes"]:
            escalations.append({
                "task": task,
                "minutes": int(waiting_minutes),
                "reason": reason
            })
        elif waiting_minutes >= config["warnAfterMinutes"]:
            warnings.append({
                "task": task,
                "minutes": int(waiting_minutes),
                "reason": reason
            })
    
    # Проверка завершённых задач (ждут ручного тестирования)
    for task in tracker.get("completedTasks", []):
        if task.get("status") == "ready_for_manual_test":
            waiting_since = datetime.fromisoformat(task.get("waitingSince", now.isoformat()))
            waiting_minutes = (now - waiting_since).total_seconds() / 60
            
            task_id = task.get("id", "UNKNOWN")
            
            if waiting_minutes >= config["escalateAfterMinutes"]:
                escalations.append({
                    "task": task,
                    "minutes": int(waiting_minutes),
                    "reason": task.get("waitingReason", "Ручное тестирование")
                })
            elif waiting_minutes >= config["warnAfterMinutes"]:
                warnings.append({
                    "task": task,
                    "minutes": int(waiting_minutes),
                    "reason": task.get("waitingReason", "Ручное тестирование")
                })
    
    return warnings, escalations

def send_notification(message: str, level: str = "info"):
    """Отправить уведомление (заглушка для интеграции)."""
    log(f"[{level.upper()}] {message}")
    # В будущем: отправка в Telegram/Slack через message tool

def main():
    """Основная логика мониторинга."""
    log("=== Task Monitor Check ===")
    
    warnings, escalations = check_stuck_tasks()
    
    if warnings:
        for w in warnings:
            msg = f"⚠️ Задача {w['task'].get('id')} ждёт {w['minutes']} мин: {w['reason']}"
            log(msg)
            send_notification(msg, "warning")
    
    if escalations:
        for e in escalations:
            msg = f"🚨 Задача {e['task'].get('id')} ждёт {e['minutes']} мин: {e['reason']}"
            log(msg)
            send_notification(msg, "escalation")
    
    if not warnings and not escalations:
        log("Все задачи в норме")
    
    log(f"Warnings: {len(warnings)}, Escalations: {len(escalations)}")

if __name__ == "__main__":
    main()
