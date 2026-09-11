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
    initData: str = ""

@app.get("/")
async def root():
    return {"status": "online"}

@app.post("/api/upload")
async def upload_excel(payload: UploadPayload):
    logging.info(f"--- POST запрос от клиента. Длина initData: {len(payload.initData)} ---")
    
    user_id = None

    # 1. Если initData передан — валидируем или парсим
    if payload.initData:
        try:
            data = safe_parse_webapp_init_data(token=BOT_TOKEN, raw_init_data=payload.initData)
            user_id = data.user.id
            logging.info(f"Валидация успешна. user_id: {user_id}")
        except Exception as parse_error:
            logging.warning(f"Ошибка safe_parse: {parse_error}. Пробуем распарсить raw string...")
            try:
                parsed = parse_qs(payload.initData)
                if 'user' in parsed:
                    user_id = json.loads(parsed['user'][0]).get('id')
            except Exception as e:
                logging.error(f"Не удалось распарсить raw initData: {e}")

    # 2. Если user_id всё ещё не найден (например, открыто вне Telegram)
    if not user_id:
        error_msg = "Ошибка: initData пуст или не содержит user_id. Приложение открыто вне Telegram?"
        logging.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    # 3. Декодирование и отправка в бот
    try:
        file_bytes = base64.b64decode(payload.file_base64)
        document = BufferedInputFile(file_bytes, filename=payload.filename)
        
        await bot.send_document(
            chat_id=user_id,
            document=document,
            caption=f"✅ Файл `{payload.filename}` успешно сгенерирован!"
        )
        return {"status": "ok"}
    except Exception as send_error:
        logging.error(f"Ошибка отправки через Telegram Bot API: {send_error}")
        raise HTTPException(status_code=500, detail=str(send_error))
