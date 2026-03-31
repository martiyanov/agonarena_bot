#!/usr/bin/env python3
"""
Staging Test — тестирование на staging окружении.

Запускает бота в тестовом режиме и проверяет handlers.
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавить app в path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Настроить staging окружение
os.environ["APP_ENV"] = "staging"
os.environ["TELEGRAM_BOT_TOKEN"] = "8695580621:AAEejmtA-MjCrz0dbXGWx46eCLgTwFrYJgE"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/staging_test.db"

from tests.test_handlers import run_all_tests


async def main():
    print("=" * 60)
    print("🧪 STAGING TEST SUITE")
    print("=" * 60)
    print(f"APP_ENV: {os.environ.get('APP_ENV')}")
    print(f"TELEGRAM_BOT_TOKEN: {os.environ.get('TELEGRAM_BOT_TOKEN')[:20]}...")
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")
    print("=" * 60)
    
    # Запустить тесты handlers
    success = run_all_tests()
    
    if success:
        print("\n✅ Все тесты пройдены!")
        print("\n📝 Примечание:")
        print("Для полного тестирования в Telegram:")
        print("1. Запусти бота: python app/main.py")
        print("2. Открой Telegram: @AgonArenaStagingBot")
        print("3. Протестируй вручную:")
        print("   - /start → главное меню")
        print("   - 📚 Сценарии → пикер сценариев")
        print("   - 🎲 Случайный → старт дуэли")
        print("   - 🏁 Завершить раунд → inline кнопка")
    else:
        print("\n❌ Некоторые тесты не пройдены!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
