#!/usr/bin/env python3
"""
MAX Bot с Long Polling для управления задачами
Команды:
- /задачи - вывести список задач пользователя
- /готово {id} - отметить задачу выполненной
- /создать {описание} - создать новую задачу
"""

import asyncio
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, time as time_class
import httpx
import asyncpg
import os
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import ritual_config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
ACCESS_TOKEN = os.getenv(
    "MAX_BOT_TOKEN",
    "f9LHodD0cOLy---sDc0u5izFP25VAGQm2DBuG1SlbyEza4x4iCCKzzx2B2dAeDpdDawHn3hoFWKGl3CVMffI"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://tasker_user:tasker_password@localhost:5432/tasker"
)

BASE_URL = "https://botapi.max.ru"

# Пул соединений с БД (будет инициализирован при запуске)
db_pool: Optional[asyncpg.Pool] = None

# HTTP клиент для работы с API
http_client: Optional[httpx.AsyncClient] = None

# Планировщик для ритуалов
scheduler: Optional[AsyncIOScheduler] = None


# ========== Database Functions ==========

async def init_db_pool():
    """Инициализация пула соединений с БД"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("✅ База данных подключена")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        raise


async def close_db_pool():
    """Закрытие пула соединений"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("❌ База данных отключена")


async def init_http_client():
    """Инициализация HTTP клиента"""
    global http_client
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(90.0, connect=10.0),
        headers={
            "Authorization": ACCESS_TOKEN,
            "Content-Type": "application/json"
        }
    )
    logger.info("✅ HTTP клиент инициализирован")


async def close_http_client():
    """Закрытие HTTP клиента"""
    global http_client
    if http_client:
        await http_client.aclose()
        logger.info("❌ HTTP клиент закрыт")


async def get_or_create_chat(max_chat_id: str, name: Optional[str] = None) -> int:
    """Получить или создать чат в БД"""
    async with db_pool.acquire() as conn:
        # Пытаемся найти существующий чат
        row = await conn.fetchrow(
            "SELECT id FROM chats WHERE max_chat_id = $1",
            max_chat_id
        )
        
        if row:
            return row['id']
        
        # Создаем новый чат
        row = await conn.fetchrow(
            "INSERT INTO chats (max_chat_id, name) VALUES ($1, $2) RETURNING id",
            max_chat_id,
            name or f"Chat {max_chat_id}"
        )
        return row['id']


async def get_user_tasks(user_id: int, chat_id: str) -> List[dict]:
    """Получить активные задачи пользователя в чате"""
    chat_db_id = await get_or_create_chat(chat_id)
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                t.id, t.title, t.description, t.tag, 
                t.status, t.created_at, t.deadline
            FROM tasks t
            WHERE t.chat_id = $1 
                AND (t.creator_id = $2 OR t.assignee_id = $2)
                AND t.status = 'active'
            ORDER BY t.deadline ASC NULLS LAST, t.created_at DESC
        """, chat_db_id, user_id)
        
        return [dict(row) for row in rows]


async def mark_task_completed(task_id: int, user_id: int) -> bool:
    """Отметить задачу как выполненную"""
    async with db_pool.acquire() as conn:
        # Проверяем, что задача существует и пользователь имеет к ней доступ
        task = await conn.fetchrow("""
            SELECT id FROM tasks 
            WHERE id = $1 
                AND (creator_id = $2 OR assignee_id = $2)
                AND status = 'active'
        """, task_id, user_id)
        
        if not task:
            return False
        
        # Обновляем статус
        await conn.execute("""
            UPDATE tasks 
            SET status = 'completed', completed_at = $1
            WHERE id = $2
        """, datetime.now(), task_id)
        
        return True


async def create_task(user_id: int, chat_id: str, title: str, description: str = "") -> int:
    """Создать новую задачу"""
    chat_db_id = await get_or_create_chat(chat_id)
    
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO tasks (
                chat_id, creator_id, title, description, status
            ) VALUES ($1, $2, $3, $4, 'active')
            RETURNING id
        """, chat_db_id, user_id, title, description)
        
        return row['id']


# ========== User Management Functions ==========

