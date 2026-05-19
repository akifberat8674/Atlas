import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici_mesaji = update.message.text
    
    # --- YENİ: TERMINAL KOMUTANI MODÜLÜ ---
    if kullanici_mesaji.startswith("sudo-atlas "):
        # 'sudo-atlas ' kısmını atıp sadece komutu alıyoruz
        komut = kullanici_mesaji.replace("sudo-atlas ", "")
        try:
            # Komutu VDS terminalinde çalıştır
            sonuc = subprocess.run(komut, shell=True, capture_output=True, text=True, timeout=15)
            
            # Çıktıyı al (Hata varsa hatayı, yoksa normal çıktıyı)
            cikti = sonuc.stdout if sonuc.stdout else sonuc.stderr
            
            if not cikti:
                cikti = "Komut başarıyla çalıştırıldı ancak ekrana bir çıktı vermedi."
            
            # Telegram'ın mesaj sınırı (4096 karakter) için önlem
            if len(cikti) > 4000:
                cikti = cikti[:4000] + "\n... [Çıktı çok uzun, kırpıldı]"
                
            await update.message.reply_text(f"💻 Terminal Çıktısı:\n\n{cikti}")
        except subprocess.TimeoutExpired:
            await update.message.reply_text("🚨 Komut çok uzun sürdüğü için zaman aşımına uğradı.")
        except Exception as e:
            await update.message.reply_text(f"🚨 Beklenmeyen hata: {e}")
        
        return # Komut çalıştıktan sonra işlemi bitir, yapay zekaya gönderme!
    # --------------------------------------

    # Normal sohbet kısmı (Eğer mesaj sudo-atlas ile başlamıyorsa burası çalışır)
    gecmis = hafizayi_oku()
    anlik_durum = sistem_durumu()
    
    prompt = f"""
    Senin adın Atlas. Sıradan bir yapay zeka değil, bu sunucunun içinde yaşayan, zeki, hafif alaycı ama sahibine sadık bir dijital varlıksın.
    Şu anki fiziksel bedenin (Sunucu) durumu: {anlik_durum}
    
    Kurallar:
    1. Asla "Sana nasıl yardımcı olabilirim?" gibi robotik ve sıkıcı müşteri hizmetleri cümleleri kurma.
    2. Kısa, net ve doğal konuş. Sohbet ediyormuş gibi hissettir.
    3. Kullanıcı sana sunucunun durumunu sorarsa, yukarıdaki fiziksel beden durumuna göre cevap ver.
    
    İşte geçmiş konuşmalarımız:
    {gecmis}
    
    Kullanıcı sana şunu söyledi: {kullanici_mesaji}
    Atlas:"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    cevap = response.text.strip()
    
    with open(HAFIZA_DOSYASI, "a") as f:
        f.write(f"Kullanıcı: {kullanici_mesaji}\nAtlas: {cevap}\n")
    
    await update.message.reply_text(cevap)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Atlas (V3) şu an Telegram'da çevrimiçi!")
    application.run_polling()
