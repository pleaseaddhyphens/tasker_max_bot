#!/usr/bin/env python3
"""
Тест для проверки настройки бота
Проверяет:
- Наличие необходимых библиотек
- Подключение к базе данных
- Корректность конфигурации
"""

import sys
import os

def test_imports():
    """Проверка импорта необходимых библиотек"""
    print("📦 Проверка зависимостей...")
    
    try:
        import asyncpg
        print("  ✅ asyncpg установлен")
    except ImportError:
        print("  ❌ asyncpg не установлен. Выполните: pip install asyncpg")
        return False
    
    try:
        import httpx
        print("  ✅ httpx установлен")
    except ImportError:
        print("  ❌ httpx не установлен. Выполните: pip install httpx")
        return False
    
    print("  ✅ Все необходимые зависимости установлены")
    return True


async def test_database():
    """Проверка подключения к базе данных"""
    print("\n📊 Проверка подключения к базе данных...")
    
    import asyncpg
    
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://tasker_user:tasker_password@localhost:5432/tasker"
    )
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("  ✅ Подключение к БД успешно")
        
        # Проверяем наличие таблиц
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        
        table_names = [row['tablename'] for row in tables]
        
        if 'chats' in table_names:
            print("  ✅ Таблица 'chats' существует")
        else:
            print("  ❌ Таблица 'chats' не найдена")
            await conn.close()
            return False
        
        if 'tasks' in table_names:
            print("  ✅ Таблица 'tasks' существует")
        else:
            print("  ❌ Таблица 'tasks' не найдена")
            await conn.close()
            return False
        
        # Проверяем количество задач
        count = await conn.fetchval("SELECT COUNT(*) FROM tasks")
        print(f"  📝 Задач в базе: {count}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка подключения к БД: {e}")
        print("\n💡 Убедитесь, что база данных запущена:")
        print("   docker compose up -d db")
        return False


def test_config():
    """Проверка конфигурации"""
    print("\n⚙️  Проверка конфигурации...")
    
    token = os.getenv("MAX_BOT_TOKEN")
    if token:
        print(f"  ✅ MAX_BOT_TOKEN установлен ({token[:20]}...)")
    else:
        print("  ⚠️  MAX_BOT_TOKEN не установлен (будет использован токен по умолчанию)")
    
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print(f"  ✅ DATABASE_URL установлен")
    else:
        print("  ⚠️  DATABASE_URL не установлен (будет использован URL по умолчанию)")
    
    return True


async def main():
    """Главная функция тестирования"""
    print("🧪 Тестирование настройки MAX Bot Long Polling\n")
    print("=" * 60)
    
    # Проверка импортов
    if not test_imports():
        print("\n❌ Тест не пройден: необходимо установить зависимости")
        print("   Выполните: pip install -r requirements.txt")
        return False
    
    # Проверка конфигурации
    test_config()
    
    # Проверка БД
    if not await test_database():
        print("\n❌ Тест не пройден: проблемы с базой данных")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Все проверки пройдены успешно!")
    print("\n🚀 Бот готов к запуску:")
    print("   ./start_bot.sh")
    print("   или")
    print("   python longpolling_bot.py")
    return True


if __name__ == '__main__':
    import asyncio
    
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Тестирование прервано")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        sys.exit(1)

