import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from google import genai
import os
import psutil
import subprocess
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
        return "".join(satirlar[-10:])

def sistem_durumu():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return f"CPU: %{cpu}, RAM: %{ram}, Disk: %{disk}"

# --- GÖZLER, KULAKLAR VE BELGE YİYİCİ MODÜLÜ ---
async def handle_multimedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = update.message
    dosya_id = None
    uzanti = ""
    talimat = mesaj.caption if mesaj.caption else ""

    if mesaj.photo:
        dosya_id = mesaj.photo[-1].file_id
        uzanti = ".jpg"
        if not talimat: talimat = "Bu fotoğrafta ne görüyorsun, detaylıca analiz et."
    elif mesaj.voice:
        dosya_id = mesaj.voice.file_id
        uzanti = ".ogg"
        talimat = "Bu sesli mesajı dinle ve ne söylediğime akıllıca bir cevap ver."
    elif mesaj.document:
        dosya_id = mesaj.document.file_id
        uzanti = f".{mesaj.document.file_name.split('.')[-1]}"
        if not talimat: talimat = "Bu belgeyi analiz et, ne olduğunu bana özetle."

    if dosya_id:
        await mesaj.reply_text("⏳ Atlas inceliyor...")
        
        yeni_dosya = await context.bot.get_file(dosya_id)
        gecici_yol = f"/root/atlas/temp_medya{uzanti}"
        await yeni_dosya.download_to_drive(gecici_yol)
        
        try:
            yuklenen_medya = client.files.upload(file=gecici_yol)
            prompt = f"Sen Atlas'sın, Akif'in dijital asistanısın. Akif sana bir dosya/medya gönderdi. Talimatı: {talimat}"
            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=[yuklenen_medya, prompt]
            )
            await mesaj.reply_text(response.text.strip())
        except Exception as e:
            await mesaj.reply_text(f"🚨 Hata: {e}")
        finally:
            if os.path.exists(gecici_yol):
                os.remove(gecici_yol)

# --- HATIRLATICI MODÜLÜ ---
async def hatirlat_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        dakika = float(context.args[0])
        hatirlatilacak_not = " ".join(context.args[1:])
        context.job_queue.run_once(
            callback=hatirlatici_tetikleyici, 
            when=dakika * 60, 
            data=hatirlatilacak_not, 
            chat_id=update.effective_chat.id
        )
        await update.message.reply_text(f"Tamamdır! {dakika} dakika sonra '{hatirlatilacak_not}' konusunu hatırlatacağım. 🫡")
    except (IndexError, ValueError):
        await update.message.reply_text("🚨 Kullanım hatası! Örnek: /hatirlat 5 Motoru kontrol et")

async def hatirlatici_tetikleyici(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"🔔 HATIRLATMA ZAMANI AKİF!\n\nKonu: {job.data}")

# --- METİN VE KOMUTAN MODÜLÜ ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici_mesaji = update.message.text
    
    if kullanici_mesaji.startswith("sudo-atlas "):
        komut = kullanici_mesaji.replace("sudo-atlas ", "")
        try:
            sonuc = subprocess.run(komut, shell=True, capture_output=True, text=True, timeout=15)
            cikti = sonuc.stdout if sonuc.stdout else sonuc.stderr
            if not cikti: cikti = "Çıktı yok."
            if len(cikti) > 4000: cikti = cikti[:4000] + "\n... [Kırpıldı]"
            await update.message.reply_text(f"💻 Terminal:\n\n{cikti}")
        except Exception as e:
            await update.message.reply_text(f"🚨 Hata: {e}")
        return

    gecmis = hafizayi_oku()
    anlik_durum = sistem_durumu()
    
    prompt = f"""
    Senin adın Atlas. Bu sunucunun içinde yaşayan, zeki, hafif alaycı ama Akif'e sadık bir dijital varlıksın.
    Fiziksel bedenin durumu: {anlik_durum}
    Asla "Sana nasıl yardımcı olabilirim?" deme. Doğal konuş.
    Geçmiş: {gecmis}
    Akif: {kullanici_mesaji}
    Atlas:"""
    
    response = client.models.generate_content(model='gemini-3-flash-preview', contents=prompt)
    cevap = response.text.strip()
    
    with open(HAFIZA_DOSYASI, "a") as f:
        f.write(f"Akif: {kullanici_mesaji}\nAtlas: {cevap}\n")
    
    await update.message.reply_text(cevap)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("hatirlat", hatirlat_komutu))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VOICE | filters.Document.ALL, handle_multimedia))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    print("Atlas (Telegram Jarvis Modu - Gemini 3 Flash) çevrimiçi!")
    application.run_polling()

