FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копируем и устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY bot_with_db.py .
COPY longpolling_bot.py .
COPY ritual_config.py .
COPY pictures ./pictures

# Создаем непривилегированного пользователя
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Открываем порт
EXPOSE 8000

# Healthcheck для проверки работоспособности бота
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f longpolling_bot.py || exit 1

# Команда запуска (по умолчанию longpolling бот)
CMD ["python", "longpolling_bot.py"]
