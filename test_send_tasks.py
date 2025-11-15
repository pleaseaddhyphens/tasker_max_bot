import requests
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

def test_send_tasks_sync():
    """
    Синхронный способ отправки задач пользователю
    """
    print("=== Тест 1: Отправка задач через requests (синхронно) ===\n")
    
    # Вариант 1: POST запрос с JSON
    response = requests.post(
        f"{BASE_URL}/send_tasks_to_user",
        json={
            "user_id": 41741568,
            "chat_id": "123",
            "notify": True
        }
    )
    
    print(f"Статус: {response.status_code}")
    result = response.json()
    print(f"Успех: {result['success']}")
    print(f"Количество задач: {result['tasks_count']}")
    print(f"\nСообщение отправлено пользователю:\n{result['message']}\n")
    print("-" * 60)


def test_send_tasks_simple():
    """
    Упрощенный способ через GET запрос
    """
    print("\n=== Тест 2: Упрощенный GET запрос ===\n")
    
    # Вариант 2: Простой GET запрос
    user_id = 41741568
    chat_id = "123"
    
    response = requests.get(f"{BASE_URL}/send_tasks_to_user/{user_id}/{chat_id}")
    
    print(f"Статус: {response.status_code}")
    result = response.json()
    print(f"Успех: {result['success']}")
    print(f"Количество задач: {result['tasks_count']}")
    print(f"\nСообщение:\n{result['message']}\n")
    print("-" * 60)


async def test_send_tasks_async():
    """
    Асинхронный способ отправки задач
    """
    print("\n=== Тест 3: Асинхронная отправка через httpx ===\n")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/send_tasks_to_user",
            json={
                "user_id": 41741568,
                "chat_id": "123",
                "notify": True
            }
        )
        
        print(f"Статус: {response.status_code}")
        result = response.json()
        print(f"Успех: {result['success']}")
        print(f"Количество задач: {result['tasks_count']}")
        print(f"\nСообщение:\n{result['message']}\n")
        print("-" * 60)


def test_create_multiple_tasks():
    """
    Создать несколько тестовых задач для демонстрации
    """
    print("\n=== Создание тестовых задач ===\n")
    
    tasks = [
        {
            "chat_id": "123",
            "creator_id": 41741568,
            "title": "Разработать новую фичу",
            "description": "Добавить функционал напоминаний",
            "tag": "разработка",
            "assignee_id": 41741568
        },
        {
            "chat_id": "123",
            "creator_id": 41741568,
            "title": "Написать тесты",
            "description": "Покрыть тестами все endpoints",
            "tag": "тестирование"
        },
        {
            "chat_id": "123",
            "creator_id": 41741568,
            "title": "Обновить документацию",
            "description": "Добавить примеры использования API",
            "tag": "документация"
        }
    ]
    
    for i, task in enumerate(tasks, 1):
        response = requests.post(f"{BASE_URL}/tasks", json=task)
        if response.status_code == 200:
            print(f"✅ Задача {i} создана: {task['title']}")
        else:
            print(f"❌ Ошибка при создании задачи {i}")
    
    print("\n" + "-" * 60)


def example_usage():
    """
    Примеры использования в реальном коде
    """
    print("\n=== Примеры использования ===\n")
    
    print("# Способ 1: POST запрос с параметрами")
    print("""
response = requests.post(
    "http://localhost:8000/send_tasks_to_user",
    json={
        "user_id": 41741568,
        "chat_id": "123",
        "notify": True
    }
)
print(response.json())
    """)
    
    print("\n# Способ 2: Упрощенный GET запрос")
    print("""
response = requests.get(
    "http://localhost:8000/send_tasks_to_user/41741568/123"
)
print(response.json())
    """)
    
    print("\n# Способ 3: Через curl")
    print("""
curl -X POST "http://localhost:8000/send_tasks_to_user" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": 41741568, "chat_id": "123", "notify": true}'
    """)
    
    print("\n# Способ 4: Простой GET через curl")
    print("""
curl "http://localhost:8000/send_tasks_to_user/41741568/123"
    """)
    
    print("\n" + "-" * 60)


def main():
    """
    Запуск всех тестов
    """
    print("🚀 Тестирование отправки задач пользователю\n")
    print("=" * 60)
    
    # Проверка доступности API
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ API недоступен. Запустите сервер!")
            return
    except Exception as e:
        print(f"❌ Не удалось подключиться к API: {e}")
        return
    
    # Создать тестовые задачи
    test_create_multiple_tasks()
    
    # Тест 1: Синхронная отправка
    test_send_tasks_sync()
    
    # Тест 2: Упрощенный GET
    test_send_tasks_simple()
    
    # Тест 3: Асинхронная отправка
    asyncio.run(test_send_tasks_async())
    
    # Показать примеры использования
    example_usage()
    
    print("\n✅ Все тесты завершены!")


if __name__ == "__main__":
    main()
