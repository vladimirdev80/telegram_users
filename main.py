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
    file: UploadFile = File(None),
    initData: str = Form(None)
):
    logging.info("--- Новый входящий POST запрос ---")
    
    if not file:
        logging.error("Файл не был передан в запросе")
        raise HTTPException(status_code=400, detail="Файл отсутствует")
        
    logging.info(f"Имя полученного файла: {file.filename}")

    if not initData:
        logging.error("Поле initData отсутствует или пустое")
        raise HTTPException(status_code=400, detail="initData отсутствует")

    user_id = None

    # 1. Попытка официальной валидации Telegram подписи
    try:
        data = safe_parse_webapp_init_data(token=BOT_TOKEN, raw_init_data=initData)
        user_id = data.user.id
        logging.info(f"Успешная валидация Telegram. ID: {user_id}")
    except Exception as parse_error:
        logging.warning(f"Официальная валидация сбойнула: {parse_error}. Пробуем извлечь user_id из raw данных...")
        
        # 2. Резервный разбор initData
        try:
            parsed_query = parse_qs(initData)
            if 'user' in parsed_query:
                user_json = json.loads(parsed_query['user'][0])
                user_id = user_json.get('id')
                logging.info(f"Извлечен user_id из сырого json: {user_id}")
        except Exception as fallback_error:
            logging.error(f"Сбой резервного разбора: {fallback_error}")

    if not user_id:
        logging.error("Не удалось определить user_id ни одним из способов")
        raise HTTPException(status_code=400, detail="Не удалось определить ID пользователя")

    # 3. Отправка документа пользователю
    try:
        file_content = await file.read()
        document = BufferedInputFile(file_content, filename=file.filename)
        
        await bot.send_document(
            chat_id=user_id,
            document=document,
            caption=f"✅ Файл с пользователями `{file.filename}` успешно сгенерирован!"
        )
        logging.info(f"Файл успешно отправлен пользователю {user_id}")
        return {"status": "ok"}
    except Exception as send_error:
        logging.error(f"Ошибка отправки файла ботом: {send_error}")
        raise HTTPException(status_code=500, detail=str(send_error))
