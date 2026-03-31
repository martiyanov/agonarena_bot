#!/usr/bin/env python3
"""
Скрипт миграции для исправления невалидных статусов дуэлей.

Исправляет:
1. 'judging' -> 'round_2_transition' (после завершения 2-го раунда)
2. 'in_progress' -> 'round_1_active' (устаревший статус)

Запуск:
    python scripts/migrate_statuses.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.db import session as db_session


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def migrate_duel_statuses() -> dict[str, int]:
    """
    Мигрирует невалидные статусы дуэлей в правильные.
    
    Returns:
        Словарь с количеством исправленных записей по типам
    """
    stats = {
        "judging_to_round_2_transition": 0,
        "in_progress_to_round_1_active": 0,
        "total_updated": 0,
    }
    
    async with db_session.AsyncSessionLocal() as session:
        # Мигрируем 'judging' -> 'round_2_transition'
        # Этот статус использовался после завершения 2-го раунда
        result = await session.execute(
            text("""
                UPDATE duels 
                SET status = 'round_2_transition' 
                WHERE status = 'judging'
                RETURNING id
            """)
        )
        judging_ids = result.scalars().all()
        stats["judging_to_round_2_transition"] = len(judging_ids)
        if judging_ids:
            logger.info(f"Migrated {len(judging_ids)} duels from 'judging' to 'round_2_transition': {list(judging_ids)}")
        
        # Мигрируем 'in_progress' -> 'round_1_active'
        # Этот статус был устаревшим и не должен использоваться
        result = await session.execute(
            text("""
                UPDATE duels 
                SET status = 'round_1_active' 
                WHERE status = 'in_progress'
                RETURNING id
            """)
        )
        in_progress_ids = result.scalars().all()
        stats["in_progress_to_round_1_active"] = len(in_progress_ids)
        if in_progress_ids:
            logger.info(f"Migrated {len(in_progress_ids)} duels from 'in_progress' to 'round_1_active': {list(in_progress_ids)}")
        
        await session.commit()
        stats["total_updated"] = stats["judging_to_round_2_transition"] + stats["in_progress_to_round_1_active"]
        
    return stats


async def verify_migration() -> list[dict]:
    """
    Проверяет, что невалидных статусов больше нет в БД.
    
    Returns:
        Список дуэлей с невалидными статусами (должен быть пустым)
    """
    async with db_session.AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, status, user_telegram_id, created_at 
                FROM duels 
                WHERE status IN ('judging', 'in_progress')
                ORDER BY id
            """)
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]


async def show_current_statuses() -> dict[str, int]:
    """
    Показывает распределение статусов дуэлей в БД.
    
    Returns:
        Словарь {статус: количество}
    """
    async with db_session.AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT status, COUNT(*) as count 
                FROM duels 
                GROUP BY status 
                ORDER BY count DESC
            """)
        )
        rows = result.mappings().all()
        return {row["status"]: row["count"] for row in rows}


async def main() -> int:
    """
    Основная функция миграции.
    
    Returns:
        Код выхода (0 - успех, 1 - ошибка)
    """
    logger.info("=" * 60)
    logger.info("Starting duel status migration")
    logger.info("=" * 60)
    
    # Показываем текущее состояние
    logger.info("\nCurrent status distribution:")
    statuses_before = await show_current_statuses()
    for status, count in statuses_before.items():
        marker = " ⚠️ INVALID" if status in ("judging", "in_progress") else ""
        logger.info(f"  {status}: {count}{marker}")
    
    # Проверяем наличие невалидных статусов
    invalid_duels = await verify_migration()
    if not invalid_duels:
        logger.info("\n✅ No invalid statuses found. Migration not needed.")
        return 0
    
    logger.info(f"\n⚠️ Found {len(invalid_duels)} duels with invalid statuses")
    for duel in invalid_duels:
        logger.info(f"  Duel #{duel['id']}: status='{duel['status']}', user={duel['user_telegram_id']}, created={duel['created_at']}")
    
    # Выполняем миграцию
    logger.info("\n" + "=" * 60)
    logger.info("Running migration...")
    logger.info("=" * 60)
    
    try:
        stats = await migrate_duel_statuses()
        
        logger.info("\nMigration results:")
        logger.info(f"  'judging' -> 'round_2_transition': {stats['judging_to_round_2_transition']}")
        logger.info(f"  'in_progress' -> 'round_1_active': {stats['in_progress_to_round_1_active']}")
        logger.info(f"  Total updated: {stats['total_updated']}")
        
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        return 1
    
    # Проверяем результат
    logger.info("\n" + "=" * 60)
    logger.info("Verifying migration...")
    logger.info("=" * 60)
    
    invalid_duels_after = await verify_migration()
    if invalid_duels_after:
        logger.error(f"\n❌ Migration incomplete! Still found {len(invalid_duels_after)} duels with invalid statuses:")
        for duel in invalid_duels_after:
            logger.error(f"  Duel #{duel['id']}: status='{duel['status']}'")
        return 1
    
    logger.info("\n✅ Migration completed successfully!")
    
    # Показываем итоговое распределение
    logger.info("\nFinal status distribution:")
    statuses_after = await show_current_statuses()
    for status, count in statuses_after.items():
        logger.info(f"  {status}: {count}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Migration finished")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