async def get_or_create_user(user_id: int, first_name: str = "", last_name: str = "") -> dict:
    """Получить или создать пользователя"""
    logger.info(f"🔍 get_or_create_user для user_id={user_id}, name={first_name}")
    
    async with db_pool.acquire() as conn:
        # Пытаемся найти пользователя
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE max_user_id = $1",
            user_id
        )
        
        if row:
            logger.info(f"✅ Пользователь {user_id} найден в БД")
            return dict(row)
        
        logger.info(f"➕ Создаём нового пользователя {user_id}")
        
        # Создаем нового пользователя
        try:
            row = await conn.fetchrow("""
                INSERT INTO users (max_user_id, first_name, last_name, onboarding_step)
                VALUES ($1, $2, $3, 'none')
                RETURNING *
            """, user_id, first_name, last_name)
            
            logger.info(f"✅ Пользователь {user_id} создан")
            return dict(row)
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя: {e}")
            import traceback
            traceback.print_exc()
            raise


async def update_user_onboarding(user_id: int, step: str):
    """Обновить шаг онбординга пользователя"""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE users 
            SET onboarding_step = $1, updated_at = NOW()
            WHERE max_user_id = $2
        """, step, user_id)


async def update_user_ritual_time(user_id: int, ritual_type: str, time_str: str):
    """Обновить время ритуала (morning или evening)"""
    from datetime import time as time_class
    
    logger.info(f"🔍 Обновление времени ритуала {ritual_type} для пользователя {user_id}: {time_str}")
    
    # Преобразуем строку "HH:MM" в объект time
    hour, minute = map(int, time_str.split(':'))
    time_obj = time_class(hour, minute)
    logger.info(f"🔍 Преобразовано в time объект: {time_obj}")
    
    async with db_pool.acquire() as conn:
        if ritual_type == "morning":
            result = await conn.execute("""
                UPDATE users 
                SET morning_ritual_time = $1, updated_at = NOW()
                WHERE max_user_id = $2
            """, time_obj, user_id)
            logger.info(f"🔍 Результат UPDATE morning: {result}")
        else:  # evening
            result = await conn.execute("""
                UPDATE users 
                SET evening_ritual_time = $1, updated_at = NOW()
                WHERE max_user_id = $2
            """, time_obj, user_id)
            logger.info(f"🔍 Результат UPDATE evening: {result}")


async def log_mood(user_id: int, mood_level: int, ritual_type: str):
    """Записать самочувствие пользователя"""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO mood_logs (user_id, mood_level, ritual_type)
            VALUES ($1, $2, $3)
        """, user_id, mood_level, ritual_type)


