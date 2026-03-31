#!/usr/bin/env python3
"""
Telegram Bot API Test Suite — автоматические тесты для Agon Arena Bot.

Запускает сценарии через Bot API и проверяет ответы.
"""

import asyncio
import os
import sys
from typing import Optional
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, ReplyKeyboardMarkup

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TEST_USER_ID = int(os.getenv("TEST_USER_ID", "127583377"))  # step_n

# Ожидания
EXPECTED_BUTTONS = {
    "start_menu": ["🎯 Сценарии", "🎲 Случайный", "ℹ️ Справка", "💬 Отзыв"],
    "in_duel_menu": ["🏁 Завершить раунд", "🎯 Сценарии", "🎲 Случайный", "ℹ️ Справка", "💬 Отзыв"],
}


class BotTester:
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
        self.results = []
    
    async def send_command(self, chat_id: int, command: str) -> Optional[Message]:
        """Отправить команду боту."""
        try:
            return await self.bot.send_message(chat_id, command)
        except Exception as e:
            self.results.append({"test": command, "status": "ERROR", "error": str(e)})
            return None
    
    async def get_last_message(self, chat_id: int, limit: int = 5) -> Optional[Message]:
        """Получить последнее сообщение от бота (через getUpdates)."""
        try:
            updates = await self.bot.get_updates(offset=-limit, timeout=5)
            for update in reversed(updates):
                if update.message and update.message.chat.id == chat_id:
                    return update.message
            return None
        except Exception as e:
            print(f"Error getting last message: {e}")
            return None
    
    async def test_start_command(self, chat_id: int) -> dict:
        """Тест: /start → главное меню."""
        print("\n=== Тест: /start → главное меню ===")
        
        msg = await self.send_command(chat_id, "/start")
        if not msg:
            return {"test": "/start", "status": "FAIL", "reason": "Нет ответа"}
        
        await asyncio.sleep(1)
        
        # Проверка текста
        response = await self.get_last_message(chat_id)
        if not response:
            return {"test": "/start", "status": "FAIL", "reason": "Бот не ответил"}
        
        # Проверка кнопок
        if response.reply_markup and isinstance(response.reply_markup, ReplyKeyboardMarkup):
            buttons = [btn.text for row in response.reply_markup.keyboard for btn in row]
            expected = EXPECTED_BUTTONS["start_menu"]
            
            if all(btn in buttons for btn in expected):
                print(f"✅ Кнопки меню: {buttons}")
                return {"test": "/start", "status": "PASS", "buttons": buttons}
            else:
                print(f"❌ Ожидилось: {expected}, найдено: {buttons}")
                return {"test": "/start", "status": "FAIL", "reason": f"Кнопки не совпадают. Ожидалось: {expected}, найдено: {buttons}"}
        else:
            return {"test": "/start", "status": "FAIL", "reason": "Нет reply keyboard"}
    
    async def test_scenarios_button(self, chat_id: int) -> dict:
        """Тест: 🎯 Сценарии → пикер сценариев."""
        print("\n=== Тест: 🎯 Сценарии → пикер сценариев ===")
        
        msg = await self.send_command(chat_id, "🎯 Сценарии")
        if not msg:
            return {"test": "Сценарии", "status": "FAIL", "reason": "Нет ответа"}
        
        await asyncio.sleep(1)
        
        # Проверка ответа
        response = await self.get_last_message(chat_id)
        if not response:
            return {"test": "Сценарии", "status": "FAIL", "reason": "Бот не ответил"}
        
        # Ожидаем: текст "Выберите сценарий" ИЛИ inline keyboard с кнопками
        has_scenario_text = "сценарий" in response.text.lower() if response.text else False
        has_inline_keyboard = response.reply_markup and isinstance(response.reply_markup, InlineKeyboardMarkup)
        
        if has_scenario_text or has_inline_keyboard:
            print(f"✅ Пикер сценариев показан")
            if has_inline_keyboard:
                inline_buttons = [[btn.text for btn in row] for row in response.reply_markup.inline_keyboard]
                print(f"   Inline кнопки: {inline_buttons}")
            return {"test": "Сценарии", "status": "PASS", "has_inline": has_inline_keyboard}
        else:
            print(f"❌ Ожидался пикер сценариев, получено: {response.text[:200] if response.text else 'нет текста'}")
            return {"test": "Сценарии", "status": "FAIL", "reason": f"Не пикер. Текст: {response.text[:200] if response.text else 'нет текста'}"}
    
    async def test_random_scenario(self, chat_id: int) -> dict:
        """Тест: 🎲 Случайный → старт дуэли."""
        print("\n=== Тест: 🎲 Случайный → старт дуэли ===")
        
        msg = await self.send_command(chat_id, "🎲 Случайный")
        if not msg:
            return {"test": "Случайный", "status": "FAIL", "reason": "Нет ответа"}
        
        await asyncio.sleep(1)
        
        response = await self.get_last_message(chat_id)
        if not response:
            return {"test": "Случайный", "status": "FAIL", "reason": "Бот не ответил"}
        
        # Ожидаем: "Поединок начался" ИЛИ "Раунд 1"
        has_duel_start = "поединок" in response.text.lower() if response.text else False
        has_round = "раунд" in response.text.lower() if response.text else False
        
        if has_duel_start or has_round:
            print(f"✅ Дуэль началась")
            return {"test": "Случайный", "status": "PASS"}
        else:
            print(f"❌ Ожидался старт дуэли, получено: {response.text[:200] if response.text else 'нет текста'}")
            return {"test": "Случайный", "status": "FAIL", "reason": "Не старт дуэли"}
    
    async def test_rules_button(self, chat_id: int) -> dict:
        """Тест: ℹ️ Справка → текст справки."""
        print("\n=== Тест: ℹ️ Справка → текст справки ===")
        
        msg = await self.send_command(chat_id, "ℹ️ Справка")
        if not msg:
            return {"test": "Справка", "status": "FAIL", "reason": "Нет ответа"}
        
        await asyncio.sleep(1)
        
        response = await self.get_last_message(chat_id)
        if not response:
            return {"test": "Справка", "status": "FAIL", "reason": "Бот не ответил"}
        
        # Ожидаем: "справка" или "как проходит"
        has_rules_text = "справка" in response.text.lower() or "как проходит" in response.text.lower() if response.text else False
        
        if has_rules_text:
            print(f"✅ Справка показана")
            return {"test": "Справка", "status": "PASS"}
        else:
            print(f"❌ Ожидалась справка, получено: {response.text[:200] if response.text else 'нет текста'}")
            return {"test": "Справка", "status": "FAIL", "reason": "Не справка"}
    
    async def run_all_tests(self, chat_id: int):
        """Запустить все тесты."""
        print("=" * 60)
        print("🧪 AGON ARENA BOT — AUTOMATED TEST SUITE")
        print("=" * 60)
        
        tests = [
            self.test_start_command(chat_id),
            self.test_scenarios_button(chat_id),
            self.test_random_scenario(chat_id),
            self.test_rules_button(chat_id),
        ]
        
        results = await asyncio.gather(*tests)
        
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
        
        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": results
        }
    
    async def close(self):
        """Закрыть сессию бота."""
        await self.bot.session.close()


async def main():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не настроен!")
        sys.exit(1)
    
    tester = BotTester(TELEGRAM_BOT_TOKEN)
    
    try:
        results = await tester.run_all_tests(TEST_USER_ID)
        
        # Сохранить результаты
        import json
        from pathlib import Path
        from datetime import datetime
        
        output_file = Path("/home/openclaw/.openclaw/workspace/agonarena_bot/state/test-results.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                **results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Результаты сохранены: {output_file}")
        
        # Вернуть код выхода
        sys.exit(0 if results["failed"] == 0 and results["errors"] == 0 else 1)
        
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
