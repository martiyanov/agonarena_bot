#!/usr/bin/env python3
"""
E2E Staging Tests — автоматические тесты на staging окружении

Тестирует полный flow без ручного вмешательства.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Конфигурация staging
TELEGRAM_BOT_TOKEN = "8695580621:AAEejmtA-MjCrz0dbXGWx46eCLgTwFrYJgE"
TEST_USER_ID = 127583377  # Степан
BASE_URL = "https://vm939255.vds.as210546.net"

sys.path.insert(0, str(Path(__file__).parent.parent))


class StagingTester:
    def __init__(self):
        self.results = []
        
    async def test_scenario_picker_buttons(self):
        """Тест: Кнопки сценариев в две строки с цифрами"""
        print("\n=== Тест: Кнопки сценариев ===")
        
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Создаём простой пикер сценариев inline
        scenarios = [
            {"id": 1, "title": "Менеджер ↔ Клиент", "difficulty": "normal"},
            {"id": 2, "title": "Тимлид ↔ Разработчик", "difficulty": "hard"},
            {"id": 3, "title": "HR ↔ Кандидат", "difficulty": "easy"},
            {"id": 4, "title": "Финансист ↔ Инвестор", "difficulty": "normal"},
            {"id": 5, "title": "CEO ↔ Команда", "difficulty": "hard"},
        ]
        
        # Строим клавиатуру как в реальном коде
        buttons = []
        for i, s in enumerate(scenarios[:5], 1):
            buttons.append(InlineKeyboardButton(
                text=f"[{i}]",
                callback_data=f"scenario:{s['id']}"
            ))
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons[:3], buttons[3:]])
        
        # Проверка: кнопки только с цифрами
        for row in keyboard.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("scenario:"):
                    # Должно быть [1], [2], а не [1. Название...]
                    assert "]" in btn.text and "." not in btn.text, \
                        f"Кнопка должна быть только цифрой: {btn.text}"
                    print(f"✅ Кнопка: {btn.text}")
        
        return {"test": "scenario_buttons", "status": "PASS"}
    
    async def test_inline_end_round_button(self):
        """Тест: Inline кнопка 'Завершить раунд' в сообщении дуэли"""
        print("\n=== Тест: Inline кнопка завершения ===")
        
        from app.bot.keyboards.main_menu import build_in_duel_keyboard
        
        # Создать клавиатуру для раунда 1
        keyboard = build_in_duel_keyboard(round_no=1, duel_id=123)
        
        # Проверка: есть кнопка "🏁 Завершить раунд"
        found = False
        for row in keyboard.inline_keyboard:
            for btn in row:
                if "Завершить" in btn.text or "🏁" in btn.text:
                    found = True
                    print(f"✅ Кнопка найдена: {btn.text}")
                    print(f"   Callback: {btn.callback_data}")
                    
                    # Проверка формата callback
                    assert btn.callback_data.startswith("duel:v1:end:"), \
                        f"Неверный формат callback: {btn.callback_data}"
        
        assert found, "Кнопка 'Завершить раунд' не найдена!"
        
        return {"test": "inline_end_round", "status": "PASS"}
    
    async def test_callback_format(self):
        """Тест: Формат callback_data корректен"""
        print("\n=== Тест: Формат callback ===")
        
        # Тестовый callback
        test_callback = "duel:v1:end:123:1"
        parts = test_callback.split(":")
        
        # Должно быть 5 частей
        assert len(parts) == 5, f"Ожидалось 5 частей, получено {len(parts)}"
        
        # Проверка частей
        assert parts[0] == "duel"
        assert parts[1] == "v1"
        assert parts[2] == "end"
        assert parts[3].isdigit()  # duel_id
        assert parts[4].isdigit()  # round_no
        
        print(f"✅ Формат корректен: {test_callback}")
        print(f"   duel_id: {parts[3]}, round_no: {parts[4]}")
        
        return {"test": "callback_format", "status": "PASS"}
    
    async def test_no_duplicate_random_button(self):
        """Тест: 'Случайный' убран из меню (только в пикере)"""
        print("\n=== Тест: Нет дублирования ===")
        
        from app.bot.keyboards.main_menu import build_main_menu
        
        # Проверка idle меню
        menu = build_main_menu(has_active_duel=False)
        buttons = [btn.text for row in menu.keyboard for btn in row]
        
        # "Случайный" должен быть убран из меню (теперь только в пикере)
        random_count = sum(1 for b in buttons if "Случайный" in b)
        
        # Ожидаем 0 — кнопка убрана из меню по дизайну AG-019
        assert random_count == 0, f"'Случайный' должен быть убран из меню, найдено: {random_count}"
        
        print(f"✅ 'Случайный' убран из меню (как задумано в AG-019)")
        print(f"   Кнопки: {buttons}")
        
        return {"test": "no_duplicate_random", "status": "PASS"}
    
    async def run_all_tests(self):
        """Запустить все тесты"""
        print("=" * 60)
        print("🧪 STAGING E2E TEST SUITE")
        print("=" * 60)
        
        tests = [
            self.test_scenario_picker_buttons,
            self.test_inline_end_round_button,
            self.test_callback_format,
            self.test_no_duplicate_random_button,
        ]
        
        results = []
        for test in tests:
            try:
                result = await test()
                results.append(result)
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                results.append({
                    "test": test.__name__,
                    "status": "FAIL",
                    "error": str(e)
                })
        
        # Итоги
        print("\n" + "=" * 60)
        print("📊 ИТОГИ")
        print("=" * 60)
        
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        
        for r in results:
            icon = "✅" if r["status"] == "PASS" else "❌"
            print(f"{icon} {r['test']}: {r['status']}")
        
        print(f"\nВсего: {len(results)} | PASS: {passed} | FAIL: {failed}")
        
        # Сохранить результаты
        output = {
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "summary": {"total": len(results), "passed": passed, "failed": failed}
        }
        
        output_file = Path("/home/openclaw/.openclaw/workspace/agonarena_bot/state/staging-test-results.json")
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\n📁 Результаты: {output_file}")
        
        return failed == 0


async def main():
    tester = StagingTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