async def get_user(user_id: int) -> Optional[dict]:
    """Получить пользователя по ID"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE max_user_id = $1",
            user_id
        )
        return dict(row) if row else None


# ========== Helper Functions ==========

def format_task_list(tasks: List[dict]) -> str:
    """Форматировать список задач для вывода"""
    if not tasks:
        return "📝 У вас нет активных задач"
    
    lines = [f"📋 Ваши активные задачи ({len(tasks)}):"]
    lines.append("")
    
    for i, task in enumerate(tasks, 1):
        # Заголовок
        lines.append(f"{i}. [{task['id']}] {task['title']}")
        
        # Тег
        if task.get('tag'):
            lines.append(f"   🏷️ {task['tag']}")
        
        # Описание (первые 100 символов)
        if task.get('description'):
            desc = task['description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            lines.append(f"   📄 {desc}")
        
        # Дедлайн
        if task.get('deadline'):
            deadline_str = task['deadline'].strftime("%d.%m.%Y %H:%M")
            lines.append(f"   ⏰ {deadline_str}")
        
        lines.append("")
    
    return "\n".join(lines).strip()


def extract_user_and_chat_id(message: Dict[str, Any]) -> tuple:
    """Извлечь ID пользователя и чата из сообщения"""
    # MAX API структура:
    # - sender.user_id - отправитель
    # - recipient.chat_id - чат
    
    # Получаем ID отправителя
    user_id = message.get("sender", {}).get("user_id")
    if not user_id:
        user_id = message.get("from", {}).get("user_id")
    
    # Получаем ID чата
    recipient = message.get("recipient", {})
    chat_id = recipient.get("chat_id")
    
    if not chat_id:
        # Fallback на другие возможные поля
        chat_id = message.get("chat", {}).get("id")
    
    if not chat_id:
        chat_id = user_id  # Личный чат с пользователем
    
    return int(user_id), str(chat_id)


async def send_message(user_id: int, text: str) -> bool:
    """Отправить сообщение пользователю"""
    try:
        url = f"{BASE_URL}/messages"
        params = {"user_id": user_id}
        payload = {"text": text, "notify": True}
        
        response = await http_client.post(url, params=params, json=payload)
        
        if response.status_code == 200:
            return True
        else:
            logger.error(f"❌ Ошибка отправки сообщения: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке сообщения: {e}")
        return False


async def upload_image_to_max(image_path: str) -> Optional[dict]:
    """
    Загрузить изображение на сервер MAX и получить структуру photos
    
    Args:
        image_path: Путь к файлу изображения
        
    Returns:
        Структура photos для вложения или None в случае ошибки
    """
    try:
        # Шаг 1: Получить URL для загрузки
        upload_url_endpoint = f"{BASE_URL}/uploads"
        params = {"type": "image"}
        
        response = await http_client.post(upload_url_endpoint, params=params)
        
        if response.status_code != 200:
            logger.error(f"❌ Ошибка получения URL для загрузки: {response.status_code} - {response.text}")
            return None
        
        upload_data = response.json()
        upload_url = upload_data.get("url")
        
        if not upload_url:
            logger.error(f"❌ URL для загрузки не найден в ответе: {upload_data}")
            return None
        
        logger.info(f"✅ Получен URL для загрузки")
        
        # Шаг 2: Загрузить файл по полученному URL
        with open(image_path, 'rb') as f:
            files = {'data': f}
            # Создаём отдельный клиент без Authorization заголовка для загрузки файла
            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0)) as upload_client:
                upload_response = await upload_client.post(upload_url, files=files)
        
        if upload_response.status_code != 200:
            logger.error(f"❌ Ошибка загрузки файла: {upload_response.status_code} - {upload_response.text}")
            return None
        
        upload_result = upload_response.json()
        
        # API возвращает структуру: {"photos": {"photo_id": {"token": "..."}}}
        # Возвращаем именно эту структуру для использования в attachments
        if "photos" in upload_result:
            photos = upload_result.get("photos", {})
            logger.info(f"✅ Файл успешно загружен, получена структура photos")
            return photos
        
        # Если структура другая, пытаемся найти token
        token = upload_result.get("token")
        if token:
            logger.info(f"✅ Файл успешно загружен, получен token")
            return {"token": token}
        
        logger.error(f"❌ Неожиданная структура ответа: {upload_result}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке изображения: {e}")
        import traceback
        traceback.print_exc()
        return None


async def send_message_with_image(user_id: int, text: str, image_path: str) -> bool:
    """
    Отправить сообщение с изображением пользователю
    
    Args:
        user_id: ID пользователя
        text: Текст сообщения
        image_path: Путь к файлу изображения
        
    Returns:
        True если сообщение отправлено успешно
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(image_path):
            logger.error(f"❌ Файл не найден: {image_path}")
            # Отправляем хотя бы текст
            return await send_message(user_id, text)
        
        # Загружаем изображение и получаем структуру photos
        photos = await upload_image_to_max(image_path)
        
        if not photos:
            logger.warning(f"⚠️ Не удалось загрузить изображение, отправляем только текст")
            return await send_message(user_id, text)
        
        # Отправляем сообщение с вложением
        url = f"{BASE_URL}/messages"
        params = {"user_id": user_id}
        payload = {
            "text": text,
            "notify": True,
            "attachments": [
                {
                    "type": "image",
                    "payload": {
                        "photos": photos
                    }
                }
            ]
        }
        
        response = await http_client.post(url, params=params, json=payload)
        
        if response.status_code == 200:
            logger.info(f"✅ Сообщение с изображением отправлено пользователю {user_id}")
            return True
        else:
            logger.error(f"❌ Ошибка отправки сообщения с изображением: {response.status_code} - {response.text}")
            # Пробуем отправить хотя бы текст
            return await send_message(user_id, text)
            
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке сообщения с изображением: {e}")
        import traceback
        traceback.print_exc()
        # Пробуем отправить хотя бы текст
        return await send_message(user_id, text)


# ========== Command Handlers ==========

