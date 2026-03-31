#!/usr/bin/env python3
"""
Скрипт для исправления оставшихся ошибок в БД после миграции.

Проблемы:
1. Duel 10, 11 — round_1_active но round 1 finished (неконсистентность)
2. Пользователи с множественными активными дуэлями

Решение:
1. Исправить дуэли 10, 11 — установить правильный статус
2. Для пользователей с множественными дуэлями — оставить только последнюю активную
3. Остальные завершить (finished)
"""

import sqlite3
from datetime import datetime
from pathlib import Path


def get_db_path():
    """Находит путь к БД."""
    possible_paths = [
        Path("/home/openclaw/.openclaw/workspace/agonarena_bot/data/agonarena.db"),
        Path("./data/agonarena.db"),
        Path("../data/agonarena.db"),
    ]
    for path in possible_paths:
        if path.exists():
            return str(path)
    raise FileNotFoundError("Database not found")


def fix_duel_inconsistencies(conn):
    """
    Исправляет дуэли 10 и 11:
    - Duel 10: round_1_active, но round 1 finished, round 2 pending
      -> должен быть round_2_active
    - Duel 11: round_1_active, но round 1 finished, round 2 in_progress
      -> должен быть round_2_active
    """
    cursor = conn.cursor()

    # Проверяем текущее состояние дуэлей 10 и 11
    cursor.execute("""
        SELECT d.id, d.status, d.current_round_number,
               dr.round_number, dr.status as round_status
        FROM duels d
        JOIN duel_rounds dr ON d.id = dr.duel_id
        WHERE d.id IN (10, 11)
        ORDER BY d.id, dr.round_number
    """)
    rows = cursor.fetchall()

    print("Текущее состояние дуэлей 10 и 11:")
    for row in rows:
        print(f"  Duel {row[0]}: duel_status={row[1]}, current_round={row[2]}, "
              f"round_{row[3]}_status={row[4]}")

    # Duel 10: round 1 finished, round 2 pending -> должен быть round_2_active
    # Duel 11: round 1 finished, round 2 in_progress -> должен быть round_2_active

    fixed = []
    for duel_id in [10, 11]:
        cursor.execute("""
            SELECT status FROM duel_rounds
            WHERE duel_id = ? AND round_number = 1
        """, (duel_id,))
        round1_status = cursor.fetchone()

        cursor.execute("""
            SELECT status FROM duel_rounds
            WHERE duel_id = ? AND round_number = 2
        """, (duel_id,))
        round2_status = cursor.fetchone()

        if round1_status and round1_status[0] == 'finished':
            # Round 1 завершен, проверяем round 2
            if round2_status:
                if round2_status[0] == 'pending':
                    # Round 2 еще не начат -> round_2_active
                    new_status = 'round_2_active'
                elif round2_status[0] == 'in_progress':
                    # Round 2 в процессе -> round_2_active
                    new_status = 'round_2_active'
                elif round2_status[0] == 'finished':
                    # Round 2 завершен -> должен быть finished
                    new_status = 'finished'
                else:
                    continue

                cursor.execute("""
                    UPDATE duels
                    SET status = ?, current_round_number = 2, updated_at = ?
                    WHERE id = ?
                """, (new_status, datetime.utcnow(), duel_id))
                fixed.append((duel_id, new_status))

    conn.commit()
    print(f"\nИсправлены дуэли: {fixed}")
    return fixed


