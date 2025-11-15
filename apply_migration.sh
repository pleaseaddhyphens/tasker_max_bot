#!/bin/bash
# Скрипт для применения миграции базы данных

set -e

echo "🔄 Применение миграции для ритуалов..."

# Проверяем доступность БД
if ! docker ps | grep -q tasker_max_db; then
    echo "❌ База данных не запущена"
    echo "   Запустите: sudo docker compose up -d db"
    exit 1
fi

echo "📊 Применяем миграцию 003_users_rituals.sql..."

# Применяем миграцию
docker exec -i tasker_max_db psql -U tasker_user -d tasker < 003_users_rituals.sql

if [ $? -eq 0 ]; then
    echo "✅ Миграция успешно применена!"
    echo ""
    echo "Проверяем таблицы..."
    docker exec -it tasker_max_db psql -U tasker_user -d tasker -c "\dt"
else
    echo "❌ Ошибка при применении миграции"
    exit 1
fi

