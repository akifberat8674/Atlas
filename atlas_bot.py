import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai
import os

# Ayarlar
genai.configure(api_key="AIzaSyCIUgI7ksuMZiwfYl0t4TriWp4LpPBDn0k")
model = genai.GenerativeModel('gemini-1.5-flash')
TOKEN = "8600728246:AAE5ICTLhfq4Zxy8yb_dD0CB0uG4DvlLZJg"
HAFIZA_DOSYASI = "/root/atlas/konusmalar.txt"

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