def fix_multiple_active_duels(conn):
    """
    Для пользователей с множественными активными дуэлями:
    - Оставить только последнюю активную (по created_at)
    - Остальные завершить (finished)
    """
    cursor = conn.cursor()

    # Находим пользователей с множественными активными дуэлями
    cursor.execute("""
        SELECT user_telegram_id, COUNT(*) as cnt
        FROM duels
        WHERE status IN ('round_1_active', 'round_2_active', 'in_progress')
        GROUP BY user_telegram_id
        HAVING cnt > 1
    """)
    users_with_multiple = cursor.fetchall()

    print(f"\nПользователи с множественными активными дуэлями: {len(users_with_multiple)}")
    for user_id, count in users_with_multiple:
        print(f"  User {user_id}: {count} активных дуэлей")

    fixed = []
    for user_id, count in users_with_multiple:
        # Получаем все активные дуэли пользователя, отсортированные по created_at
        cursor.execute("""
            SELECT id, status, created_at
            FROM duels
            WHERE user_telegram_id = ?
              AND status IN ('round_1_active', 'round_2_active', 'in_progress')
            ORDER BY created_at DESC
        """, (user_id,))

        duels = cursor.fetchall()

        if len(duels) <= 1:
            continue

        # Оставляем последнюю (самую новую), остальные завершаем
        latest_duel_id = duels[0][0]
        duels_to_finish = [d[0] for d in duels[1:]]

        print(f"\n  User {user_id}:")
        print(f"    Оставляем активной: Duel {latest_duel_id} ({duels[0][1]})")
        print(f"    Завершаем: {duels_to_finish}")

        for duel_id in duels_to_finish:
            cursor.execute("""
                UPDATE duels
                SET status = 'finished', updated_at = ?
                WHERE id = ?
            """, (datetime.utcnow(), duel_id))
            fixed.append((user_id, duel_id))

    conn.commit()
    print(f"\nЗавершено дуэлей: {len(fixed)}")
    return fixed


def verify_fixes(conn):
    """Проверяет, что все исправления применены корректно."""
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("ПРОВЕРКА ИСПРАВЛЕНИЙ")
    print("="*60)

    # Проверяем дуэли 10 и 11
    cursor.execute("""
        SELECT d.id, d.status, d.current_round_number,
               dr.round_number, dr.status as round_status
        FROM duels d
        JOIN duel_rounds dr ON d.id = dr.duel_id
        WHERE d.id IN (10, 11)
        ORDER BY d.id, dr.round_number
    """)
    rows = cursor.fetchall()

    print("\nСостояние дуэлей 10 и 11 после исправления:")
    for row in rows:
        print(f"  Duel {row[0]}: duel_status={row[1]}, current_round={row[2]}, "
              f"round_{row[3]}_status={row[4]}")

    # Проверяем, что нет пользователей с множественными активными дуэлями
    cursor.execute("""
        SELECT user_telegram_id, COUNT(*) as cnt
        FROM duels
        WHERE status IN ('round_1_active', 'round_2_active', 'in_progress')
        GROUP BY user_telegram_id
        HAVING cnt > 1
    """)
    remaining = cursor.fetchall()

    print(f"\nПользователи с множественными активными дуэлями (должно быть 0): {len(remaining)}")
    for user_id, count in remaining:
        print(f"  User {user_id}: {count} активных дуэлей")

    # Общая статистика
    cursor.execute("""
        SELECT status, COUNT(*) as cnt
        FROM duels
        GROUP BY status
        ORDER BY cnt DESC
    """)
    stats = cursor.fetchall()

    print("\nСтатистика по статусам дуэлей:")
    for status, count in stats:
        print(f"  {status}: {count}")

    return len(remaining) == 0


def main():
    db_path = get_db_path()
    print(f"Using database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        print("\n" + "="*60)
        print("ИСПРАВЛЕНИЕ ДУЭЛЕЙ 10 И 11")
        print("="*60)
        fixed_duels = fix_duel_inconsistencies(conn)

        print("\n" + "="*60)
        print("ИСПРАВЛЕНИЕ МНОЖЕСТВЕННЫХ АКТИВНЫХ ДУЭЛЕЙ")
        print("="*60)
        fixed_multiple = fix_multiple_active_duels(conn)

        # Проверка
        is_valid = verify_fixes(conn)

        print("\n" + "="*60)
        if is_valid:
            print("✅ ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ УСПЕШНО")
        else:
            print("⚠️ ЕСТЬ НЕУСТРАНЕННЫЕ ПРОБЛЕМЫ")
        print("="*60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
