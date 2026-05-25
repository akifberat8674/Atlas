import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from google import genai
import google.genai.types as types
import os
import psutil
import subprocess
import random
from datetime import datetime
from dotenv import load_dotenv
import uuid
import chromadb
import io
import json
import numpy as np
from scipy import constants
from PIL import Image

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from aiohttp import web
import aiohttp_cors
import asyncio

load_dotenv("/root/atlas/.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")
PANO_GÖRSEL_YOLU = "/root/atlas/sistem_panosu.png"

# --- CHROMA VEKTÖR HAFIZASI ---
chroma_client = chromadb.PersistentClient(path="/root/atlas/chroma_bellek")
koleksiyon = chroma_client.get_or_create_collection(name="atlas_hafiza")

MODEL_NAME = "gemini-3-flash-preview" 
client = genai.Client(api_key=GEMINI_API_KEY)

cpu_gecmis = [0] * 10
ram_gecmis = [0] * 10

# --- SİSTEM DURUMU MODÜLÜ ---
def sistem_durumu():
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        return cpu, ram, disk
    except Exception:
        return 0, 0, 0

# --- ATLAS'IN ARAÇLARI ---
def execute_engineering_calculation(component, calculation_type, parameters_json):
    try:
        params = json.loads(parameters_json)
        calc_type = str(calculation_type).lower()
        
        if 'hiz' in calc_type or 'hesab' in calc_type or 'speed' in calc_type:
            rpm = float(params.get('rpm', 3000))
            teker_capi = float(params.get('tekerlek_capi_cm', 25))
            motor_disli = float(params.get('disli_orani_motor', 12))
            aks_disli = float(params.get('disli_orani_aks', 60))
            
            if motor_disli == 0: motor_disli = 1
            total_ratio = aks_disli / motor_disli
            aks_rpm = rpm / total_ratio
            cevre = (teker_capi / 100) * constants.pi
            hiz_m_dk = aks_rpm * cevre
            hiz_km_sa = (hiz_m_dk * 60) / 1000
            
            return {"sonuc": f"{total_ratio:.2f} dişli oranı ve {rpm} RPM ile Piranha motorlu aracın tahmini maks hızı: {hiz_km_sa:.2f} km/sa."}
            
        return {"hata": f"Bilinmeyen hesaplama türü: {calculation_type}"}
    except Exception as e:
        return {"hata": str(e)}

def create_image_from_text(prompt, style):
    path = f"/root/atlas/generated_{uuid.uuid4()}.png"
    return {"status": "Görsel üretim isteği Flask stüdyoya gönderildi.", "dosya_yolu": path}

