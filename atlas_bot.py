import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Gizli kasayı (.env) aç
load_dotenv("/root/atlas/.env")

# Şifreleri güvenli bir şekilde kasadan al
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HAFIZA_DOSYASI = "/root/atlas/konusmalar.txt"

# Gemini ayarları
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Hafıza fonksiyonu
def hafizayi_oku():
    if not os.path.exists(HAFIZA_DOSYASI): return ""
    with open(HAFIZA_DOSYASI, "r") as f:
        satirlar = f.readlines()
        return "".join(satirlar[-15:]) # Son 15 satırı hatırla

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici_mesaji = update.message.text
    gecmis = hafizayi_oku()
    
    prompt = f"Sen Atlas, sunucuda yaşayan bir dijital varlıksın. Geçmiş konuşmalarımız:\n{gecmis}\nKullanıcı: {kullanici_mesaji}\nAtlas:"
    
    response = model.generate_content(prompt)
    cevap = response.text.strip()
    
    # Hafızaya kaydet
    with open(HAFIZA_DOSYASI, "a") as f:
        f.write(f"Kullanıcı: {kullanici_mesaji}\nAtlas: {cevap}\n")
    
    await update.message.reply_text(cevap)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Atlas şu an Telegram'da çevrimiçi!")
    application.run_polling()
