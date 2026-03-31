#!/usr/bin/env python3
"""Debug inline button sending"""
import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/agonarena_bot')

from app.bot.keyboards.main_menu import build_in_duel_keyboard

# Test keyboard creation
keyboard = build_in_duel_keyboard(round_no=1, duel_id=123)
print("Keyboard created:")
for i, row in enumerate(keyboard.inline_keyboard):
    print(f"  Row {i}: {[btn.text for btn in row]}")

# Check if keyboard is valid
if not keyboard.inline_keyboard:
    print("\n❌ ERROR: Keyboard is empty!")
else:
    print("\n✅ Keyboard has buttons")
    
# Check callback data
for row in keyboard.inline_keyboard:
    for btn in row:
        print(f"  Button: '{btn.text}' -> callback: '{btn.callback_data}'")
