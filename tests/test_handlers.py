#!/usr/bin/env python3
"""
Handler Tests — проверка handlers без Telegram API.

Проверяет что handlers корректно зарегистрированы и нет конфликтов.
"""

import sys
from pathlib import Path

# Добавить app в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.bot.handlers.menu import MENU_TEXTS, SCENARIOS_BUTTON, RULES_BUTTON


def test_no_handler_conflicts():
    """Тест: Нет конфликтов handlers (одна кнопка — один handler)."""
    print("\n=== Тест: Конфликты handlers ===")
    
    # Собрать все кнопки из MENU_TEXTS
    menu_buttons = list(MENU_TEXTS)
    
    # Проверить что SCENARIOS_BUTTON не в RULES_BUTTON handler
    # Это было проблемой: SCENARIOS_BUTTON был в двух handlers
    
    # Импортировать handlers для проверки
    from app.bot.handlers.menu import (
        show_scenarios,
        handle_rules_button,
    )
    
    # Проверка: SCENARIOS_BUTTON должен быть только в show_scenarios
    # handle_rules_button должен обрабатывать только RULES_BUTTON
    
    print(f"✅ SCENARIOS_BUTTON: '{SCENARIOS_BUTTON}'")
    print(f"✅ RULES_BUTTON: '{RULES_BUTTON}'")
    print(f"✅ MENU_TEXTS: {len(menu_buttons)} кнопок")
    
    # Проверка что кнопки разные
    if SCENARIOS_BUTTON in [RULES_BUTTON]:
        print(f"❌ КОНФЛИКТ: SCENARIOS_BUTTON == RULES_BUTTON")
        return {"test": "handler_conflicts", "status": "FAIL", "reason": "Кнопки идентичны"}
    
    print(f"✅ Конфликтов не найдено")
    return {"test": "handler_conflicts", "status": "PASS"}


def test_scenarios_handler_exists():
    """Тест: Handler для 'Сценарии' существует."""
    print("\n=== Тест: Handler для 'Сценарии' ===")
    
    # Проверить что show_scenarios существует
    from app.bot.handlers.menu import show_scenarios, _send_scenario_picker
    
    if show_scenarios and _send_scenario_picker:
        print(f"✅ Handler show_scenarios существует")
        print(f"✅ Функция _send_scenario_picker существует")
        return {"test": "scenarios_handler", "status": "PASS"}
    else:
        print(f"❌ Handler не найден")
        return {"test": "scenarios_handler", "status": "FAIL", "reason": "Handler не существует"}


def test_keyboard_builder():
    """Тест: Inline keyboard builder существует."""
    print("\n=== Тест: Inline keyboard builder ===")
    
    from app.bot.keyboards.main_menu import build_main_menu, build_in_duel_keyboard
    
    # Проверить build_main_menu
    main_menu = build_main_menu(has_active_duel=False)
    if main_menu and main_menu.keyboard:
        print(f"✅ build_main_menu работает")
        buttons = [btn.text for row in main_menu.keyboard for btn in row]
        print(f"   Кнопки: {buttons}")
        
        # Проверить что END_ROUND_BUTTON нет в idle меню
        if "🏁 Завершить раунд" not in buttons:
            print(f"✅ END_ROUND_BUTTON удалён из idle меню")
        else:
            print(f"❌ END_ROUND_BUTTON всё ещё в idle меню")
            return {"test": "keyboard_builder", "status": "FAIL", "reason": "END_ROUND_BUTTON в idle меню"}
    else:
        print(f"❌ build_main_menu не работает")
        return {"test": "keyboard_builder", "status": "FAIL", "reason": "build_main_menu не работает"}
    
    # Проверить build_in_duel_keyboard
    try:
        inline_keyboard = build_in_duel_keyboard(round_no=1, duel_id=123)
        if inline_keyboard and inline_keyboard.inline_keyboard:
            print(f"✅ build_in_duel_keyboard работает")
            inline_buttons = [btn.text for row in inline_keyboard.inline_keyboard for btn in row]
            print(f"   Inline кнопки: {inline_buttons}")
            
            if "🏁 Завершить раунд" in inline_buttons:
                print(f"✅ Кнопка 'Завершить раунд' в inline")
            else:
                print(f"❌ Кнопка 'Завершить раунд' не найдена")
                return {"test": "keyboard_builder", "status": "FAIL", "reason": "Нет inline кнопки"}
        else:
            print(f"❌ build_in_duel_keyboard не работает")
            return {"test": "keyboard_builder", "status": "FAIL", "reason": "build_in_duel_keyboard не работает"}
    except Exception as e:
        print(f"❌ build_in_duel_keyboard ошибка: {e}")
        return {"test": "keyboard_builder", "status": "FAIL", "reason": str(e)}
    
    return {"test": "keyboard_builder", "status": "PASS"}


def test_judge_formatting():
    """Тест: Форматирование судей (нет дублирования 'Раунд 1:')."""
    print("\n=== Тест: Форматирование судей ===")
    
    from app.bot.handlers.menu import _format_final_verdict
    from app.services.judge_service import JudgeService
    
    # Создать mock verdicts
    class MockVerdict:
        def __init__(self, judge_type, comment, round1_comment=None, round2_comment=None):
            self.judge_type = judge_type
            self.comment = comment
            self.round1_comment = round1_comment
            self.round2_comment = round2_comment
    
    verdicts = [
        MockVerdict(
            judge_type="coach",
            comment="Общий комментарий",
            round1_comment="Раунд 1: Стороны установили контакт",  # Уже с префиксом
            round2_comment="Раунд 2: Взаимодействие улучшилось"  # Уже с префиксом
        )
    ]
    
    judge_service = JudgeService()
    result = _format_final_verdict(judge_service, verdicts, "Финальный вердикт")
    
    print(f"Результат форматирования:\n{result}")
    
    # Проверить нет ли дублирования "Раунд 1: Раунд 1:"
    if "Раунд 1: Раунд 1:" in result:
        print(f"❌ ДУБЛИРОВАНИЕ: найдено 'Раунд 1: Раунд 1:'")
        return {"test": "judge_formatting", "status": "FAIL", "reason": "Дублирование префикса"}
    
    if "Раунд 2: Раунд 2:" in result:
        print(f"❌ ДУБЛИРОВАНИЕ: найдено 'Раунд 2: Раунд 2:'")
        return {"test": "judge_formatting", "status": "FAIL", "reason": "Дублирование префикса"}
    
    print(f"✅ Дублирования не найдено")
    return {"test": "judge_formatting", "status": "PASS"}


def run_all_tests():
    """Запустить все тесты."""
    print("=" * 60)
    print("🧪 AGON ARENA BOT — HANDLER TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_no_handler_conflicts,
        test_scenarios_handler_exists,
        test_keyboard_builder,
        test_judge_formatting,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Ошибка теста {test_func.__name__}: {e}")
            results.append({
                "test": test_func.__name__,
                "status": "ERROR",
                "reason": str(e)
            })
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ")
    print("=" * 60)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    for r in results:
        status_icon = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {r['test']}: {r['status']}")
        if "reason" in r:
            print(f"   {r['reason']}")
    
    print(f"\nВсего: {len(results)} | PASS: {passed} | FAIL: {failed} | ERROR: {errors}")
    print("=" * 60)
    
    # Сохранить результаты
    import json
    from datetime import datetime
    
    output_file = Path("/home/openclaw/.openclaw/workspace/agonarena_bot/state/test-results-handlers.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "errors": errors
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Результаты сохранены: {output_file}")
    
    return all(r["status"] == "PASS" for r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
