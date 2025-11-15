from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from typing import Optional, List
from datetime import datetime
import asyncpg
import os
from contextlib import asynccontextmanager

# Конфигурация базы данных
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://tasker_user:tasker_password@localhost:5432/tasker"
)

# Пул соединений с БД
db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global db_pool
    # Startup: создаем пул соединений
    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=60
    )
    print("✅ База данных подключена")
    yield
    # Shutdown: закрываем пул соединений
    await db_pool.close()
    print("❌ База данных отключена")


app = FastAPI(title="MAX Bot API with Database", lifespan=lifespan)

# Конфигурация MAX Bot API
ACCESS_TOKEN = "f9LHodD0cOLy---sDc0u5izFP25VAGQm2DBuG1SlbyEza4x4iCCKzzx2B2dAeDpdDawHn3hoFWKGl3CVMffI"
BASE_URL = "https://dev.max.ru/docs"


# ========== Pydantic Models ==========

class SendMessageRequest(BaseModel):
    user_id: int
    text: str
    notify: bool = True
    disable_link_preview: Optional[bool] = None


class SendMessageResponse(BaseModel):
    success: bool
    message: dict
    error: Optional[str] = None


class CreateTaskRequest(BaseModel):
    """Модель для создания задачи"""
    chat_id: str  # max_chat_id
    creator_id: int
    title: str
    description: Optional[str] = None
    tag: Optional[str] = None
    assignee_id: Optional[int] = None
    deadline: Optional[datetime] = None
    reminder_at: Optional[datetime] = None


class TaskResponse(BaseModel):
    """Модель ответа с информацией о задаче"""
    id: int
    chat_id: int
    creator_id: int
    assignee_id: Optional[int]
    title: str
    description: Optional[str]
    tag: Optional[str]
    status: str
    created_at: datetime
    deadline: Optional[datetime]
    reminder_at: Optional[datetime]
    completed_at: Optional[datetime]


class UpdateTaskStatusRequest(BaseModel):
    """Модель для обновления статуса задачи"""
    status: str  # active, completed, archived


class SendTasksToUserRequest(BaseModel):
    """Модель для отправки задач пользователю"""
    user_id: int
    chat_id: str
    notify: bool = True


# ========== Database Functions ==========

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


async def create_task_in_db(task_data: CreateTaskRequest) -> int:
    """Создать задачу в базе данных"""
    # Получаем или создаем чат
    chat_id = await get_or_create_chat(task_data.chat_id)
    
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO tasks (
                chat_id, creator_id, assignee_id, title, description,
                tag, deadline, reminder_at, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active')
            RETURNING id
        """,
            chat_id,
            task_data.creator_id,
            task_data.assignee_id,
            task_data.title,
            task_data.description,
            task_data.tag,
            task_data.deadline,
            task_data.reminder_at
        )
        return row['id']


async def get_task_by_id(task_id: int) -> Optional[dict]:
    """Получить задачу по ID"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                t.id, t.chat_id, t.creator_id, t.assignee_id,
                t.title, t.description, t.tag, t.status,
                t.created_at, t.deadline, t.reminder_at, t.completed_at
            FROM tasks t
            WHERE t.id = $1
        """, task_id)
        
        if row:
            return dict(row)
        return None


async def get_active_tasks(chat_id: str) -> List[dict]:
    """Получить все активные задачи чата"""
    chat_db_id = await get_or_create_chat(chat_id)
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                t.id, t.chat_id, t.creator_id, t.assignee_id,
                t.title, t.description, t.tag, t.status,
                t.created_at, t.deadline, t.reminder_at, t.completed_at
            FROM tasks t
            WHERE t.chat_id = $1 AND t.status = 'active'
            ORDER BY t.deadline ASC NULLS LAST, t.created_at DESC
        """, chat_db_id)
        
        return [dict(row) for row in rows]


