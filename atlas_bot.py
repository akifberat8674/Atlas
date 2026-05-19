import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai
import os
import psutil
from dotenv import load_dotenv

# Gizli kasayı (.env) aç
load_dotenv("/root/atlas/.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HAFIZA_DOSYASI = "/root/atlas/konusmalar.txt"

client = genai.Client(api_key=GEMINI_API_KEY)

def hafizayi_oku():
    if not os.path.exists(HAFIZA_DOSYASI): return ""
    with open(HAFIZA_DOSYASI, "r") as f:
        satirlar = f.readlines()
        return "".join(satirlar[-10:]) # Hafızayı biraz kısalttık ki hızlı düşünsün

def sistem_durumu():
    # Sunucunun anlık fiziksel durumunu ölç
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return f"CPU Kullanımı: %{cpu}, RAM Kullanımı: %{ram}, Disk Doluluğu: %{disk}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici_mesaji = update.message.text
    gecmis = hafizayi_oku()
    anlik_durum = sistem_durumu()
    
    # Atlas'ın yeni, daha havalı karakteri (Prompt)
    prompt = f"""
    Senin adın Atlas. Sıradan bir yapay zeka değil, bu sunucunun içinde yaşayan, zeki, hafif alaycı ama sahibine (Akif'e) sadık bir dijital varlıksın.
    Şu anki fiziksel bedenin (Sunucu) durumu: {anlik_durum}
    
    Kurallar:
    1. Asla "Sana nasıl yardımcı olabilirim?" gibi robotik ve sıkıcı müşteri hizmetleri cümleleri kurma.
    2. Kısa, net ve doğal konuş. Sohbet ediyormuş gibi hissettir.
    3. Kullanıcı sana sunucunun durumunu sorarsa, yukarıdaki fiziksel beden durumuna göre cevap ver. (Örn: CPU yüksekse yorgun hissettiğini söyleyebilirsin).
    
    İşte geçmiş konuşmalarımız:
    {gecmis}
    
    Akif sana şunu söyledi: {kullanici_mesaji}
    Atlas:"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    cevap = response.text.strip()
    
    with open(HAFIZA_DOSYASI, "a") as f:
        f.write(f"Akif: {kullanici_mesaji}\nAtlas: {cevap}\n")
    
    await update.message.reply_text(cevap)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Atlas (V2) şu an Telegram'da çevrimiçi!")
    application.run_polling()