async def handle_list_tasks(user_id: int, chat_id: str):
    """Обработчик команды /задачи - вывести список задач"""
    try:
        logger.info(f"📋 Пользователь {user_id} запросил список задач в чате {chat_id}")
        
        tasks = await get_user_tasks(user_id, chat_id)
        response = format_task_list(tasks)
        
        await send_message(user_id, response)
        logger.info(f"✅ Отправлено {len(tasks)} задач пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке /задачи: {e}")
        await send_message(user_id, "⚠️ Произошла ошибка при получении списка задач")


async def handle_complete_task(user_id: int, chat_id: str, text: str):
    """Обработчик команды /готово {id} - отметить задачу выполненной"""
    try:
        # Извлекаем ID задачи
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
        logger.info(f"✓ Пользователь {user_id} пытается завершить задачу {task_id}")
        
        # Отмечаем задачу как выполненную
        success = await mark_task_completed(task_id, user_id)
        
        if success:
            await send_message(user_id, f"✅ Задача #{task_id} отмечена как выполненная!")
            logger.info(f"✅ Задача {task_id} завершена пользователем {user_id}")
        else:
            await send_message(
                user_id,
                f"⚠️ Задача #{task_id} не найдена или уже выполнена\n"
                f"Используйте /задачи для просмотра активных задач"
            )
            logger.warning(f"⚠️ Задача {task_id} не найдена для пользователя {user_id}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке /готово: {e}")
        await send_message(user_id, "⚠️ Произошла ошибка при обновлении задачи")


async def handle_create_task(user_id: int, chat_id: str, text: str):
    """Обработчик команды /создать {описание} - создать новую задачу"""
    try:
        # Извлекаем описание задачи
        task_text = text[len('/создать'):].strip()
        
        if not task_text:
            await send_message(
                user_id,
                "⚠️ Описание задачи не может быть пустым\n"
                "Используйте: /создать {название задачи}\n"
                "Например: /создать Написать отчет"
            )
            return
        
        # Разделяем на название и описание (первая строка - название, остальное - описание)
        lines = task_text.split('\n', 1)
        title = lines[0].strip()
        description = lines[1].strip() if len(lines) > 1 else ""
        
        logger.info(f"➕ Пользователь {user_id} создает задачу: {title}")
        
        # Создаем задачу
        task_id = await create_task(user_id, chat_id, title, description)
        
        response = f"✅ Задача #{task_id} создана!\n\n"
        response += f"📝 {title}"
        if description:
            response += f"\n📄 {description[:100]}"
            if len(description) > 100:
                response += "..."
        
        await send_message(user_id, response)
        logger.info(f"✅ Создана задача {task_id} пользователем {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании задачи: {e}")
        await send_message(user_id, "⚠️ Произошла ошибка при создании задачи")


async def handle_start(user_id: int, first_name: str = "", last_name: str = ""):
    """Обработчик команды /start - начало онбординга"""
    logger.info(f"🚀 Пользователь {user_id} начинает онбординг")
    
    # Получаем или создаем пользователя
    user = await get_or_create_user(user_id, first_name, last_name)
    
    # Формируем приветствие
    name = user.get('first_name', 'друг')
    if not name:
        name = 'друг'
    
    greeting = f"""Привет, {name}! 👋

Этот таскер бот поможет держать твое ментальное состояние в балансе, повышая продуктивность и отслеживая рабочие и личные задачи.

Давай настроим время утреннего ритуала.
Укажи время в формате ЧЧ:ММ (например, 08:00)"""
    
    # Устанавливаем шаг онбординга
    await update_user_onboarding(user_id, "morning_time")
    
    await send_message(user_id, greeting)


