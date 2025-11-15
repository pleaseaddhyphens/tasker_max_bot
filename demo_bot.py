#!/usr/bin/env python3
"""
Демонстрационный скрипт для тестирования логики бота без подключения к MAX API
Эмулирует получение сообщений и обработку команд
"""

import asyncio
import logging
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Эмуляция данных пользователя
DEMO_USER_ID = 94717924
DEMO_CHAT_ID = "demo_chat_123"

# Эмуляция базы данных в памяти
tasks_db = []
task_counter = 1


def create_task(user_id: int, chat_id: str, title: str, description: str = "") -> int:
    """Создать задачу в эмулированной БД"""
    global task_counter
    task = {
        "id": task_counter,
        "user_id": user_id,
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "status": "active"
    }
    tasks_db.append(task)
    task_id = task_counter
    task_counter += 1
    return task_id


def get_user_tasks(user_id: int, chat_id: str) -> list:
    """Получить задачи пользователя"""
    return [t for t in tasks_db if t["user_id"] == user_id and t["status"] == "active"]


def mark_task_completed(task_id: int, user_id: int) -> bool:
    """Отметить задачу выполненной"""
    for task in tasks_db:
        if task["id"] == task_id and task["user_id"] == user_id and task["status"] == "active":
            task["status"] = "completed"
            return True
    return False


