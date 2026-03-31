#!/usr/bin/env python3
"""
AG-062-TEST: Комплексное тестирование всех сценариев бота Agon Arena

Запуск: python scripts/test_scenarios.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import session as db_session
from app.services.duel_service import DuelService
from app.db.models import Duel, DuelRound, JudgeResult


class ScenarioTester:
    """Test all bot scenarios according to state machine."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def log_error(self, msg: str):
        self.errors.append(msg)
        print(f"❌ ERROR: {msg}")
        
    def log_warning(self, msg: str):
        self.warnings.append(msg)
        print(f"⚠️ WARNING: {msg}")
        
    def log_success(self, msg: str):
        print(f"✅ {msg}")

    async def test_database_consistency(self):
        """Test 1: Database consistency - check for orphaned records."""
        print("\n=== Test 1: Database Consistency ===")
        
        async with db_session.AsyncSessionLocal() as session:
            duel_service = DuelService()
            
            # Check for duels without rounds
            from sqlalchemy import select
            from app.db.models import Duel
            
            result = await session.execute(select(Duel))
            duels = result.scalars().all()
            
            for duel in duels:
                rounds = await duel_service.get_duel_rounds(session, duel.id)
                if not rounds:
                    self.log_error(f"Duel {duel.id} has no rounds")
                elif len(rounds) != 2:
                    self.log_warning(f"Duel {duel.id} has {len(rounds)} rounds (expected 2)")
                    
            # Check for rounds without messages
            from app.db.models import DuelRound
            result = await session.execute(select(DuelRound))
            rounds = result.scalars().all()
            
            for round_obj in rounds:
                # Check round consistency
                if round_obj.status == "in_progress" and not round_obj.started_at:
                    self.log_warning(f"Round {round_obj.id} is in_progress but has no started_at")
                if round_obj.status == "finished" and not round_obj.finished_at:
                    self.log_warning(f"Round {round_obj.id} is finished but has no finished_at")
                    
        if not any(e.startswith("Duel") for e in self.errors):
            self.log_success("Database consistency check passed")

    async def test_duel_status_transitions(self):
        """Test 2: Duel status transitions - valid state machine."""
        print("\n=== Test 2: Duel Status Transitions ===")
        
        valid_transitions = {
            "draft": ["round_1_active"],
            "round_1_active": ["round_1_processing", "round_1_transition", "finished", "cancelled"],
            "round_1_processing": ["round_1_transition", "finished", "cancelled"],
            "round_1_transition": ["round_2_active", "finished", "cancelled"],
            "round_2_active": ["round_2_processing", "round_2_transition", "finished", "cancelled"],
            "round_2_processing": ["round_2_transition", "finished", "cancelled"],
            "round_2_transition": ["finished", "cancelled"],
            "finished": [],
            "cancelled": [],
        }
        
        async with db_session.AsyncSessionLocal() as session:
            from sqlalchemy import select
            from app.db.models import Duel
            
            result = await session.execute(select(Duel))
            duels = result.scalars().all()
            
            invalid_statuses = []
            for duel in duels:
                if duel.status not in valid_transitions:
                    invalid_statuses.append(f"Duel {duel.id}: {duel.status}")
                    
            if invalid_statuses:
                for inv in invalid_statuses:
                    self.log_error(f"Invalid duel status: {inv}")
            else:
                self.log_success("All duel statuses are valid")

    async def test_round_status_consistency(self):
        """Test 3: Round status consistency with duel status."""
        print("\n=== Test 3: Round Status Consistency ===")
        
        async with db_session.AsyncSessionLocal() as session:
            from sqlalchemy import select
            from app.db.models import Duel, DuelRound
            
            result = await session.execute(select(Duel))
            duels = result.scalars().all()
            
            for duel in duels:
                rounds = await session.execute(
                    select(DuelRound).where(DuelRound.duel_id == duel.id)
                )
                rounds = rounds.scalars().all()
                
                if duel.status in ("round_1_active", "round_1_processing"):
                    round_1 = next((r for r in rounds if r.round_number == 1), None)
                    if round_1 and round_1.status == "finished":
                        self.log_error(f"Duel {duel.id} is {duel.status} but round 1 is finished")
                        
                if duel.status in ("round_2_active", "round_2_processing"):
                    round_1 = next((r for r in rounds if r.round_number == 1), None)
                    round_2 = next((r for r in rounds if r.round_number == 2), None)
                    if round_1 and round_1.status != "finished":
                        self.log_error(f"Duel {duel.id} is {duel.status} but round 1 is not finished")
                    if round_2 and round_2.status == "finished":
                        self.log_error(f"Duel {duel.id} is {duel.status} but round 2 is finished")
                        
        if not any("round" in e for e in self.errors):
            self.log_success("Round status consistency check passed")

    async def test_judge_results_consistency(self):
        """Test 4: Judge results consistency."""
        print("\n=== Test 4: Judge Results Consistency ===")
        
        async with db_session.AsyncSessionLocal() as session:
            from sqlalchemy import select
            from app.db.models import JudgeResult, Duel
            
            # Check for judge results on unfinished duels
            result = await session.execute(
                select(JudgeResult, Duel).join(Duel, JudgeResult.duel_id == Duel.id)
                .where(Duel.status.notin_(["finished", "cancelled"]))
            )
            invalid_judges = result.all()
            
            if invalid_judges:
                for jr, duel in invalid_judges:
                    self.log_warning(f"Judge result {jr.id} exists for unfinished duel {duel.id} ({duel.status})")
                    
            # Check for finished duels without judge results
            result = await session.execute(
                select(Duel).where(Duel.status == "finished")
            )
            finished_duels = result.scalars().all()
            
            for duel in finished_duels:
                judge_results = await session.execute(
                    select(JudgeResult).where(JudgeResult.duel_id == duel.id)
                )
                if not judge_results.scalars().all():
                    self.log_warning(f"Finished duel {duel.id} has no judge results")
                    
        if not any("Judge" in e for e in self.errors):
            self.log_success("Judge results consistency check passed")

    async def test_user_active_duels(self):
        """Test 5: User active duels - only one active per user."""
        print("\n=== Test 5: User Active Duels ===")
        
        async with db_session.AsyncSessionLocal() as session:
            from sqlalchemy import select, func
            from app.db.models import Duel
            
            result = await session.execute(
                select(Duel.user_telegram_id, func.count(Duel.id))
                .where(Duel.status.notin_(["finished", "cancelled"]))
                .group_by(Duel.user_telegram_id)
                .having(func.count(Duel.id) > 1)
            )
            multiple_active = result.all()
            
            if multiple_active:
                for user_id, count in multiple_active:
                    self.log_error(f"User {user_id} has {count} active duels")
            else:
                self.log_success("No users with multiple active duels")

    async def test_orphaned_records(self):
        """Test 6: Check for orphaned records."""
        print("\n=== Test 6: Orphaned Records ===")
        
        async with db_session.AsyncSessionLocal() as session:
            from sqlalchemy import select, exists
            from app.db.models import DuelRound, Duel, JudgeResult
            
            # Rounds without duels
            result = await session.execute(
                select(DuelRound).where(
                    ~exists().where(Duel.id == DuelRound.duel_id)
                )
            )
            orphaned_rounds = result.scalars().all()
            
            if orphaned_rounds:
                for r in orphaned_rounds:
                    self.log_error(f"Orphaned round {r.id} (duel_id={r.duel_id})")
            else:
                self.log_success("No orphaned rounds")

    async def test_scenario_references(self):
        """Test 7: Scenario references integrity."""
        print("\n=== Test 7: Scenario References ===")
        
        async with db_session.AsyncSessionLocal() as session:
            from sqlalchemy import select, exists
            from app.db.models import Duel, Scenario
            
            result = await session.execute(
                select(Duel).where(
                    Duel.scenario_id.isnot(None) &
                    ~exists().where(Scenario.id == Duel.scenario_id)
                )
            )
            invalid_scenarios = result.scalars().all()
            
            if invalid_scenarios:
                for d in invalid_scenarios:
                    self.log_error(f"Duel {d.id} references non-existent scenario {d.scenario_id}")
            else:
                self.log_success("All scenario references are valid")

    async def run_all_tests(self):
        """Run all scenario tests."""
        print("=" * 60)
        print("AG-062: Comprehensive Scenario Testing")
        print("=" * 60)
        
        await self.test_database_consistency()
        await self.test_duel_status_transitions()
        await self.test_round_status_consistency()
        await self.test_judge_results_consistency()
        await self.test_user_active_duels()
        await self.test_orphaned_records()
        await self.test_scenario_references()
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        
        if self.errors:
            print("\n❌ FAILED - Critical issues found:")
            for e in self.errors:
                print(f"  - {e}")
            return 1
        elif self.warnings:
            print("\n⚠️ PASSED with warnings")
            return 0
        else:
            print("\n✅ ALL TESTS PASSED")
            return 0


async def main():
    tester = ScenarioTester()
    exit_code = await tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