async def handle_onboarding_message(user_id: int, text: str, user: dict):
    """Обработка сообщений в процессе онбординга"""
    step = user.get('onboarding_step', 'none')
    
    if step == "morning_time":
        # Ожидаем время утреннего ритуала
        if await validate_and_save_time(user_id, text, "morning"):
            await update_user_onboarding(user_id, "evening_time")
            await send_message(
                user_id,
                "✅ Отлично! Утренний ритуал настроен.\n\n"
                "Теперь давай настроим время вечернего ритуала.\n"
                "Укажи время в формате ЧЧ:ММ (например, 21:00)"
            )
        else:
            await send_message(
                user_id,
                "⚠️ Неверный формат времени.\n"
                "Пожалуйста, укажи время в формате ЧЧ:ММ (например, 08:00)"
            )
    
    elif step == "evening_time":
        # Ожидаем время вечернего ритуала
        if await validate_and_save_time(user_id, text, "evening"):
            await update_user_onboarding(user_id, "completed")
            await send_message(
                user_id,
                "✅ Отлично! Вечерний ритуал настроен.\n\n"
                "🎉 Настройка завершена!\n\n"
                "Я буду спрашивать о твоем самочувствии в указанное время.\n"
                "Используй /помощь чтобы узнать о доступных командах."
            )
        else:
            await send_message(
                user_id,
                "⚠️ Неверный формат времени.\n"
                "Пожалуйста, укажи время в формате ЧЧ:ММ (например, 21:00)"
            )


async def validate_and_save_time(user_id: int, time_str: str, ritual_type: str) -> bool:
    """Валидация и сохранение времени ритуала"""
    import re
    
    # Проверяем формат ЧЧ:ММ
    pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9])$'
    
    logger.info(f"🔍 Валидация времени: '{time_str}' для пользователя {user_id}")
    
    if not re.match(pattern, time_str):
        logger.warning(f"⚠️ Неверный формат времени: '{time_str}'")
        return False
    
    logger.info(f"✅ Формат времени корректен: '{time_str}'")
    
    try:
        await update_user_ritual_time(user_id, ritual_type, time_str)
        logger.info(f"✅ Время {ritual_type} сохранено: {time_str}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения времени: {e}")
        import traceback
        traceback.print_exc()
        return False


async def handle_mood_response(user_id: int, text: str):
    """Обработка ответа о самочувствии"""
    try:
        mood_level = int(text.strip())
        
        if 1 <= mood_level <= 7:
            # Определяем тип ритуала по времени пользователя
            user = await get_user(user_id)
            ritual_type = "morning"  # по умолчанию
            
            if user:
                current_time = datetime.now().time()
                morning_time = user.get('morning_ritual_time')
                evening_time = user.get('evening_ritual_time')
                
                # Определяем какой ритуал ближе по времени
                if morning_time and evening_time:
                    # Вычисляем разницу в минутах
                    current_minutes = current_time.hour * 60 + current_time.minute
                    morning_minutes = morning_time.hour * 60 + morning_time.minute
                    evening_minutes = evening_time.hour * 60 + evening_time.minute
                    
                    diff_morning = abs(current_minutes - morning_minutes)
                    diff_evening = abs(current_minutes - evening_minutes)
                    
                    # Если ближе к вечернему времени
                    if diff_evening < diff_morning:
                        ritual_type = "evening"
                elif evening_time:
                    ritual_type = "evening"
            
            await log_mood(user_id, mood_level, ritual_type)
            
            # Получаем описание из конфига
            mood_name = ritual_config.get_mood_description(mood_level)
            
            # Формируем ответное сообщение в зависимости от типа ритуала
            if ritual_type == "morning":
                # Используем специальные сообщения для утреннего ритуала в зависимости от уровня настроения
                greeting = ritual_config.get_morning_ritual_message(mood_level)
            else:
                greeting = ritual_config.get_evening_ritual_message(mood_level)
            
            await send_message(
                user_id,
                f"{greeting}"
            )
            return True
        else:
            await send_message(
                user_id,
                "⚠️ Пожалуйста, укажи число от 1 до 7"
            )
            return False
            
    except ValueError:
        return False


async def handle_help(user_id: int):
    """Обработчик команды /помощь - показать справку"""
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

🔄 /start
   Перезапустить настройку ритуалов

