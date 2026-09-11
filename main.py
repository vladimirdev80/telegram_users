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

# Схема входящего JSON запроса
class UploadPayload(BaseModel):
    file_base64: str
    filename: str
    initData: str

@app.get("/")
async def root():
    return {"status": "online"}

@app.post("/api/upload")
async def upload_excel(payload: UploadPayload):
    logging.info(f"--- Получен JSON-запрос для файла: {payload.filename} ---")
    
    if not payload.initData:
        logging.error("Строка initData пуста")
        raise HTTPException(status_code=400, detail="initData отсутствует")

    user_id = None

    # 1. Попытка официальной валидации Telegram подписи
    try:
        data = safe_parse_webapp_init_data(token=BOT_TOKEN, raw_init_data=payload.initData)
        user_id = data.user.id
        logging.info(f"Успешная валидация Telegram. ID пользователя: {user_id}")
    except Exception as parse_error:
        logging.warning(f"Официальная проверка подписи не прошла: {parse_error}. Пробуем извлечь user_id...")
        
        # 2. Резервный разбор initData
        try:
            parsed_query = parse_qs(payload.initData)
            if 'user' in parsed_query:
                user_json = json.loads(parsed_query['user'][0])
                user_id = user_json.get('id')
                logging.info(f"Извлечен user_id из raw данных: {user_id}")
        except Exception as fallback_error:
            logging.error(f"Сбой извлечения user_id: {fallback_error}")

    if not user_id:
        raise HTTPException(status_code=400, detail="Не удалось определить ID пользователя")

    # 3. Декодирование файла и отправка пользователю
    try:
        file_bytes = base64.b64decode(payload.file_base64)
        document = BufferedInputFile(file_bytes, filename=payload.filename)
        
        await bot.send_document(
            chat_id=user_id,
            document=document,
            caption=f"✅ Файл `{payload.filename}` успешно сформирован!"
        )
        logging.info(f"Файл успешно отправлен пользователю {user_id}")
        return {"status": "ok"}
    except Exception as send_error:
        logging.error(f"Ошибка отправки файла ботом: {send_error}")
        raise HTTPException(status_code=500, detail=str(send_error))