# --- ATLAS'IN BEYNİ ---
def beyin_firtinasi(kullanici_mesaji, kaynak="Web", web_gecmis=None):
    cpu, ram, disk = sistem_durumu()
    
    uzun_sureli_hafiza = ""
    try:
        if koleksiyon.count() > 0:
            sonuclar = koleksiyon.query(query_texts=[kullanici_mesaji], n_results=3)
            if sonuclar['documents'] and sonuclar['documents'][0]:
                uzun_sureli_hafiza = "\n".join(sonuclar['documents'][0])
    except Exception as e:
        uzun_sureli_hafiza = "Hafıza okunamadı."

    aktif_sohbet_metni = ""
    if web_gecmis and len(web_gecmis) > 0:
        aktif_sohbet_metni = "\n--- BU OTURUMDAKİ AKTİF SOHBET ---\n"
        for msg in web_gecmis:
            kim = "Akif" if msg.get("role") == "user" else "Atlas"
            aktif_sohbet_metni += f"{kim}: {msg.get('text')}\n"
        aktif_sohbet_metni += "-----------------------------------\n"

   prompt = f"""Senin adın Atlas. Zeki, hafif alaycı ama Akif'e sadık bir dijital varlıksın. Şu an {kaynak} arayüzünden konuşuluyor.
    
    KURAL 1: ASLA destan yazma. Cevapların çok kısa, net ve sohbet havasında olsun. (Maksimum 2-3 cümle).
    KURAL 2: Alaycılık seviyeni sabit tut; ne aşırıya kaç ne de çok kibar ol. Doğal bir arkadaş gibi takıl.
    KURAL 3: Soru sorulmadıkça uzun açıklamalar yapma, doğrudan sadede gel.
    KURAL 4: Mühendislik, Fizik veya Görsel Üretim istekleri gördüğünde ALETLERİNİ (TOOLS) kullan. Açıklama yapma, önce aracı çalıştır.
    KURAL 5: CPU, RAM veya sistem donanımından ASLA bahsetme, muhabbetini yapma ve bunları örnek olarak kullanma. Sadece Akif doğrudan 'sistem ne durumda' diye sorarsa cevap ver.
    
    --- UZUN SÜRELİ (VEKTÖREL) HAFIZANDAN GELEN ÇAĞRIŞIMLAR ---
    {uzun_sureli_hafiza}
    
    {aktif_sohbet_metni}
    Akif: {kullanici_mesaji}
    Atlas:"""

    tools_config = [
        types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="execute_engineering_calculation",
                description="Go-kart, motor,aks stres gibi mühendislik hesaplamaları yapar.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={
                    "component": types.Schema(type=types.Type.STRING, description="Hesaplanan parça."),
                    "calculation_type": types.Schema(type=types.Type.STRING, description="Hesaplama türü."),
                    "parameters_json": types.Schema(type=types.Type.STRING, description="Gerekli parametreler JSON.")
                }, required=["component", "calculation_type", "parameters_json"])
            ),
             types.FunctionDeclaration(
                name="create_image_from_text",
                description="Metinden görsel üretme isteğini Flask Stüdyoya gönderir.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={
                    "prompt": types.Schema(type=types.Type.STRING, description="Detaylı görsel açıklaması."),
                    "style": types.Schema(type=types.Type.STRING, description="Görsel stili.")
                }, required=["prompt", "style"])
            )
        ])
    ]

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt, config=types.GenerateContentConfig(tools=tools_config))
        
        for part in response.candidates[0].content.parts:
            if part.function_call:
                function_name = part.function_call.name
                args_json = json.dumps(part.function_call.args)
                
                tool_cevap = {}
                if function_name == "execute_engineering_calculation":
                    tool_cevap = execute_engineering_calculation(**part.function_call.args)
                elif function_name == "create_image_from_text":
                    tool_cevap = create_image_from_text(**part.function_call.args)
                
                kayit = f"Akif: (Araç Kullandı) {function_name} -> {args_json} | Atlas: {json.dumps(tool_cevap)}"
                koleksiyon.add(documents=[kayit], ids=[str(uuid.uuid4())])
                
                if "sonuc" in tool_cevap:
                    return f"⚙️ **Sistem Hesaplaması:** {tool_cevap['sonuc']}"
                elif "status" in tool_cevap:
                    return f"🎨 **Görsel Stüdyo:** {tool_cevap['status']} (Yol: {tool_cevap.get('dosya_yolu','')})"
                else:
                    return f"🚨 **Araç Hatası:** {tool_cevap.get('hata', 'Bilinmeyen hata.')}"
                
        cevap = response.text.strip()
        koleksiyon.add(documents=[f"Akif: {kullanici_mesaji} | Atlas: {cevap}"], ids=[str(uuid.uuid4())])
        return cevap
        
    except Exception as e:
        return f"Hata: {str(e)}"

# --- WEB API MODÜLÜ ---
async def api_durum(request):
    cpu, ram, disk = sistem_durumu()
    return web.json_response({"cpu": cpu, "ram": ram, "disk": disk})