❓ /помощь
   Показать эту справку
    """.strip()
    
    await send_message(user_id, help_text)


async def handle_unknown_command(user_id: int):
    """Обработчик неизвестных команд"""
    await send_message(
        user_id,
        "⚠️ Неизвестная команда\n"
        "Используйте /помощь для просмотра доступных команд"
    )


# ========== Ritual Scheduler ==========

async def send_ritual_to_user(user_id: int, ritual_type: str):
    """
    Отправить ритуал пользователю
    
    Args:
        user_id: ID пользователя
        ritual_type: 'morning' или 'evening'
    """
    try:
        logger.info(f"🌅 Отправка {ritual_type} ритуала пользователю {user_id}")
        
        # Получаем конфигурацию ритуала
        ritual = ritual_config.get_ritual_config(ritual_type)
        text = ritual["text"]
        image_path = ritual["image_path"]
        
        # Добавляем инструкцию к тексту
        full_text = f"{text}\n\n{ritual_config.MOOD_INSTRUCTION}"
        
        # Отправляем сообщение с изображением
        success = await send_message_with_image(user_id, full_text, image_path)
        
        if success:
            logger.info(f"✅ Ритуал {ritual_type} отправлен пользователю {user_id}")
        else:
            logger.error(f"❌ Не удалось отправить ритуал {ritual_type} пользователю {user_id}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке ритуала: {e}")
        import traceback
        traceback.print_exc()


async def check_and_send_rituals():
    """
    Проверить время и отправить ритуалы всем пользователям
    Эта функция вызывается планировщиком каждую минуту
    """
    try:
        current_time = datetime.now().time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        logger.info(f"🕐 Проверка ритуалов: {current_hour:02d}:{current_minute:02d}")
        
        # Получаем всех пользователей с настроенными ритуалами
        async with db_pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT max_user_id, morning_ritual_time, evening_ritual_time 
                FROM users 
                WHERE onboarding_step = 'completed'
                  AND (morning_ritual_time IS NOT NULL OR evening_ritual_time IS NOT NULL)
            """)
        
        for user in users:
            user_id = user['max_user_id']
            morning_time = user['morning_ritual_time']
            evening_time = user['evening_ritual_time']
            
            # Проверяем утренний ритуал
            if morning_time and morning_time.hour == current_hour and morning_time.minute == current_minute:
                logger.info(f"🌅 Время утреннего ритуала для пользователя {user_id}")
                await send_ritual_to_user(user_id, "morning")
            
            # Проверяем вечерний ритуал
            if evening_time and evening_time.hour == current_hour and evening_time.minute == current_minute:
                logger.info(f"🌙 Время вечернего ритуала для пользователя {user_id}")
                await send_ritual_to_user(user_id, "evening")
                
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке ритуалов: {e}")
        import traceback
        traceback.print_exc()


async def init_scheduler():
    """Инициализация планировщика ритуалов"""
    global scheduler
    
    try:
        scheduler = AsyncIOScheduler()
        
        # Добавляем задачу проверки ритуалов каждую минуту
        scheduler.add_job(
            check_and_send_rituals,
            CronTrigger(second=0),  # Запускать в начале каждой минуты
            id='ritual_checker',
            name='Проверка и отправка ритуалов',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Планировщик ритуалов запущен (проверка каждую минуту)")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации планировщика: {e}")
        import traceback
        traceback.print_exc()


