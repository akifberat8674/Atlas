import asyncio
import os
import json
import logging
import subprocess
import psutil
from aiohttp import web
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from google import genai
from dotenv import load_dotenv

load_dotenv("/root/atlas/.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
IG_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
IG_VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN")
HAFIZA_DOSYASI = "/root/atlas/konusmalar.txt"

client = genai.Client(api_key=GEMINI_API_KEY)

def hafizayi_oku():
    if not os.path.exists(HAFIZA_DOSYASI): return ""
    with open(HAFIZA_DOSYASI, "r") as f:
        return "".join(f.readlines()[-10:])

def sistem_durumu():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return f"CPU: %{cpu}, RAM: %{ram}, Disk: %{disk}"

def beyin_firtinasi(kullanici_mesaji, platform="Telegram"):
    gecmis = hafizayi_oku()
    anlik_durum = sistem_durumu()
    
    prompt = f"""
    Senin adın Atlas. Bu sunucunun içinde yaşayan, zeki, hafif alaycı ama Akif'e sadık bir dijital varlıksın.
    Şu an seninle {platform} üzerinden konuşuluyor.
    Fiziksel bedenin durumu: {anlik_durum}
    Asla "Sana nasıl yardımcı olabilirim?" deme. Doğal ve akıcı konuş.
    Geçmiş: {gecmis}
    Kullanıcı: {kullanici_mesaji}
    Atlas:"""
    
    response = client.models.generate_content(model='gemini-3-flash', contents=prompt)
    cevap = response.text.strip()
    
    with open(HAFIZA_DOSYASI, "a") as f:
        f.write(f"[{platform}] Akif/Kullanıcı: {kullanici_mesaji}\nAtlas: {cevap}\n")
    return cevap

# --- TELEGRAM MODÜLÜ ---
async def handle_telegram_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici_mesaji = update.message.text
    if kullanici_mesaji.startswith("sudo-atlas "):
        komut = kullanici_mesaji.replace("sudo-atlas ", "")
        try:
            sonuc = subprocess.run(komut, shell=True, capture_output=True, text=True, timeout=15)
            cikti = sonuc.stdout if sonuc.stdout else sonuc.stderr
            await update.message.reply_text(f"💻 Terminal:\n\n{cikti[:4000]}")
        except Exception as e:
            await update.message.reply_text(f"🚨 Hata: {e}")
        return
    
    cevap = beyin_firtinasi(kullanici_mesaji, platform="Telegram")
    await update.message.reply_text(cevap)

# --- INSTAGRAM MODÜLÜ (WEBHOOK) ---
async def instagram_send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={IG_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()

async def handle_instagram_webhook(request):
    # Meta'nın webhook doğrulama adımı (GET isteği)
    if request.method == "GET":
        params = request.query
        if params.get("hub.verify_token") == IG_VERIFY_TOKEN:
            return web.Response(text=params.get("hub.challenge"))
        return web.Response(status=403)
    
    # Mesaj geldiğinde tetiklenen adım (POST isteği)
    elif request.method == "POST":
        try:
            data = await request.json()
            if "entry" in data:
                for entry in data["entry"]:
                    if "messaging" in entry:
                        for messaging_event in entry["messaging"]:
                            if "message" in messaging_event and "text" in messaging_event["message"]:
                                sender_id = messaging_event["sender"]["id"]
                                user_text = messaging_event["message"]["text"]
                                
                                # Instagram mesajını Gemini 3 Flash'a gönder
                                atlas_cevap = beyin_firtinasi(user_text, platform="Instagram")
                                
                                # Cevabı Instagram DM'den geri yolla
                                await instagram_send_message(sender_id, atlas_cevap)
        except Exception as e:
            print(f"Instagram yönlendirme hatası: {e}")
        return web.Response(text="EVENT_RECEIVED")

# --- ANA TETİKLEYİCİ (İKİ MOTORU BİRDEN ÇALIŞTIRAN YAPI) ---
async def main():
    # 1. Telegram'ı Başlat (Arka planda dinlemeye alıyoruz)
    tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    tg_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_telegram_text))
    
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    print("🤖 Telegram Motoru Aktif!")

    # 2. Instagram Webhook Sunucusunu Başlat (5000 portundan dinleyecek)
    web_app = web.Application()
    web_app.router.add_get('/webhook', handle_instagram_webhook)
    web_app.router.add_post('/webhook', handle_instagram_webhook)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 5000)
    await site.start()
    print("📸 Instagram Webhook Kapısı Açıldı! (Port: 5000)")

    # Sistemin sürekli açık kalmasını sağla
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())

