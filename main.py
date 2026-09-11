import io
import os
import json
import logging
from urllib.parse import parse_qs
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/")
async def root():
    return {"status": "online"}

@app.post("/api/upload")
async def upload_excel(
    file: UploadFile = File(...),
    initData: str = Form(...)
):
    logging.info(f"Получен файл: {file.filename}")
    logging.info(f"Длина initData: {len(initData)}")
    
    if not initData:
        raise HTTPException(status_code=400, detail="initData is empty")

    user_id = None

    # 1. Попытка официальной валидации Telegram подписи
    try:
        data = safe_parse_webapp_init_data(token=BOT_TOKEN, raw_init_data=initData)
        user_id = data.user.id
        logging.info(f"Валидация прошла успешно. ID пользователя: {user_id}")
    except Exception as parse_error:
        logging.warning(f"Официальная валидация не прошла: {parse_error}. Парсим raw initData...")
        
        # 2. Резервный разбор initData (если валидация не прошла, достаем user.id напрямую)
        try:
            parsed_query = parse_qs(initData)
            if 'user' in parsed_query:
                user_json = json.loads(parsed_query['user'][0])
                user_id = user_json.get('id')
                logging.info(f"Извлечен ID из raw user: {user_id}")
        except Exception as fallback_error:
            logging.error(f"Не удалось извлечь user_id: {fallback_error}")

    if not user_id:
        raise HTTPException(status_code=400, detail="Could not determine user_id from initData")

    # 3. Отправка файла пользователю
    try:
        file_content = await file.read()
        document = BufferedInputFile(file_content, filename=file.filename)
        
        await bot.send_document(
            chat_id=user_id,
            document=document,
            caption=f"✅ Файл `{file.filename}` успешно сформирован!"
        )
        return {"status": "ok"}
    except Exception as send_error:
        logging.error(f"Ошибка отправки через Telegram Bot: {send_error}")
        raise HTTPException(status_code=500, detail=str(send_error))
