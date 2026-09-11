import base64
import os
import json
import logging
from urllib.parse import parse_qs
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.utils.web_app import safe_parse_webapp_init_data

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UploadPayload(BaseModel):
    file_base64: str
    filename: str
    initData: str

@app.get("/")
async def root():
    return {"status": "online"}

@app.post("/api/upload")
async def upload_excel(payload: UploadPayload):
    logging.info(f"--- Получен JSON запрос: {payload.filename} ---")
    
    user_id = None

    # Валидация / извлечение user_id
    if payload.initData:
        try:
            data = safe_parse_webapp_init_data(token=BOT_TOKEN, raw_init_data=payload.initData)
            user_id = data.user.id
        except Exception:
            try:
                parsed = parse_qs(payload.initData)
                if 'user' in parsed:
                    user_id = json.loads(parsed['user'][0]).get('id')
            except Exception:
                pass

    if not user_id:
        raise HTTPException(status_code=400, detail="Не удалось определить user_id")

    # Декодирование файла из Base64 и отправка
    try:
        file_bytes = base64.b64decode(payload.file_base64)
        document = BufferedInputFile(file_bytes, filename=payload.filename)
        
        await bot.send_document(
            chat_id=user_id,
            document=document,
            caption=f"✅ Файл `{payload.filename}` успешно сформирован!"
        )
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
        raise HTTPException(status_code=500, detail=str(e))
