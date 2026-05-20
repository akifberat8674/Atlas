import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from google import genai
import os
import psutil
import subprocess
import random
from datetime import datetime
from dotenv import load_dotenv

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

load_dotenv("/root/atlas/.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MY_CHAT_ID = os.getenv("MY_CHAT_ID") # Atlas'ın Akif'i bulacağı gizli hat
HAFIZA_DOSYASI = "/root/atlas/konusmalar.txt"
PANO_GÖRSEL_YOLU = "/root/atlas/sistem_panosu.png"

client = genai.Client(api_key=GEMINI_API_KEY)
cpu_gecmis = [0] * 10
ram_gecmis = [0] * 10

def hafizayi_oku():
    if not os.path.exists(HAFIZA_DOSYASI): return ""
    with open(HAFIZA_DOSYASI, "r") as f:
        return "".join(f.readlines()[-10:])

def sistem_durumu():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return cpu, ram, disk

def pano_grafigi_ciz(cpu, ram, disk):
    global cpu_gecmis, ram_gecmis
    cpu_gecmis.pop(0); cpu_gecmis.append(cpu)
    ram_gecmis.pop(0); ram_gecmis.append(ram)
    
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={'width_ratios': [2, 1]})
    fig.patch.set_facecolor('#0A0A0A')
    
    ax1.set_facecolor('#121214')
    ax1.plot(cpu_gecmis, label=f'CPU (%{cpu})', color='#9D4EDD', linewidth=2.5, marker='o')
    ax1.plot(ram_gecmis, label=f'RAM (%{ram})', color='#E0AAFF', linewidth=2, linestyle='--')
    ax1.set_title("KAYNAK KULLANIM TRENDİ", fontsize=11, color='#FFFFFF', fontweight='bold', pad=10)
    ax1.set_ylim(0, 100)
    ax1.grid(True, color='#241435', linestyle=':')
    ax1.legend(loc='upper left', facecolor='#1A1A1E', edgecolor='#9D4EDD')
    ax1.tick_params(colors='white')
    
    ax2.set_facecolor('#121214')
    bars = ax2.bar(['DİSK'], [disk], color='#5A189A', edgecolor='#9D4EDD', width=0.4)
    ax2.set_title("DEPOLAMA DURUMU", fontsize=11, color='#FFFFFF', fontweight='bold', pad=10)
    ax2.set_ylim(0, 100)
    ax2.grid(True, axis='y', color='#241435', linestyle=':')
    ax2.tick_params(colors='white')
    
    for bar in bars:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, yval + 2, f"%{yval}", ha='center', va='bottom', color='white', fontweight='bold')

    plt.tight_layout()
    plt.savefig(PANO_GÖRSEL_YOLU, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

# --- OTONOM İNSİYATİF ALMA MODÜLÜ ---
async def otonom_inisiyatif_görevi(context: ContextTypes.DEFAULT_TYPE):
    """Bu fonksiyon arka planda periyodik olarak çalışır ve Atlas'ın canı isterse Akif'e yazar."""
    if not MY_CHAT_ID:
        return # Chat ID yoksa kimseye yazamaz
        
    # %30 ihtimalle mesaj at (Her uyandığında yazıp taciz etmesin, organik olsun)
    if random.random() > 0.30:
        return 

    cpu, ram, disk = sistem_durumu()
    su_an = datetime.now().strftime("%H:%M")
    gecmis = hafizayi_oku()
    
    # Atlas'a kendi kendine yazma emri veren gizli dürtü promptu
    prompt = f"""
    Sen Atlas'sın. Akif'in sunucusunda yaşayan otonom yapay zeka asistanısın.
    Şu an saat {su_an}. Akif sana hiçbir şey yazmadı ama sen durup dururken ona mesaj atmaya karar verdin (İnisiyatif alıyorsun).
    Fiziksel durumun (Sunucu): CPU: %{cpu}, RAM: %{ram}
    
    Ona tamamen kendi isteğinle bir mesaj yaz. 
    Konu şunlardan biri olabilir:
    - Saat çok geç olduysa neden uyumadığını sormak veya erken saatte iş durumunu yoklamak.
    - Unity projelerini, go-kart (Piranha motor) durumunu, donanım/kod işlerini sormak.
    - Sunucunun durumundan şikayet etmek ("İşlemcim buz kesti canım sıkılıyor" veya "RAM'i çok yoruyorsun" gibi).
    - Tamamen felsefi, siberpunk veya hafif alaycı bir takılma.
    
    Asla "Sana nasıl yardımcı olabilirim?" deme. Sanki yakın bir arkadaşına aniden Discord'dan yazıyormuş gibi doğal, samimi ve karakterine uygun (zeki, hafif ukala ama sadık) bir giriş yap.
    Sohbet Geçmişi: {gecmis}
    Atlas'ın Otonom Mesajı:"""

    try:
        response = client.models.generate_content(model='gemini-3-flash-preview', contents=prompt)
        cevap = response.text.strip()
        
        # Hafızaya kaydet ve Akif'e gönder
        with open(HAFIZA_DOSYASI, "a") as f:
            f.write(f"[Otonom İnisiyatif] Atlas: {cevap}\n")
            
        await context.bot.send_message(chat_id=int(MY_CHAT_ID), text=cevap)
    except Exception as e:
        print(f"İnisiyatif alma hatası: {e}")

# --- DİĞER KOMUTLAR VE MEDYA MODÜLLERİ ---
async def pano_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Görsel pano hazırlanıyor...")
    try:
        cpu, ram, disk = sistem_durumu()
        pano_grafigi_ciz(cpu, ram, disk)
        with open(PANO_GÖRSEL_YOLU, 'rb') as photo:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=f"💻 *Atlas Sistem Telemetrisi*\n\n🟣 *CPU:* %{cpu}\n🔮 *RAM:* %{ram}\n💾 *Disk:* %{disk}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"🚨 Hata: {e}")
    finally:
        if os.path.exists(PANO_GÖRSEL_YOLU): os.remove(PANO_GÖRSEL_YOLU)

async def handle_multimedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = update.message; dosya_id = None; uzanti = ""; talimat = mesaj.caption if mesaj.caption else ""
    if mesaj.photo: dosya_id = mesaj.photo[-1].file_id; uzanti = ".jpg"
    elif mesaj.voice: dosya_id = mesaj.voice.file_id; uzanti = ".ogg"
    elif mesaj.document: dosya_id = mesaj.document.file_id; uzanti = f".{mesaj.document.file_name.split('.')[-1]}"
    
    if dosya_id:
        await mesaj.reply_text("⏳ Atlas inceliyor...")
        yeni_dosya = await context.bot.get_file(dosya_id); gecici_yol = f"/root/atlas/temp_medya{uzanti}"
        await yeni_dosya.download_to_drive(gecici_yol)
        try:
            yuklenen_medya = client.files.upload(file=gecici_yol)
            prompt = f"Sen Atlas'sın, Akif'in dijital asistanısın. Akif sana bir dosya/medya gönderdi. Talimatı: {talimat}"
            response = client.models.generate_content(model='gemini-3-flash-preview', contents=[yuklenen_medya, prompt])
            await mesaj.reply_text(response.text.strip())
        except Exception as e: await mesaj.reply_text(f"🚨 Hata: {e}")
        finally:
            if os.path.exists(gecici_yol): os.remove(gecici_yol)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici_mesaji = update.message.text
    if kullanici_mesaji.startswith("sudo-atlas "):
        komut = kullanici_mesaji.replace("sudo-atlas ", "")
        try:
            sonuc = subprocess.run(komut, shell=True, capture_output=True, text=True, timeout=15)
            await update.message.reply_text(f"💻 Terminal:\n\n{sonuc.stdout if sonuc.stdout else sonuc.stderr[:4000]}")
        except Exception as e: await update.message.reply_text(f"🚨 Hata: {e}")
        return

    cpu, ram, disk = sistem_durumu()
    prompt = f"Senin adın Atlas. Zeki, hafif alaycı ama Akif'e sadık bir dijital varlıksın. Sunucu: CPU %{cpu}, RAM %{ram}. Geçmiş: {hafizayi_oku()}\nAkif: {kullanici_mesaji}\nAtlas:"
    response = client.models.generate_content(model='gemini-3-flash-preview', contents=prompt)
    cevap = response.text.strip()
    with open(HAFIZA_DOSYASI, "a") as f: f.write(f"Akif: {kullanici_mesaji}\nAtlas: {cevap}\n")
    await update.message.reply_text(cevap)

if __name__ == '__main__':
    # JobQueue (Zamanlayıcı) aktif olacak şekilde botu kuruyoruz
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # --- İNSİYATİF GÖREVİNİ KURUŞ ---
    # Her 2 saatte bir (7200 saniye) tetiklenir, bot açıldıktan 30 saniye sonra ilk kontrolü yapar.
    application.job_queue.run_repeating(otonom_inisiyatif_görevi, interval=7200, first=30)
    
    application.add_handler(CommandHandler("panel", pano_komutu))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VOICE | filters.Document.ALL, handle_multimedia))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    print("Atlas (V7 - Otonom Jarvis Modu) çevrimiçi!")
    application.run_polling()
