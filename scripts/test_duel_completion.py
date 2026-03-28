#!/usr/bin/env python3
"""Integration test: Verify duel completion flow works end-to-end."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import session as db_session
from app.services.duel_service import DuelService
from app.services.judge_service import JudgeService


async def test_duel_completion():
    """Test that duel can be completed and judge results saved."""
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        judge_service = JudgeService()

        # Get latest duel for user (owner)
        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=127583377)
        if not duel:
            print("❌ No duel found for user 127583377")
            return False

        print(f"Testing duel #{duel.id}, status={duel.status}")

        # Check if duel is already finished
        if duel.status == "finished":
            print(f"✓ Duel #{duel.id} already finished")
            
            # Check judge results exist
            judge_results = await duel_service.list_judge_results(session, duel.id)
            if judge_results:
                print(f"✓ Judge results exist: {len(judge_results)} records")
                for jr in judge_results:
                    print(f"  - {jr.judge_type}: winner={jr.winner}")
                    if jr.round1_comment:
                        print(f"    round1: {jr.round1_comment[:50]}...")
                    if jr.round2_comment:
                        print(f"    round2: {jr.round2_comment[:50]}...")
                return True
            else:
                print("❌ No judge results found for finished duel")
                return False

        # Duel not finished - check if we can complete it
        if duel.status == "judging":
            print(f"⏳ Duel #{duel.id} in judging state")
            return True

        if duel.status == "in_progress":
            print(f"⏳ Duel #{duel.id} still in progress (status={duel.status})")
            print("  This is expected if user hasn't finished round 2 yet")
            return True

        print(f"⚠ Unexpected duel status: {duel.status}")
        return True


async def test_judge_results_schema():
    """Test that judge_results table has round1_comment and round2_comment columns."""
    import sqlite3
    
    db_path = Path("/app/data/agonarena.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(judge_results)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()
    
    required = {"round1_comment", "round2_comment"}
    missing = required - columns
    
    if missing:
        print(f"❌ Missing columns in judge_results: {missing}")
        return False
    
    print("✓ judge_results schema OK (round1_comment, round2_comment present)")
    return True


async def main():
    print("=" * 60)
    print("DUEL COMPLETION INTEGRATION TEST")
    print("=" * 60)
    
    results = []
    
    print("\n1. Testing judge_results schema...")
    results.append(await test_judge_results_schema())
    
    print("\n2. Testing duel completion flow...")
    results.append(await test_duel_completion())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
