#!/bin/bash
# PM Self-Monitoring — самоконтроль для PM

LOG_FILE="/home/openclaw/.openclaw/workspace/agonarena_bot/state/pm-activity.log"
LAST_ACTIVITY_FILE="/tmp/pm-last-activity"
ALERT_THRESHOLD_MINUTES=30

# Записать активность
log_activity() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') — $1" >> "$LOG_FILE"
    date +%s > "$LAST_ACTIVITY_FILE"
}

# Проверить время с последней активности
check_idle_time() {
    if [ -f "$LAST_ACTIVITY_FILE" ]; then
        LAST_ACTIVITY=$(cat "$LAST_ACTIVITY_FILE")
        CURRENT_TIME=$(date +%s)
        IDLE_MINUTES=$(( (CURRENT_TIME - LAST_ACTIVITY) / 60 ))
        
        if [ $IDLE_MINUTES -ge $ALERT_THRESHOLD_MINUTES ]; then
            echo "⚠️ PM неактивен $IDLE_MINUTES минут!"
            return 1
        fi
    fi
    return 0
}

# Отправить уведомление (заглушка — в реальности через message tool)
send_alert() {
    echo "🚨 ALERT: $1"
    echo "$(date) — ALERT: $1" >> "$LOG_FILE"
}

case "$1" in
    log)
        log_activity "$2"
        ;;
    check)
        if ! check_idle_time; then
            send_alert "PM не отвечает более 30 минут при активной задаче"
        fi
        ;;
    *)
        echo "Usage: $0 {log 'message'|check}"
        ;;
esac
