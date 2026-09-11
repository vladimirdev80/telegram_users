import io
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.utils.init_data import safe_parse_webapp_init_data

# Токен рекомендуется брать из переменных окружения (Environment Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8918854648:AAHA3xvclAe0-Q51PI-Qf9M9m9NezzHWnmM")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

@app.post("/api/upload")
async def upload_excel(
    file: UploadFile = File(...),
    initData: str = Form(...)
):
    try:
        # Валидация подписи initData из Telegram
        data = safe_parse_webapp_init_data(token=BOT_TOKEN, raw_init_data=initData)
        user_id = data.user.id
        
        # Чтение содержимого файла
        file_content = await file.read()
        document = BufferedInputFile(file_content, filename=file.filename)
        
        # Отправка Excel-файла в чат пользователя
        await bot.send_document(
            chat_id=user_id,
            document=document,
            caption=f"✅ Файл с пользователями `{file.filename}` успешно сгенерирован!"
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))