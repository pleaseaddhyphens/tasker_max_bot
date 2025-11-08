# import requests

# # Отправка сообщения
# response = requests.post(
#     "http://localhost:8000/send_message",
#     json={
#         "user_id": 94717924,
#         "text": "Привет!",
#         "notify": True
#     }
# )

# print(response.json())

import httpx
import asyncio

async def send_message():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/send_message",
            json={
                "user_id": 94717924,
                "text": "Привет!",
                "notify": True
            }
        )
        print(response.json())

asyncio.run(send_message())