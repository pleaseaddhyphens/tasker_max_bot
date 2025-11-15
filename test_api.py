import requests
import json
from datetime import datetime, timedelta

# Базовый URL API
BASE_URL = "http://localhost:8000"

def test_create_task():
    """Тест создания задачи"""
    print("\n=== Тест 1: Создание задачи ===")
    
    # Данные задачи
    task_data = {
        "chat_id": "test_chat_123",
        "creator_id": 94717924,
        "title": "Разработать новую фичу",
        "description": "Нужно добавить функционал напоминаний о задачах",
        "tag": "разработка",
        "assignee_id": 94717924,
        "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
        "reminder_at": (datetime.now() + timedelta(days=6)).isoformat()
    }
    
    response = requests.post(f"{BASE_URL}/tasks", json=task_data)
    
    if response.status_code == 200:
        task = response.json()
        print(f"✅ Задача создана успешно!")
        print(f"   ID: {task['id']}")
        print(f"   Название: {task['title']}")
        print(f"   Тег: {task['tag']}")
        print(f"   Статус: {task['status']}")
        return task['id']
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)
        return None


def test_quick_create_task():
    """Тест быстрого создания задачи"""
    print("\n=== Тест 2: Быстрое создание задачи ===")
    
    params = {
        "chat_id": "test_chat_123",
        "creator_id": 94717924,
        "title": "Написать тесты",
        "description": "Покрыть тестами все API endpoints",
        "tag": "тестирование"
    }
    
    response = requests.post(f"{BASE_URL}/tasks/quick_create", params=params)
    
    if response.status_code == 200:
        task = response.json()
        print(f"✅ Задача быстро создана!")
        print(f"   ID: {task['id']}")
        print(f"   Название: {task['title']}")
        return task['id']
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)
        return None


def test_get_task(task_id):
    """Тест получения задачи по ID"""
    print(f"\n=== Тест 3: Получение задачи ID={task_id} ===")
    
    response = requests.get(f"{BASE_URL}/tasks/{task_id}")
    
    if response.status_code == 200:
        task = response.json()
        print(f"✅ Задача получена:")
        print(f"   Название: {task['title']}")
        print(f"   Описание: {task['description']}")
        print(f"   Статус: {task['status']}")
        print(f"   Тег: {task['tag']}")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)


def test_get_active_tasks(chat_id="test_chat_123"):
    """Тест получения активных задач чата"""
    print(f"\n=== Тест 4: Получение активных задач чата {chat_id} ===")
    
    response = requests.get(f"{BASE_URL}/chats/{chat_id}/tasks")
    
    if response.status_code == 200:
        tasks = response.json()
        print(f"✅ Найдено задач: {len(tasks)}")
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task['title']} (ID: {task['id']}, Тег: {task['tag']})")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)


def test_complete_task(task_id):
    """Тест завершения задачи"""
    print(f"\n=== Тест 5: Завершение задачи ID={task_id} ===")
    
    response = requests.patch(
        f"{BASE_URL}/tasks/{task_id}/status",
        json={"status": "completed"}
    )
    
    if response.status_code == 200:
        task = response.json()
        print(f"✅ Задача завершена!")
        print(f"   Статус: {task['status']}")
        print(f"   Дата завершения: {task['completed_at']}")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)


def test_get_archive(chat_id="test_chat_123"):
    """Тест получения архива задач"""
    print(f"\n=== Тест 6: Получение архива чата {chat_id} ===")
    
    response = requests.get(f"{BASE_URL}/chats/{chat_id}/archive")
    
    if response.status_code == 200:
        tasks = response.json()
        print(f"✅ Найдено задач в архиве: {len(tasks)}")
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task['title']} (завершена: {task['completed_at']})")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)


def main():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов API")
    
    # Проверка доступности API
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ API недоступен. Убедитесь, что сервер запущен на http://localhost:8000")
            return
    except Exception as e:
        print(f"❌ Не удалось подключиться к API: {e}")
        print("   Убедитесь, что сервер запущен: python bot_with_db.py")
        return
    
    # Создание задач
    task_id_1 = test_create_task()
    task_id_2 = test_quick_create_task()
    
    # Проверка созданных задач
    if task_id_1:
        test_get_task(task_id_1)
    
    # Получение всех активных задач
    test_get_active_tasks()
    
    # Завершение задачи
    if task_id_1:
        test_complete_task(task_id_1)
    
    # Проверка активных задач после завершения
    test_get_active_tasks()
    
    # Проверка архива
    test_get_archive()
    
    print("\n✅ Все тесты завершены!")


if __name__ == "__main__":
    main()
