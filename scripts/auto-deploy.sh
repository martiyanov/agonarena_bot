#!/bin/bash
# Auto-Deploy — автоматический деплой при изменениях в коде

WATCH_DIR="/home/openclaw/.openclaw/workspace/agonarena_bot/app"
DEPLOY_SCRIPT="/home/openclaw/.openclaw/workspace/agonarena_bot/scripts/deploy.sh"
LAST_CHECK=$(date +%s)

echo "👁️  Auto-Deploy Watcher"
echo "======================="
echo "Watch: $WATCH_DIR"
echo "Deploy: $DEPLOY_SCRIPT"
echo ""

while true; do
    # Проверка изменений в app/
    CHANGED=$(find "$WATCH_DIR" -type f -newer /tmp/.auto-deploy-last-check 2>/dev/null | head -1)
    
    if [ -n "$CHANGED" ]; then
        echo "📝 Изменения обнаружены: $CHANGED"
        echo "🚀 Запуск деплоя..."
        echo ""
        
        # Запуск деплоя
        "$DEPLOY_SCRIPT"
        
        # Обновление timestamp
        touch /tmp/.auto-deploy-last-check
        
        echo ""
        echo "⏳ Следующая проверка через 5 сек..."
        echo ""
    fi
    
    sleep 5
done
