#!/bin/bash
# Скрипт для запуска MAX Bot с long polling

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Запуск MAX Bot Long Polling...${NC}"
echo ""

# Активация conda environment (если нужно)
if [ -n "$CONDA_DEFAULT_ENV" ] && [ "$CONDA_DEFAULT_ENV" != "max" ]; then
    echo -e "${YELLOW}⚠️  Активация conda environment 'max'${NC}"
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate max
fi

# Проверка наличия базы данных
echo -e "${YELLOW}📊 Проверка базы данных...${NC}"
if ! docker ps | grep -q tasker_max_db; then
    echo -e "${YELLOW}⚠️  База данных не запущена. Запуск...${NC}"
    docker compose up -d db
    echo -e "${YELLOW}⏳ Ожидание запуска БД (5 секунд)...${NC}"
    sleep 5
fi

# Проверка установки зависимостей
if ! python -c "import maxapi" 2>/dev/null; then
    echo -e "${YELLOW}📦 Установка зависимостей...${NC}"
    pip install -r requirements.txt
fi

# Запуск бота
echo -e "${GREEN}🤖 Запуск бота...${NC}"
echo ""
python longpolling_bot.py

