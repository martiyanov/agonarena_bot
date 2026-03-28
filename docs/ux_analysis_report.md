# UX ANALYSIS REPORT

**Bot:** Agon Arena  
**Date:** 2026-03-28  
**Analyst:** AG-024

---

## Screen-by-Screen Analysis

### 1. Main Menu (`/start` command)

**Current state:**
- Welcome message with bot name "Agon Arena"
- Brief description: "Тренажёр управленческих поединков"
- Feature bullets: 2 раунда, смена ролей, 3 судьи
- Reply keyboard with 6 buttons in 3 rows

**Issues:**
- ❌ **Inconsistent button labels:** `menu.py` defines `START_BUTTON = "🎯 Выбрать сценарий"` but keyboard uses `SELECT_SCENARIO_BUTTON` — potential maintenance issue
- ❌ **No visual hierarchy:** All buttons same size/weight, no clear primary action
- ❌ **Wasted space:** "Завершить раунд" button shown when no duel is active (confusing)
- ⚠️ **Missing context:** User doesn't know if they have an active duel from main menu

**Recommendations:**
1. **High Priority:** Dynamic keyboard — hide "Завершить раунд" when no active duel exists
2. **High Priority:** Add status line showing active duel state (e.g., "🔴 Активный поединок #123" or "⚪ Нет активных поединков")
3. **Medium Priority:** Consolidate button constants between `menu.py` and `keyboards/main_menu.py`
4. **Low Priority:** Consider inline keyboard for cleaner appearance

---

### 2. Scenario Picker

**Current state:**
- Lists up to 10 scenarios with number, title, roles, difficulty
- Inline keyboard: 2 rows of 5 number buttons (1-5, 6-10) + "🎲 Случайный" button
- HTML formatted with bold headers

**Issues:**
- ❌ **Poor scalability:** If >10 scenarios, scenarios 11+ are silently hidden (no pagination, no indication)
- ❌ **Cognitive load:** User must count/match numbers to scenarios — error-prone
- ❌ **No scenario preview:** Can't see description before selecting
- ⚠️ **Difficulty formatting:** Inconsistent — shown as `| {difficulty}` but may be empty
- ⚠️ **Long titles:** Scenario titles may wrap awkwardly, breaking visual alignment

**Recommendations:**
1. **High Priority:** Add pagination or "show more" if >10 scenarios exist
2. **High Priority:** Replace numbered buttons with scenario title buttons (or hybrid: "1. Краткое название")
3. **Medium Priority:** Add scenario description preview on selection (callback query answer or follow-up message)
4. **Medium Priority:** Standardize difficulty display (always show, or hide consistently)
5. **Low Priority:** Add scenario category badges if categories exist

---

### 3. Duel Flow — Round 1 (Start)

**Current state:**
- Duel ID header
- Scenario title
- Timer hint (⏱ На раунд: X минут/сек)
- Role assignment (user vs AI)
- Opening line from AI
- Instructions: "Что дальше" with 3 numbered steps

**Issues:**
- ❌ **Information overload:** 10+ lines of text before user can act
- ❌ **Redundant instructions:** "Что дальше" section repeated every duel start — users learn once, don't need reminder
- ❌ **Timer ambiguity:** Shows total time but not countdown (user must wait for turn response to see remaining time)
- ⚠️ **No visual separation:** Opening line blends with instructions
- ⚠️ **Parse mode inconsistency:** Uses HTML but no line breaks between sections

**Recommendations:**
1. **High Priority:** Split into 2 messages: (1) duel setup info, (2) opening line as separate message for emphasis
2. **High Priority:** Remove "Что дальше" instructions after first use (store in user state, show only on first duel)
3. **Medium Priority:** Add visible countdown timer in turn responses (not just at start)
4. **Low Priority:** Use quote formatting or code block for AI opening line to distinguish from bot instructions

---

### 4. Duel Flow — Round 2 (Transition)

**Current state:**
- "Раунд 1 завершён" header
- Role swap announcement
- Timer hint
- New opening line from AI (now user plays opposite role)

**Issues:**
- ❌ **No completion feedback:** Doesn't show what happened in Round 1 (no summary)
- ❌ **Abrupt transition:** User doesn't know if their Round 1 performance was good/bad
- ⚠️ **Same format as Round 1:** Missed opportunity to emphasize role swap
- ⚠️ **No "Continue" button:** User must remember to send message (no explicit call-to-action button)

