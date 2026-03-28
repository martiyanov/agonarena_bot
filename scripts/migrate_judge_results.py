#!/usr/bin/env python3
"""Migration: Add round1_comment and round2_comment to judge_results table."""

import sqlite3
from pathlib import Path

DB_PATH = Path("/app/data/agonarena.db")


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(judge_results)")
    columns = {row[1] for row in cursor.fetchall()}

    if "round1_comment" not in columns:
        print("Adding round1_comment column...")
        cursor.execute("ALTER TABLE judge_results ADD COLUMN round1_comment TEXT")
        print("✓ round1_comment added")
    else:
        print("✓ round1_comment already exists")

    if "round2_comment" not in columns:
        print("Adding round2_comment column...")
        cursor.execute("ALTER TABLE judge_results ADD COLUMN round2_comment TEXT")
        print("✓ round2_comment added")
    else:
        print("✓ round2_comment already exists")

    conn.commit()
    conn.close()
    print("Migration complete!")


if __name__ == "__main__":
    migrate()
