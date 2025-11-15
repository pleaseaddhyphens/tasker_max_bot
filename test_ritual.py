#!/usr/bin/env python3
"""
Тестовый скрипт для проверки отправки ритуалов
Использование: python test_ritual.py <user_id> <ritual_type>
Пример: python test_ritual.py 94717924 morning
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from longpolling_bot import (
    init_db_pool, 
    init_http_client, 
    close_db_pool, 
    close_http_client,
    send_ritual_to_user,
    send_message_with_image
)
import ritual_config


async def test_ritual(user_id: int, ritual_type: str = "morning"):
    """
    Тестирование отправки ритуала
    
    Args:
        user_id: ID пользователя в MAX
        ritual_type: 'morning' или 'evening'
    """
    try:
        print(f"🧪 Тестирование отправки {ritual_type} ритуала для пользователя {user_id}")
        
        # Инициализация
        print("📦 Инициализация...")
        await init_db_pool()
        await init_http_client()
        print("✅ Инициализация завершена")
        
        # Отправка ритуала
        print(f"📤 Отправка ритуала...")
        await send_ritual_to_user(user_id, ritual_type)
        print("✅ Ритуал отправлен")
        
        # Ждем немного для завершения запроса
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Закрываем соединения
        await close_http_client()
        await close_db_pool()
        print("👋 Тест завершен")


async def test_simple_message(user_id: int):
    """
    Тестирование отправки простого сообщения с картинкой
    
    Args:
        user_id: ID пользователя в MAX
    """
    try:
        print(f"🧪 Тестирование отправки сообщения с картинкой для пользователя {user_id}")
        
        # Инициализация
        print("📦 Инициализация...")
        await init_http_client()
        print("✅ Инициализация завершена")
        
        # Получаем путь к картинке
        ritual = ritual_config.get_ritual_config("morning")
        image_path = ritual["image_path"]
        
        print(f"🖼️ Путь к картинке: {image_path}")
        print(f"📁 Файл существует: {os.path.exists(image_path)}")
        
        # Отправка сообщения
        print(f"📤 Отправка сообщения...")
        success = await send_message_with_image(
            user_id, 
            "Тестовое сообщение с картинкой", 
            image_path
        )
        
        if success:
            print("✅ Сообщение отправлено успешно")
        else:
            print("❌ Ошибка отправки сообщения")
        
        # Ждем немного для завершения запроса
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Закрываем соединения
        await close_http_client()
        print("👋 Тест завершен")


def print_usage():
    """Вывести справку"""
    print("""
🧪 Тестовый скрипт для проверки отправки ритуалов

Использование:
  python test_ritual.py <user_id> <ritual_type>
  python test_ritual.py <user_id> simple

Параметры:
  user_id       - ID пользователя в MAX (обязательный)
  ritual_type   - Тип ритуала: morning или evening (по умолчанию: morning)
                  или simple для простого теста с картинкой

Примеры:
  python test_ritual.py 94717924 morning
  python test_ritual.py 94717924 evening
  python test_ritual.py 94717924 simple
    """)


def main():
    """Главная функция"""
    # Проверяем аргументы
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("❌ Ошибка: user_id должен быть числом")
        print_usage()
        sys.exit(1)
    
    # Определяем тип теста
    test_type = sys.argv[2] if len(sys.argv) > 2 else "morning"
    
    # Запускаем тест
    if test_type == "simple":
        asyncio.run(test_simple_message(user_id))
    elif test_type in ["morning", "evening"]:
        asyncio.run(test_ritual(user_id, test_type))
    else:
        print(f"❌ Ошибка: неизвестный тип ритуала '{test_type}'")
        print("Используйте: morning, evening или simple")
        sys.exit(1)


if __name__ == "__main__":
    main()