**Recommendations:**
1. **High Priority:** Add 1-line Round 1 summary (e.g., "Вы сыграли за {role}, было N реплик")
2. **Medium Priority:** Emphasize role swap visually: "🔄 РОЛИ СМЕНИЛИСЬ" header with before/after
3. **Medium Priority:** Add inline button "Начать раунд 2" to acknowledge and proceed
4. **Low Priority:** Show Round 1 duration (how long user took)

---

### 5. Round Completion ("Завершить раунд" button)

**Current state:**
- Static button in main menu keyboard
- Same button used for: end Round 1 → start Round 2, end Round 2 → finish duel
- No confirmation dialog

**Issues:**
- ❌ **Always visible:** Button shown even when no duel active (confusing)
- ❌ **Ambiguous action:** Same button for two different transitions (user doesn't know which will happen)
- ❌ **No state indication:** User can't tell if they're in Round 1 or 2 from keyboard
- ❌ **No confirmation:** Accidental clicks immediately advance/finish duel
- ⚠️ **Race condition handling:** `ACTION_IN_PROGRESS_USERS` prevents double-clicks but shows generic "Действие уже выполняется" — not informative

**Recommendations:**
1. **High Priority:** Dynamic button text: "🏁 Завершить раунд 1" vs "🏁 Завершить поединок" based on state
2. **High Priority:** Hide button when no active duel exists
3. **Medium Priority:** Add confirmation for Round 2 → Finish transition (irreversible action)
4. **Medium Priority:** Show current round in main menu status
5. **Low Priority:** Improve error messages with specific state info

---

### 6. Judge Results Screen (Final Verdict)

**Current state:**
- "Поединок завершён" header
- Final verdict (summary from all judges)
- Individual judge comments with labels (e.g., "Стратег", "Тактик", "Психолог")
- Round-specific comments if available (indented sub-bullets)

**Issues:**
- ❌ **Wall of text:** All judges shown sequentially — hard to scan
- ❌ **No visual distinction:** Final verdict vs judge comments use same formatting
- ❌ **Judge labels unclear:** "Стратег/Тактик/Психолог" not explained (new users don't know what each means)
- ⚠️ **HTML escaping:** Uses `escape()` but no line breaks between judge sections
- ⚠️ **No save/export:** Results shown once, user must check "Итоги" to see again

**Recommendations:**
1. **High Priority:** Add visual separators between judges (horizontal rules or emoji dividers)
2. **High Priority:** Bold/format final verdict more prominently (larger header, different emoji)
3. **Medium Priority:** Add judge role explanations in help screen or tooltip
4. **Medium Priority:** Add "📥 Сохранить результаты" button (export to text/file)
5. **Low Priority:** Add rating scores if judges provide numeric ratings (e.g., 1-10 per category)

---

### 7. Results History (`my_results` handler)

**Current state:**
- Shows ONLY last duel (not history)
- Duel status, current round, timer hint
- Round statuses with roles
- Judge comments (same format as final screen)
- Brief final verdict (first line only)

**Issues:**
- ❌ **Misleading name:** "Итоги" implies history, but shows only last duel
- ❌ **No pagination:** Can't view previous duels
- ❌ **Incomplete verdict:** Shows only first line of final verdict (truncated)
- ⚠️ **Status info not useful:** "Статус: finished" is obvious if showing results
- ⚠️ **No filtering/sorting:** Can't filter by scenario, date, outcome

**Recommendations:**
1. **High Priority:** Rename button to "Последний поединок" or implement actual history
2. **High Priority:** Show full final verdict, not truncated
3. **Medium Priority:** Implement duel history list with pagination (last 5-10 duels)
4. **Medium Priority:** Add duel metadata: date, duration, scenario name
5. **Low Priority:** Add stats dashboard (total duels, win rate, avg scores)

---

### 8. Help Screen (`how_it_works` handler)

**Current state:**
- 4 sections: Как проходит поединок, Как действовать, Обратная связь, Поддержать проект
- Numbered steps for actions
- Links to donation
- ~15 lines total

**Issues:**
- ❌ **Outdated instructions:** References "Завершить раунд" button behavior that may confuse (see Round Completion issues)
- ❌ **No troubleshooting:** Doesn't address common issues (voice not working, duel stuck, etc.)
- ❌ **Wall of text:** No visual breaks between sections
- ⚠️ **Donation link placement:** Feels out of place in help screen (should be separate)
- ⚠️ **No examples:** Doesn't show what a good response looks like

**Recommendations:**
1. **High Priority:** Add FAQ section with common issues and solutions
2. **Medium Priority:** Move donation link to separate button/menu item
3. **Medium Priority:** Add example dialogue snippet (what good responses look like)
4. **Low Priority:** Add video/GIF demo link if available
5. **Low Priority:** Break into collapsible sections (if Telegram supports) or split into multiple messages

---

### 9. Feedback Flow

**Current state:**
- "💬 Обратная связь" button in main menu
- Puts user in `FEEDBACK_REQUEST_USERS` set
- Next message captured and forwarded to owner
- Confirmation: "✅ Спасибо за обратную связь! Сообщение передано владельцу."

**Issues:**
- ❌ **No validation:** Empty or single-character feedback accepted
- ❌ **No edit/cancel:** Once in feedback mode, user can't exit without sending
- ❌ **Silent failure:** If forwarding fails, user still gets success message (lies to user)
- ⚠️ **No follow-up:** User doesn't know if/when owner responded
- ⚠️ **No feedback categories:** Can't categorize (bug, feature request, general)

**Recommendations:**
1. **High Priority:** Add minimum length validation (e.g., 10 characters)
2. **High Priority:** Add "❌ Отмена" button to exit feedback mode
3. **Medium Priority:** Honest error handling: if forwarding fails, tell user and retry
4. **Medium Priority:** Add feedback categories (inline buttons: "🐛 Баг", "💡 Идея", "📝 Другое")
5. **Low Priority:** Add ticket/ID system so user can reference their feedback later

---

## Top 5 Priority Improvements

1. **High Priority:** Dynamic main menu keyboard → Hide "Завершить раунд" when no active duel, show duel status
   - **Impact:** High (reduces confusion for all users)
   - **Effort:** Low (state check + conditional keyboard)

2. **High Priority:** Scenario picker pagination → Handle >10 scenarios gracefully
   - **Impact:** High (prevents silent data loss as scenarios grow)
   - **Effort:** Medium (pagination logic + navigation buttons)

3. **High Priority:** Split duel start messages → Separate setup info from opening line
   - **Impact:** High (improves readability and focus)
   - **Effort:** Low (split one `answer()` into two)

4. **Medium Priority:** Results history implementation → Show actual duel history, not just last duel
   - **Impact:** Medium (users expect history from "Итоги" button)
   - **Effort:** Medium-High (DB queries + pagination UI)

5. **Medium Priority:** Feedback mode improvements → Add cancel button, validation, honest error handling
   - **Impact:** Medium (improves trust and UX for feedback sub-flow)
   - **Effort:** Low (add cancel button, validation, better error messages)

---

## Recommended Implementation Order

| # | Fix | Impact | Effort | Notes |
|---|-----|--------|--------|-------|
| 1 | Dynamic main menu keyboard | High | Low | Quick win, immediate UX improvement |
| 2 | Split duel start messages | High | Low | Reduces cognitive load |
| 3 | Feedback mode improvements | Medium | Low | Builds user trust |
| 4 | Scenario picker pagination | High | Medium | Prevents future issues as content grows |
| 5 | Results history implementation | Medium | Medium-High | Requires DB + UI work |
| 6 | Round completion button state | High | Low | Clarifies current action |
| 7 | Judge results formatting | Medium | Low | Improves readability |
| 8 | Help screen FAQ section | Medium | Low | Reduces support burden |
| 9 | Role swap emphasis (Round 2) | Medium | Low | Improves transition clarity |
| 10 | Button constant consolidation | Low | Low | Code quality, not user-facing |

---

## Additional Observations

### Consistency Issues
- **Button labels:** Defined in both `menu.py` and `keyboards/main_menu.py` — DRY violation
- **Parse modes:** Mix of HTML and Markdown (`start.py` uses Markdown, `menu.py` uses HTML)
- **Error messages:** Varying levels of detail (some specific, some generic)

### Accessibility Concerns
- **Color reliance:** Emoji used for status but no text alternative for screen readers
- **Touch targets:** Inline keyboard number buttons may be too small for some users
- **Text length:** Some messages approach Telegram's length limits without truncation strategy

### Missing Features
- **Duel abandonment:** No way to cancel/forfeit an active duel
- **Settings:** No user preferences (e.g., turn time limits, notification settings)
- **Onboarding:** First-time users get same experience as veterans (no progressive disclosure)
- **Localization:** All text hardcoded in Russian (no i18n infrastructure)

---

**Ready for PM to review and spawn DEV for implementation.**
