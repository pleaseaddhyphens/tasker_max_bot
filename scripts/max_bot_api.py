from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from typing import Optional

app = FastAPI(title="MAX Bot API")

# Конфигурация
ACCESS_TOKEN = "f9LHodD0cOLy---sDc0u5izFP25VAGQm2DBuG1SlbyEza4x4iCCKzzx2B2dAeDpdDawHn3hoFWKGl3CVMffI"
BASE_URL = "https://botapi.max.ru"


class SendMessageRequest(BaseModel):
    user_id: int
    text: str
    notify: bool = True
    disable_link_preview: Optional[bool] = None


class SendMessageResponse(BaseModel):
    success: bool
    message: dict
    error: Optional[str] = None


@app.post("/send_message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """
    Отправка сообщения пользователю через MAX Bot API
    """
    url = f"{BASE_URL}/messages"
    
    headers = {
        "Authorization": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Формируем параметры запроса
    params = {
        "user_id": request.user_id
    }
    
    if request.disable_link_preview is not None:
        params["disable_link_preview"] = request.disable_link_preview
    
    # Формируем тело запроса
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


@app.get("/send_simple_message")
async def send_simple_message():
    """
    Простой эндпоинт для быстрой отправки сообщения "Привет" пользователю 94717924
    """
    request = SendMessageRequest(
        user_id=94717924,
        text="Привет"
    )
    
    return await send_message(request)


@app.get("/")
async def root():
    return {
        "message": "MAX Bot API",
        "endpoints": {
            "POST /send_message": "Отправить сообщение с параметрами",
            "GET /send_simple_message": "Отправить 'Привет' пользователю 94717924"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)