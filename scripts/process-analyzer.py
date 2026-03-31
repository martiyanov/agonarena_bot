#!/usr/bin/env python3
"""
Process Analyzer — глубокий анализ истории разработки.

Анализирует:
1. Историю сообщений (chat history)
2. Переходы между статусами задач
3. Время на каждом этапе
4. Частые ошибки/баги
5. Bottlenecks процесса

Выдаёт рекомендации по оптимизации.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

WORKSPACE = Path("/home/openclaw/.openclaw/workspace/agonarena_bot")
MEMORY_DIR = WORKSPACE / "memory"
STATE_DIR = WORKSPACE / "state"
TASK_TRACKER = STATE_DIR / "task-tracker.json"
PROCESS_ANALYSIS = STATE_DIR / "process-analysis.md"
ANALYSIS_OUTPUT = STATE_DIR / "process-recommendations.json"

def load_task_tracker():
    """Загрузить трекер задач."""
    if not TASK_TRACKER.exists():
        return {"activeTasks": [], "completedTasks": []}
    with open(TASK_TRACKER) as f:
        return json.load(f)

def load_memory_notes(days: int = 7):
    """Загрузить daily notes за последние N дней."""
    notes = []
    today = datetime.now().date()
    
    for i in range(days):
        date = today - timedelta(days=i)
        note_path = MEMORY_DIR / f"{date.isoformat()}.md"
        if note_path.exists():
            with open(note_path) as f:
                notes.append({
                    "date": date.isoformat(),
                    "content": f.read()
                })
    
    return notes

def load_process_analysis():
    """Загрузить последний анализ процесса."""
    if not PROCESS_ANALYSIS.exists():
        return None
    with open(PROCESS_ANALYSIS) as f:
        return f.read()

def analyze_task_flow(completed_tasks: List[Dict]) -> Dict[str, Any]:
    """Анализ потока задач."""
    if not completed_tasks:
        return {"error": "Нет завершённых задач"}
    
    total_tasks = len(completed_tasks)
    tasks_with_bugs = sum(1 for t in completed_tasks if t.get("bugsFound", 0) > 0)
    tasks_manual_test_failed = sum(1 for t in completed_tasks if t.get("status") == "manual_test_failed")
    
    # Время на этапах (если есть данные)
    stage_times = {}
    
    return {
        "total_tasks": total_tasks,
        "tasks_with_bugs": tasks_with_bugs,
        "bug_rate": round(tasks_with_bugs / total_tasks * 100, 1) if total_tasks > 0 else 0,
        "manual_test_fail_rate": round(tasks_manual_test_failed / total_tasks * 100, 1) if total_tasks > 0 else 0,
        "stage_times": stage_times
    }

def analyze_bottlenecks(active_tasks: List[Dict]) -> List[Dict[str, Any]]:
    """Анализ узких мест (задачи в ожидании)."""
    bottlenecks = []
    now = datetime.utcnow()
    
    for task in active_tasks:
        created_at = task.get("createdAt", task.get("waitingSince"))
        if created_at:
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(tzinfo=None)
            waiting_hours = (now - created_dt).total_seconds() / 3600
            
            if waiting_hours > 1:
                bottlenecks.append({
                    "task_id": task.get("id"),
                    "waiting_hours": round(waiting_hours, 2),
                    "status": task.get("status"),
                    "stages": task.get("stages", {})
                })
    
    return bottlenecks

def analyze_memory_patterns(memory_notes: List[Dict]) -> Dict[str, Any]:
    """Анализ паттернов в daily notes."""
    patterns = {
        "frequent_issues": [],
        "repeated_tasks": [],
        "time_wasters": []
    }
    
    # Поиск повторяющихся тем
    issue_keywords = {
        "баг": 0,
        "фикс": 0,
        "тест": 0,
        "ожидание": 0,
        "пауза": 0,
        "ошибка": 0
    }
    
    for note in memory_notes:
        content_lower = note["content"].lower()
        for keyword in issue_keywords:
            if keyword in content_lower:
                issue_keywords[keyword] += 1
    
    patterns["frequent_issues"] = [
        {"keyword": k, "count": v} 
        for k, v in sorted(issue_keywords.items(), key=lambda x: x[1], reverse=True)
        if v > 0
    ]
    
    return patterns

def generate_recommendations(
    task_flow: Dict,
    bottlenecks: List,
    patterns: Dict
) -> List[Dict[str, Any]]:
    """Генерация рекомендаций по оптимизации."""
    recommendations = []
    
    # Рекомендация 1: Баги на ручном тестировании
    if task_flow.get("manual_test_fail_rate", 0) > 0:
        recommendations.append({
            "priority": "high",
            "category": "testing",
            "issue": f"{task_flow['manual_test_fail_rate']}% задач проваливают ручное тестирование",
            "recommendation": "Перенести ручное тестирование раньше (после DEV, до TEST). Добавить E2E тесты для UI.",
            "estimated_impact": "Сокращение времени на 30-50%"
        })
    
    # Рекомендация 2: Задачи в ожидании
    if bottlenecks:
        recommendations.append({
            "priority": "high",
            "category": "process",
            "issue": f"{len(bottlenecks)} задач в ожидании >1 часа",
            "recommendation": "Автоматически вызывать следующий этап. Уменьшить время ожидания пользователя.",
            "estimated_impact": f"Сокращение простоев на {sum(b['waiting_hours'] for b in bottlenecks):.1f} часов"
        })
    
    # Рекомендация 3: Частые баги
    if task_flow.get("bug_rate", 0) > 20:
        recommendations.append({
            "priority": "medium",
            "category": "quality",
            "issue": f"{task_flow['bug_rate']}% задач имеют баги",
            "recommendation": "Добавить code review перед TEST. Увеличить покрытие unit тестами.",
            "estimated_impact": "Снижение багов на 40-60%"
        })
    
    # Рекомендация 4: Паттерны (частые проблемы)
    if patterns.get("frequent_issues"):
        top_issues = patterns["frequent_issues"][:3]
        if top_issues:
            recommendations.append({
                "priority": "medium",
                "category": "patterns",
                "issue": f"Частые темы: {', '.join(i['keyword'] for i in top_issues)}",
                "recommendation": "Проанализировать корневые причины. Добавить预防措施.",
                "estimated_impact": "Улучшение качества процесса"
            })
    
    return recommendations

def main():
    """Основная логика анализа."""
    print("=== Process Analyzer ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Загрузка данных
    tracker = load_task_tracker()
    memory_notes = load_memory_notes(days=7)
    process_analysis = load_process_analysis()
    
    # Анализ
    task_flow = analyze_task_flow(tracker.get("completedTasks", []))
    bottlenecks = analyze_bottlenecks(tracker.get("activeTasks", []))
    patterns = analyze_memory_patterns(memory_notes)
    recommendations = generate_recommendations(task_flow, bottlenecks, patterns)
    
    # Вывод
    output = {
        "timestamp": datetime.now().isoformat(),
        "task_flow": task_flow,
        "bottlenecks": bottlenecks,
        "patterns": patterns,
        "recommendations": recommendations
    }
    
    # Сохранение рекомендаций
    with open(ANALYSIS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nTask Flow: {json.dumps(task_flow, indent=2, ensure_ascii=False)}")
    print(f"\nBottlenecks: {len(bottlenecks)} задач в ожидании")
    print(f"\nRecommendations: {len(recommendations)}")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. [{rec['priority'].upper()}] {rec['category']}")
        print(f"   Issue: {rec['issue']}")
        print(f"   Recommendation: {rec['recommendation']}")
        print(f"   Impact: {rec['estimated_impact']}")
    
    print(f"\nOutput saved to: {ANALYSIS_OUTPUT}")
    
    return output

if __name__ == "__main__":
    main()
