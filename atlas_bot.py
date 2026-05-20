import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from google import genai
import os
import psutil
import subprocess
from dotenv import load_dotenv

# Grafik kütüphanelerini arka plan modunda (Non-GUI) başlatıyoruz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Gizli kasayı (.env) aç
load_dotenv("/root/atlas/.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HAFIZA_DOSYASI = "/root/atlas/konusmalar.txt"
PANO_GÖRSEL_YOLU = "/root/atlas/sistem_panosu.png"

client = genai.Client(api_key=GEMINI_API_KEY)

# Geçmiş kaynak takibi için hafıza listeleri (Son 10 kaydı tutar)
cpu_gecmis = [0] * 10
ram_gecmis = [0] * 10

def hafizayi_oku():
    if not os.path.exists(HAFIZA_DOSYASI): return ""
    with open(HAFIZA_DOSYASI, "r") as f:
        satirlar = f.readlines()
        return "".join(satirlar[-10:])

def sistem_durumu():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return cpu, ram, disk

# --- GÖRSEL SİSTEM PANOSU OLUŞTURUCU ---
def pano_grafigi_ciz(cpu, ram, disk):
    global cpu_gecmis, ram_gecmis
    
    # Listeleri güncelle (en eskiyi at, yeniyi ekle)
    cpu_gecmis.pop(0)
    cpu_gecmis.append(cpu)
    ram_gecmis.pop(0)
    ram_gecmis.append(ram)
    
    # Grafik alanını oluştur (Karanlık Tema)
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={'width_ratios': [2, 1]})
    fig.patch.set_facecolor('#0A0A0A') # Derin Siyah Arka Plan
    
    # 1. Grafik: Zaman Tüneli (CPU & RAM)
    ax1.set_facecolor('#121214')
    ax1.plot(cpu_gecmis, label=f'CPU (%{cpu})', color='#9D4EDD', linewidth=2.5, marker='o') # Parlak Mor
    ax1.plot(ram_gecmis, label=f'RAM (%{ram})', color='#E0AAFF', linewidth=2, linestyle='--') # Açık Mor
    ax1.set_title("KAYNAK KULLANIM TRENDİ", fontsize=11, color='#FFFFFF', fontweight='bold', pad=10)
    ax1.set_ylim(0, 100)
    ax1.grid(True, color='#241435', linestyle=':') # Morumsu ince ızgara çizgileri
    ax1.legend(loc='upper left', facecolor='#1A1A1E', edgecolor='#9D4EDD')
    ax1.tick_params(colors='white')
    
    # 2. Grafik: Anlık Durum (Disk)
    ax2.set_facecolor('#121214')
    bars = ax2.bar(['DİSK'], [disk], color='#5A189A', edgecolor='#9D4EDD', width=0.4) # Derin Mor Sütun
    ax2.set_title("DEPOLAMA DURUMU", fontsize=11, color='#FFFFFF', fontweight='bold', pad=10)
    ax2.set_ylim(0, 100)
    ax2.grid(True, axis='y', color='#241435', linestyle=':')
    ax2.tick_params(colors='white')
    
    # Sütun üzerine yüzde değerini yazma
    for bar in bars:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, yval + 2, f"%{yval}", ha='center', va='bottom', color='white', fontweight='bold')

    plt.tight_layout()
    plt.savefig(PANO_GÖRSEL_YOLU, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

async def pano_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 İstatistikler toplanıyor, görsel pano hazırlanıyor...")
    
    try:
        cpu, ram, disk = sistem_durumu()
        pano_grafigi_ciz(cpu, ram, disk)
        
        # Hazırlanan resmi Telegram'dan gönder
        with open(PANO_GÖRSEL_YOLU, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, 
                photo=photo, 
                caption=f"💻 *Atlas Sistem Telemetrisi*\n\n🟣 *CPU:* %{cpu}\n🔮 *RAM:* %{ram}\n💾 *Disk:* %{disk}",
                parse_mode="Markdown"
            )
    except Exception as e:
        await update.message.reply_text(f"🚨 Pano çizilirken bir hata oluştu: {e}")
    finally:
        if os.path.exists(PANO_GÖRSEL_YOLU):
            os.remove(PANO_GÖRSEL_YOLU)

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
            response = client.models.generate_content(model='gemini-3-flash-preview', contents=[yuklenen_medya, prompt])
            await mesaj.reply_text(response.text.strip())
        except Exception as e:
            await mesaj.reply_text(f"🚨 Hata: {e}")
        finally:
            if os.path.exists(gecici_yol): os.remove(gecici_yol)

# --- HATIRLATICI MODÜLÜ ---
async def hatirlat_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        dakika = float(context.args[0])
        hatirlatilacak_not = " ".join(context.args[1:])
        context.job_queue.run_once(callback=hatirlatici_tetikleyici, when=dakika * 60, data=hatirlatilacak_not, chat_id=update.effective_chat.id)
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
            await update.message.reply_text(f"💻 Terminal:\n\n{cikti[:4000]}")
        except Exception as e:
            await update.message.reply_text(f"🚨 Hata: {e}")
        return

    cpu, ram, disk = sistem_durumu()
    anlik_durum_metin = f"CPU: %{cpu}, RAM: %{ram}, Disk: %{disk}"
    gecmis = hafizayi_oku()
    
    prompt = f"""
    Senin adın Atlas. Bu sunucunun içinde yaşayan, zeki, hafif alaycı ama Akif'e sadık bir dijital varlıksın.
    Fiziksel bedenin durumu: {anlik_durum_metin}
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
    
    # Komutları tanımlıyoruz
    application.add_handler(CommandHandler("panel", pano_komutu))
    application.add_handler(CommandHandler("hatirlat", hatirlat_komutu))
    
    application.add_handler(MessageHandler(filters.PHOTO | filters.VOICE | filters.Document.ALL, handle_multimedia))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    print("Atlas (V6 - Telemetry Jarvis Modu) çevrimiçi!")
    application.run_polling()