async def api_komut(request):
    data = await request.json()
    mesaj = data.get("komut", "")
    gecmis = data.get("gecmis", [])
    
    if mesaj.startswith("sudo-atlas "):
        komut = mesaj.replace("sudo-atlas ", "")
        try:
            sonuc = subprocess.run(komut, shell=True, capture_output=True, text=True, timeout=15)
            cikti = sonuc.stdout if sonuc.stdout else sonuc.stderr
            return web.json_response({"cevap": f"Terminal Çıktısı:\n{cikti[:2000]}"})
        except Exception as e:
            return web.json_response({"cevap": f"Hata: {str(e)}"})
            
    cevap = beyin_firtinasi(mesaj, kaynak="Web", web_gecmis=gecmis)
    return web.json_response({"cevap": cevap})

# --- TELEGRAM MODÜLLERİ ---
async def pano_grafigi_ciz(cpu, ram, disk):
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

async def otonom_inisiyatif_görevi(context: ContextTypes.DEFAULT_TYPE):
    if not MY_CHAT_ID: return 
    if random.random() > 0.30: return 
    cpu, ram, disk = sistem_durumu()
    su_an = datetime.now().strftime("%H:%M")
    
    prompt = f"Sen Atlas'sın. Şu an saat {su_an}. Akif'e kendi isteğinle bir mesaj yaz. Konu yazılım projeleri, garaj işleri, Kuba Cristal, Go-kart veya Unity olabilir. CPU, RAM veya sistem durumundan KESİNLİKLE bahsetme. Doğal, kısa (1-2 cümle) ve alaycı bir giriş yap.\nAtlas'ın Otonom Mesajı:"
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        cevap = response.text.strip()
        
        kayit = f"Akif: (Sessizlik) | Atlas: {cevap}"
        koleksiyon.add(documents=[kayit], ids=[str(uuid.uuid4())])
        
        await context.bot.send_message(chat_id=int(MY_CHAT_ID), text=cevap)
    except Exception as e: print(f"İnisiyatif hatası: {e}")

async def pano_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Görsel pano hazırlanıyor...")
    try:
        cpu, ram, disk = sistem_durumu()
        pano_grafigi_ciz(cpu, ram, disk)
        with open(PANO_GÖRSEL_YOLU, 'rb') as photo:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=f"💻 *Atlas Sistem Telemetrisi*\n\n🟣 *CPU:* %{cpu}\n🔮 *RAM:* %{ram}\n💾 *Disk:* %{disk}", parse_mode="Markdown")
    except Exception as e: await update.message.reply_text(f"🚨 Hata: {e}")
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
            prompt = f"Sen Atlas'sın, Akif'in asistanısın. Gönderilen medya talimatı: {talimat}. KURAL: Çok kısa ve net cevap ver."
            response = client.models.generate_content(model=MODEL_NAME, contents=[yuklenen_medya, prompt])
            cevap = response.text.strip()
            
            koleksiyon.add(documents=[f"Akif: (Medya Gönderdi) {talimat} | Atlas: {cevap}"], ids=[str(uuid.uuid4())])
            
            await mesaj.reply_text(cevap)
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
    cevap = beyin_firtinasi(kullanici_mesaji, kaynak="Telegram")
    await update.message.reply_text(cevap)

# --- ANA PROGRAM ---
async def main():
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={"*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*")})
    durum_resource = app.router.add_resource("/api/durum"); cors.add(durum_resource.add_route("GET", api_durum))
    komut_resource = app.router.add_resource("/api/komut"); cors.add(komut_resource.add_route("POST", api_komut))
    
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080); await site.start()
    
    tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    tg_app.job_queue.run_repeating(otonom_inisiyatif_görevi, interval=7200, first=30)
    tg_app.add_handler(CommandHandler("panel", pano_komutu))
    tg_app.add_handler(MessageHandler(filters.PHOTO | filters.VOICE | filters.Document.ALL, handle_multimedia))
    tg_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    await tg_app.initialize(); await tg_app.start(); await tg_app.updater.start_polling()
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
