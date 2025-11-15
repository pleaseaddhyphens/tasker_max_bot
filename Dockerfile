FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements.txt и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY bot_with_db.py .

# Открываем порт
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "bot_with_db:app", "--host", "0.0.0.0", "--port", "8000"]
