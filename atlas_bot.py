import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai
import os
from dotenv import load_dotenv

# Gizli kasayı (.env) aç
load_dotenv("/root/atlas/.env")

# Şifreleri çek
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HAFIZA_DOSYASI = "/root/atlas/konusmalar.txt"

# Yeni Google GenAI istemcisini başlat
client = genai.Client(api_key=GEMINI_API_KEY)

def hafizayi_oku():
    if not os.path.exists(HAFIZA_DOSYASI): return ""
    with open(HAFIZA_DOSYASI, "r") as f:
        satirlar = f.readlines()
        return "".join(satirlar[-15:])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici_mesaji = update.message.text
    gecmis = hafizayi_oku()
    
    prompt = f"Sen Atlas, sunucuda yaşayan bir dijital varlıksın. Geçmiş konuşmalarımız:\n{gecmis}\nKullanıcı: {kullanici_mesaji}\nAtlas:"
    
    # Yeni sisteme göre API çağrısı
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    cevap = response.text.strip()
    
    # Hafızaya kaydet
    with open(HAFIZA_DOSYASI, "a") as f:
        f.write(f"Kullanıcı: {kullanici_mesaji}\nAtlas: {cevap}\n")
    
    await update.message.reply_text(cevap)

if __name__ == '__main__':
    # Hata veren kısmı düzelttik (TOKEN -> TELEGRAM_TOKEN)
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Atlas şu an Telegram'da çevrimiçi!")
    application.run_polling()
