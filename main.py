import io
import os
import logging
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
    logging.info(f"Получен запрос на загрузку файла: {file.filename}")
    
    if not initData:
        logging.error("initData пустая")
        raise HTTPException(status_code=400, detail="initData field is missing")

    try:
        # Валидация подписи Telegram WebApp
        data = safe_parse_webapp_init_data(token=BOT_TOKEN, raw_init_data=initData)
        user_id = data.user.id
        logging.info(f"Успешная валидация пользователя Telegram ID: {user_id}")
    except Exception as e:
        logging.error(f"Ошибка проверки initData: {str(e)}")
        # Возвращаем понятную причину ошибки клиенту
        raise HTTPException(status_code=400, detail=f"Telegram validation failed: {str(e)}")

    try:
        file_content = await file.read()
        document = BufferedInputFile(file_content, filename=file.filename)
        
        await bot.send_document(
            chat_id=user_id,
            document=document,
            caption=f"✅ Файл с пользователями `{file.filename}` успешно сгенерирован!"
        )
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Ошибка при отправке файла через бота: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bot send error: {str(e)}")