async def shutdown_scheduler():
    """Остановка планировщика"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("❌ Планировщик ритуалов остановлен")


# ========== Long Polling ==========

async def get_updates(offset: int = 0, timeout: int = 60):
    """Получить обновления от MAX API
    
    Возвращает: (updates, marker)
    """
    try:
        url = f"{BASE_URL}/updates"
        params = {
            "timeout": timeout
        }
        
        # Добавляем marker только если он есть
        if offset > 0:
            params["marker"] = offset
        
        response = await http_client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"🔍 DEBUG: Полный ответ API: {data}")
            updates = data.get("updates", [])
            marker = data.get("marker", offset)
            logger.info(f"🔍 DEBUG: Количество updates: {len(updates)}, marker: {marker}")
            return updates, marker
        else:
            logger.error(f"❌ Ошибка получения обновлений: {response.status_code}")
            logger.error(f"Ответ: {response.text}")
            return [], offset
            
    except httpx.TimeoutException:
        # Timeout - это нормально для long polling
        return [], offset
    except Exception as e:
        logger.error(f"❌ Ошибка при получении обновлений: {e}")
        return [], offset


async def process_message(message: Dict[str, Any]):
    """Обработать полученное сообщение"""
    try:
        # Извлекаем текст сообщения
        logger.info(f"🔍 DEBUG: Структура message: {message}")
        
        text = message.get("body", {}).get("text", "").strip()
        logger.info(f"🔍 DEBUG: Извлечённый текст: '{text}'")
        
        if not text:
            logger.warning(f"⚠️ Пустой текст сообщения")
            return
        
        # Извлекаем user_id, chat_id и имя пользователя
        user_id, chat_id = extract_user_and_chat_id(message)
        sender = message.get("sender", {})
        first_name = sender.get("first_name", "")
        last_name = sender.get("last_name", "")
        
        logger.info(f"🔍 DEBUG: user_id={user_id}, chat_id={chat_id}, name={first_name}")
        logger.info(f"📨 Получено сообщение от {user_id}: {text[:50]}")
        
        # Получаем пользователя для проверки состояния онбординга
        user = await get_user(user_id)
        
        # Если пользователь не найден или не прошел онбординг - обрабатываем /start
        if text == '/start':
            await handle_start(user_id, first_name, last_name)
            return
        
        # Если пользователь в процессе онбординга
        if user and user.get('onboarding_step') not in ['none', 'completed']:
            await handle_onboarding_message(user_id, text, user)
            return
        
        # Маршрутизация команд
        if text == '/задачи':
            await handle_list_tasks(user_id, chat_id)
        elif text.startswith('/готово'):
            await handle_complete_task(user_id, chat_id, text)
        elif text.startswith('/создать'):
            await handle_create_task(user_id, chat_id, text)
        elif text == '/помощь' or text == '/help':
            await handle_help(user_id)
        elif text.startswith('/'):
            # Неизвестная команда
            await handle_unknown_command(user_id)
        else:
            # Обычное сообщение - может быть ответом на вопрос о самочувствии
            # Пробуем обработать как цифру (ответ на ритуал)
            if text.isdigit():
                handled = await handle_mood_response(user_id, text)
                if not handled:
                    # Не удалось обработать как настроение
                    pass
            # Игнорируем остальные обычные сообщения
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке сообщения: {e}")
        import traceback
        traceback.print_exc()


async def process_update(update: Dict[str, Any]):
    """Обработать одно обновление"""
    try:
        # Логируем структуру обновления для отладки
        logger.info(f"🔍 DEBUG: Обновление: {update}")
        
        # MAX API использует "update_type", а не "type"
        update_type = update.get("update_type")
        logger.info(f"🔍 DEBUG: Тип обновления: {update_type}")
        
        if update_type == "message_created":
            message = update.get("message", {})
            logger.info(f"🔍 DEBUG: Сообщение: {message}")
            await process_message(message)
        elif update_type == "bot_started":
            # Кто-то запустил бота - начинаем онбординг
            user_id = update.get("user_id")
            user_data = update.get("user", {})
            first_name = user_data.get("first_name", "")
            last_name = user_data.get("last_name", "")
            
            logger.info(f"👋 Пользователь {user_id} запустил бота")
            if user_id:
                await handle_start(user_id, first_name, last_name)
        else:
            logger.warning(f"⚠️ Неизвестный тип обновления: {update_type}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке обновления: {e}")
        import traceback
        traceback.print_exc()


async def long_polling_loop():
    """Основной цикл long polling"""
    
    logger.info("📡 Запуск long polling...")
    
    # MAX API использует marker для отслеживания позиции
    last_marker = 0
    
    while True:
        try:
            # Получаем обновления и новый marker
            updates, new_marker = await get_updates(offset=last_marker, timeout=60)
            
            # Обновляем marker
            last_marker = new_marker
            
            if updates:
                logger.info(f"📬 Получено {len(updates)} обновлений")
                
                for update in updates:
                    # Обрабатываем обновление
                    await process_update(update)
            
            # Небольшая задержка между запросами (если не было обновлений)
            if not updates:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("⏹️  Получен сигнал остановки")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка в long polling: {e}")
            # Ждем перед повторной попыткой
            await asyncio.sleep(5)


# ========== Main ==========

async def main():
    """Основная функция запуска бота"""
    logger.info("🚀 Запуск MAX Bot с Long Polling...")
    
    try:
        # Инициализация
        await init_db_pool()
        await init_http_client()
        await init_scheduler()
        
        # Запускаем long polling
        await long_polling_loop()
        
    except KeyboardInterrupt:
        logger.info("⏹️  Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Закрываем соединения
        await shutdown_scheduler()
        await close_http_client()
        await close_db_pool()
        logger.info("👋 Бот остановлен")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 До свидания!")

