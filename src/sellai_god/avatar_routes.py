from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import httpx
import re

router = APIRouter()

class MessageCreate(BaseModel):
    content: str

def _detect_language(text: str) -> str:
    if re.search(r'[\u4e00-\u9fff]', text):
        return "zh"
    return "en"

@router.post("/avatars/{avatar_id}/messages")
async def send_message(avatar_id: str, body: MessageCreate):
    lang = _detect_language(body.content)
    system_prompt = "你是 SellAI，专业的电商 AI 合伙人。回复要详细、专业、有数据支撑。"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('BAILIAN_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-plus",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": body.content}
                    ]
                }
            )
            print("STATUS:", response.status_code)
            print("TEXT:", response.text)
            result = response.json()
            reply = result["choices"][0]["message"]["content"]
    except Exception as e:
        reply = f"AI服务暂时不可用: {str(e)}"
    
    return {"reply": reply, "role": "assistant", "detected_lang": lang}

@router.get("/avatars")
async def list_avatars():
    return {"avatars": []}

@router.post("/avatars")
async def create_avatar(name: str, personality: str = "通用"):
    return {"id": "1", "name": name, "personality": personality}
