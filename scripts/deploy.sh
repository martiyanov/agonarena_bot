#!/bin/bash
# Deploy script — деплой изменений в Docker контейнер

set -e

echo "🚀 Agon Arena Bot — Deploy Script"
echo "=================================="

# Конфигурация
CONTAINER_NAME="agonarena-bot-app"
IMAGE_NAME="agonarena_bot_app"
ENV_FILE=".env"
DOCKER_COMPOSE_FILE="docker-compose.yml"

# Проверка окружения
if [ "$1" == "--staging" ]; then
    ENV_FILE=".env.staging"
    DOCKER_COMPOSE_FILE="docker-compose.staging.yml"
    CONTAINER_NAME="agonarena-bot-staging"
    echo "🎯 STAGING окружение"
elif [ "$1" == "--prod" ]; then
    echo "🎯 PRODUCTION окружение"
else
    echo "🎯 LOCAL/DEFAULT окружение"
fi

echo ""

# 1. Остановка старого контейнера
echo "⏹️  Остановка контейнера..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# 2. Сборка нового образа (без кэша для актуального кода)
echo "🔨 Сборка образа (без кэша)..."
cd /home/openclaw/.openclaw/workspace/agonarena_bot
docker build --no-cache -t "$IMAGE_NAME" .

# 3. Запуск контейнера (через docker run, минуя docker-compose)
echo "▶️  Запуск контейнера..."

# Очистка старого контейнера
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Запуск
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -p 8080:8080 \
    -v /home/openclaw/.openclaw/workspace/agonarena_bot/data:/app/data \
    --env-file "$ENV_FILE" \
    "$IMAGE_NAME"

# 4. Проверка статуса
echo ""
echo "📊 Статус:"
docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}"

# 5. Логи (последние 10 строк)
echo ""
echo "📋 Последние логи:"
docker logs --tail 10 "$CONTAINER_NAME" 2>/dev/null || echo "Логи недоступны"

echo ""
echo "✅ Деплой завершён!"
echo ""
echo "📝 Примечание:"
echo "   Для просмотра логов: docker logs -f $CONTAINER_NAME"
echo "   Для остановки: docker stop $CONTAINER_NAME"
