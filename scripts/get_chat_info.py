from fastapi import FastAPI, HTTPException
from typing import List, Optional, Dict, Any
import httpx

app = FastAPI(title="MAX Chat Participants API")

# Конфигурация
BASE_URL = "https://platform-api.max.ru"
ACCESS_TOKEN = "f9LHodD0cOLy---sDc0u5izFP25VAGQm2DBuG1SlbyEza4x4iCCKzzx2B2dAeDpdDawHn3hoFWKGl3CVMffI"
CHAT_ID = -68973305722340


@app.get("/")
async def root():
    """Корневой эндпоинт с информацией об API"""
    return {
        "message": "MAX Chat Participants API",
        "endpoints": {
            "docs": "/docs",
            "participants_ids": "/chat/{chat_id}/participants",
            "participants_full": "/chat/{chat_id}/members",
            "default_chat_ids": "/chat/default/participants",
            "default_chat_members": "/chat/default/members"
        },
        "example_chat_id": CHAT_ID
    }


@app.get("/chat/{chat_id}/participants", response_model=List[int])
async def get_chat_participant_ids(chat_id: int):
    """
    Получить только ID участников чата
    
    Args:
        chat_id: ID чата
        
    Returns:
        Список ID участников чата
    """
    url = f"{BASE_URL}/chats/{chat_id}/members"
    headers = {"Authorization": ACCESS_TOKEN}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            members = data.get("members", [])
            
            # Извлекаем только user_id
            participant_ids = [member["user_id"] for member in members]
            
            return participant_ids
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка API: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )


@app.get("/chat/{chat_id}/members")
async def get_chat_members_full(chat_id: int):
    """
    Получить полную информацию об участниках чата
    
    Args:
        chat_id: ID чата
        
    Returns:
        Полная информация об участниках (ID, имена, роли, время активности и т.д.)
    """
    url = f"{BASE_URL}/chats/{chat_id}/members"
    headers = {"Authorization": ACCESS_TOKEN}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка API: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )


@app.get("/chat/default/participants", response_model=List[int])
async def get_default_chat_participant_ids():
    """
    Получить ID участников чата по умолчанию (chat_id=-68973305722340)
    
    Returns:
        Список ID участников
    """
    return await get_chat_participant_ids(CHAT_ID)


@app.get("/chat/default/members")
async def get_default_chat_members_full():
    """
    Получить полную информацию об участниках чата по умолчанию
    
    Returns:
        Полная информация об участниках
    """
    return await get_chat_members_full(CHAT_ID)


@app.get("/chat/{chat_id}/members/admins")
async def get_chat_admins(chat_id: int):
    """
    Получить только администраторов чата
    
    Args:
        chat_id: ID чата
        
    Returns:
        Список администраторов
    """
    url = f"{BASE_URL}/chats/{chat_id}/members"
    headers = {"Authorization": ACCESS_TOKEN}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            members = data.get("members", [])
            
            # Фильтруем только администраторов
            admins = [
                member for member in members 
                if member.get("is_admin") or member.get("is_owner")
            ]
            
            return {
                "chat_id": chat_id,
                "admins_count": len(admins),
                "admins": admins
            }
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка API: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )


@app.get("/chat/{chat_id}/members/bots")
async def get_chat_bots(chat_id: int):
    """
    Получить только ботов в чате
    
    Args:
        chat_id: ID чата
        
    Returns:
        Список ботов
    """
    url = f"{BASE_URL}/chats/{chat_id}/members"
    headers = {"Authorization": ACCESS_TOKEN}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            members = data.get("members", [])
            
            # Фильтруем только ботов
            bots = [member for member in members if member.get("is_bot")]
            
            return {
                "chat_id": chat_id,
                "bots_count": len(bots),
                "bots": bots
            }
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка API: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)