async def update_task_status(task_id: int, status: str) -> bool:
    """Обновить статус задачи"""
    async with db_pool.acquire() as conn:
        completed_at = datetime.now() if status == 'completed' else None
        
        result = await conn.execute("""
            UPDATE tasks 
            SET status = $1, completed_at = $2
            WHERE id = $3
        """, status, completed_at, task_id)
        
        return result == "UPDATE 1"


async def get_archived_tasks(chat_id: str) -> List[dict]:
    """Получить архивированные задачи чата"""
    chat_db_id = await get_or_create_chat(chat_id)
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                t.id, t.chat_id, t.creator_id, t.assignee_id,
                t.title, t.description, t.tag, t.status,
                t.created_at, t.deadline, t.reminder_at, t.completed_at
            FROM tasks t
            WHERE t.chat_id = $1 AND t.status IN ('completed', 'archived')
            ORDER BY t.completed_at DESC NULLS LAST, t.created_at DESC
        """, chat_db_id)
        
        return [dict(row) for row in rows]


# ========== Helper Functions ==========

def format_tasks_message(tasks: List[dict]) -> str:
    """Форматировать список задач в красивое сообщение"""
    if not tasks:
        return "📝 Активных задач нет"
    
    message = f"📋 Активные задачи ({len(tasks)}):\n\n"
    
    for i, task in enumerate(tasks, 1):
        # Заголовок задачи
        message += f"{i}. {task['title']}\n"
        
        # Тег
        if task['tag']:
            message += f"   🏷️ {task['tag']}\n"
        
        # Описание
        if task['description']:
            desc = task['description'][:100] + "..." if len(task['description']) > 100 else task['description']
            message += f"   📄 {desc}\n"
        
        # Исполнитель
        if task['assignee_id']:
            message += f"   👤 Исполнитель: {task['assignee_id']}\n"
        
        # Дедлайн
        if task['deadline']:
            deadline_str = task['deadline'].strftime("%d.%m.%Y %H:%M")
            message += f"   ⏰ Дедлайн: {deadline_str}\n"
        
        message += "\n"
    
    return message.strip()


# ========== MAX Bot API Endpoints ==========

@app.post("/send_message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """Отправка сообщения пользователю через MAX Bot API"""
    url = f"{BASE_URL}/messages"
    headers = {
        "Authorization": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    params = {"user_id": request.user_id}
    if request.disable_link_preview is not None:
        params["disable_link_preview"] = request.disable_link_preview
    
    payload = {
        "text": request.text,
        "notify": request.notify
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return SendMessageResponse(
                    success=True,
                    message=response.json()
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ошибка API: {response.text}"
                )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка соединения: {str(e)}"
        )


@app.post("/send_tasks_to_user")
async def send_tasks_to_user(request: SendTasksToUserRequest):
    """
    Отправить список активных задач пользователю в MAX
    
    Пример запроса:
    ```json
    {
        "user_id": 94717924,
        "chat_id": "123",
        "notify": true
    }
    ```
    """
    try:
        # Получаем активные задачи
        tasks = await get_active_tasks(request.chat_id)
        
        # Форматируем сообщение
        message_text = format_tasks_message(tasks)
        
        # Отправляем сообщение пользователю
        message_request = SendMessageRequest(
            user_id=request.user_id,
            text=message_text,
            notify=request.notify
        )
        
        result = await send_message(message_request)
        
        return {
            "success": True,
            "tasks_count": len(tasks),
            "message_sent": result.success,
            "message": message_text
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при отправке задач: {str(e)}"
        )


@app.get("/send_tasks_to_user/{user_id}/{chat_id}")
async def send_tasks_to_user_simple(user_id: int, chat_id: str):
    """
    Упрощенный endpoint для отправки задач через GET запрос
    
    Пример: /send_tasks_to_user/94717924/123
    """
    request = SendTasksToUserRequest(
        user_id=user_id,
        chat_id=chat_id,
        notify=True
    )
    return await send_tasks_to_user(request)


# ========== Task Management Endpoints ==========

@app.post("/tasks", response_model=TaskResponse)
async def create_task(task: CreateTaskRequest):
    """
    Создать новую задачу в БД
    
    Пример запроса:
    ```json
    {
        "chat_id": "123456",
        "creator_id": 94717924,
        "title": "Написать документацию",
        "description": "Нужно описать все API endpoints",
        "tag": "документация",
        "assignee_id": 94717924,
        "deadline": "2025-11-15T18:00:00",
        "reminder_at": "2025-11-14T18:00:00"
    }
    ```
    """
    try:
        task_id = await create_task_in_db(task)
        task_data = await get_task_by_id(task_id)
        
        if not task_data:
            raise HTTPException(status_code=500, detail="Не удалось создать задачу")
        
        return TaskResponse(**task_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании задачи: {str(e)}")


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """Получить задачу по ID"""
    task = await get_task_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return TaskResponse(**task)


@app.get("/chats/{chat_id}/tasks", response_model=List[TaskResponse])
async def get_chat_tasks(chat_id: str):
    """Получить все активные задачи чата"""
    tasks = await get_active_tasks(chat_id)
    return [TaskResponse(**task) for task in tasks]


@app.get("/chats/{chat_id}/archive", response_model=List[TaskResponse])
async def get_chat_archive(chat_id: str):
    """Получить архив выполненных задач чата"""
    tasks = await get_archived_tasks(chat_id)
    return [TaskResponse(**task) for task in tasks]


@app.patch("/tasks/{task_id}/status")
async def update_status(task_id: int, request: UpdateTaskStatusRequest):
    """
    Обновить статус задачи
    
    Доступные статусы:
    - active: активная задача
    - completed: выполненная задача
    - archived: архивированная задача
    """
    if request.status not in ['active', 'completed', 'archived']:
        raise HTTPException(
            status_code=400,
            detail="Недопустимый статус. Используйте: active, completed, archived"
        )
    
    success = await update_task_status(task_id, request.status)
    
    if not success:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = await get_task_by_id(task_id)
    return TaskResponse(**task)


# ========== Simple Test Endpoints ==========

@app.get("/send_simple_message")
async def send_simple_message():
    """Простой эндпоинт для быстрой отправки сообщения"""
    request = SendMessageRequest(
        user_id=94717924,
        text="Привет"
    )
    return await send_message(request)


@app.post("/tasks/quick_create")
async def quick_create_task(
    chat_id: str,
    creator_id: int,
    title: str,
    description: str = "",
    tag: str = ""
):
    """
    Упрощенный endpoint для быстрого создания задачи
    
    Пример: /tasks/quick_create?chat_id=123&creator_id=94717924&title=Test&description=Desc&tag=important
    """
    task = CreateTaskRequest(
        chat_id=chat_id,
        creator_id=creator_id,
        title=title,
        description=description if description else None,
        tag=tag if tag else None
    )
    
    return await create_task(task)


@app.get("/")
async def root():
    """Корневой эндпоинт с описанием API"""
    return {
        "message": "MAX Bot API with Database",
        "version": "1.0.0",
        "endpoints": {
            "messages": {
                "POST /send_message": "Отправить сообщение с параметрами",
                "GET /send_simple_message": "Отправить 'Привет' пользователю 94717924",
                "POST /send_tasks_to_user": "Отправить список задач пользователю",
                "GET /send_tasks_to_user/{user_id}/{chat_id}": "Отправить задачи (упрощенный)"
            },
            "tasks": {
                "POST /tasks": "Создать новую задачу",
                "GET /tasks/{task_id}": "Получить задачу по ID",
                "GET /chats/{chat_id}/tasks": "Получить активные задачи чата",
                "GET /chats/{chat_id}/archive": "Получить архив выполненных задач",
                "PATCH /tasks/{task_id}/status": "Обновить статус задачи",
                "POST /tasks/quick_create": "Быстро создать задачу (упрощенный)"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)