def format_task_list(tasks: list) -> str:
    """Форматировать список задач"""
    if not tasks:
        return "📝 У вас нет активных задач"
    
    lines = [f"📋 Ваши активные задачи ({len(tasks)}):"]
    lines.append("")
    
    for i, task in enumerate(tasks, 1):
        lines.append(f"{i}. [{task['id']}] {task['title']}")
        if task['description']:
            desc = task['description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            lines.append(f"   📄 {desc}")
        lines.append("")
    
    return "\n".join(lines).strip()


async def send_message(user_id: int, text: str):
    """Эмуляция отправки сообщения"""
    print("\n" + "="*60)
    print(f"🤖 Ответ бота пользователю {user_id}:")
    print("-"*60)
    print(text)
    print("="*60 + "\n")


async def handle_list_tasks(user_id: int, chat_id: str):
    """Обработать команду /задачи"""
    logger.info(f"📋 Пользователь {user_id} запросил список задач")
    tasks = get_user_tasks(user_id, chat_id)
    response = format_task_list(tasks)
    await send_message(user_id, response)


async def handle_complete_task(user_id: int, chat_id: str, text: str):
    """Обработать команду /готово {id}"""
    import re
    match = re.search(r'/готово\s+(\d+)', text)
    
    if not match:
        await send_message(
            user_id,
            "⚠️ Неверный формат команды\n"
            "Используйте: /готово {id задачи}\n"
            "Например: /готово 5"
        )
        return
    
    task_id = int(match.group(1))
    logger.info(f"✓ Пользователь {user_id} завершает задачу {task_id}")
    
    success = mark_task_completed(task_id, user_id)
    
    if success:
        await send_message(user_id, f"✅ Задача #{task_id} отмечена как выполненная!")
    else:
        await send_message(
            user_id,
            f"⚠️ Задача #{task_id} не найдена или уже выполнена\n"
            f"Используйте /задачи для просмотра активных задач"
        )


async def handle_create_task(user_id: int, chat_id: str, text: str):
    """Обработать команду /создать"""
    task_text = text[len('/создать'):].strip()
    
    if not task_text:
        await send_message(
            user_id,
            "⚠️ Описание задачи не может быть пустым\n"
            "Используйте: /создать {название задачи}\n"
            "Например: /создать Написать отчет"
        )
        return
    
    lines = task_text.split('\n', 1)
    title = lines[0].strip()
    description = lines[1].strip() if len(lines) > 1 else ""
    
    logger.info(f"➕ Пользователь {user_id} создает задачу: {title}")
    
    task_id = create_task(user_id, chat_id, title, description)
    
    response = f"✅ Задача #{task_id} создана!\n\n"
    response += f"📝 {title}"
    if description:
        response += f"\n📄 {description[:100]}"
        if len(description) > 100:
            response += "..."
    
    await send_message(user_id, response)


async def handle_help(user_id: int):
    """Обработать команду /помощь"""
    help_text = """
🤖 MAX Task Bot - Справка по командам

📋 /задачи
   Показать список ваших активных задач

✅ /готово {id}
   Отметить задачу как выполненную
   Например: /готово 5

➕ /создать {название}
   Создать новую задачу
   Например: /создать Написать отчет
   
   Можно добавить описание со второй строки:
   /создать Написать отчет
   Подготовить квартальный отчет по проекту

❓ /помощь
   Показать эту справку
    """.strip()
    
    await send_message(user_id, help_text)


async def process_message(text: str, user_id: int = DEMO_USER_ID, chat_id: str = DEMO_CHAT_ID):
    """Обработать сообщение"""
    text = text.strip()
    
    print(f"\n👤 Пользователь {user_id}: {text}")
    
    if text == '/задачи':
        await handle_list_tasks(user_id, chat_id)
    elif text.startswith('/готово'):
        await handle_complete_task(user_id, chat_id, text)
    elif text.startswith('/создать'):
        await handle_create_task(user_id, chat_id, text)
    elif text in ['/помощь', '/help', '/start']:
        await handle_help(user_id)
    else:
        logger.warning(f"Неизвестная команда: {text}")


async def demo_scenario():
    """Демонстрационный сценарий работы бота"""
    print("\n" + "🎬 " + "="*58)
    print("  ДЕМОНСТРАЦИЯ РАБОТЫ MAX BOT LONG POLLING")
    print("="*60 + "\n")
    
    await asyncio.sleep(1)
    
    # Сценарий 1: Справка
    print("📍 Сценарий 1: Получение справки")
    await process_message("/помощь")
    await asyncio.sleep(2)
    
    # Сценарий 2: Создание задач
    print("\n📍 Сценарий 2: Создание задач")
    await process_message("/создать Написать документацию")
    await asyncio.sleep(1)
    
    await process_message("/создать Провести code review\nПроверить последние изменения в main branch")
    await asyncio.sleep(1)
    
    await process_message("/создать Обновить зависимости")
    await asyncio.sleep(2)
    
    # Сценарий 3: Просмотр задач
    print("\n📍 Сценарий 3: Просмотр списка задач")
    await process_message("/задачи")
    await asyncio.sleep(2)
    
    # Сценарий 4: Завершение задачи
    print("\n📍 Сценарий 4: Завершение задачи")
    await process_message("/готово 1")
    await asyncio.sleep(1)
    
    await process_message("/готово 99")  # Несуществующая задача
    await asyncio.sleep(2)
    
    # Сценарий 5: Обновленный список
    print("\n📍 Сценарий 5: Проверка обновленного списка")
    await process_message("/задачи")
    await asyncio.sleep(2)
    
    # Сценарий 6: Завершение оставшихся задач
    print("\n📍 Сценарий 6: Завершение всех задач")
    await process_message("/готово 2")
    await asyncio.sleep(1)
    await process_message("/готово 3")
    await asyncio.sleep(1)
    
    await process_message("/задачи")
    await asyncio.sleep(1)
    
    print("\n" + "="*60)
    print("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("="*60 + "\n")


async def interactive_mode():
    """Интерактивный режим"""
    print("\n" + "💬 " + "="*58)
    print("  ИНТЕРАКТИВНЫЙ РЕЖИМ")
    print("  Введите команды для тестирования бота")
    print("  Для выхода введите 'exit' или нажмите Ctrl+C")
    print("="*60 + "\n")
    
    while True:
        try:
            text = input("👤 Вы: ").strip()
            
            if text.lower() in ['exit', 'quit', 'выход']:
                print("\n👋 До свидания!")
                break
            
            if not text:
                continue
            
            await process_message(text)
            
        except KeyboardInterrupt:
            print("\n\n👋 До свидания!")
            break
        except Exception as e:
            logger.error(f"Ошибка: {e}")


async def main():
    """Главная функция"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        await interactive_mode()
    else:
        await demo_scenario()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 До свидания!")

