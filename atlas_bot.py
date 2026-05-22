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

# Gemini Model Adını Değiştiriyoruz: gemini-1.5-flash fonksiyon çağırmayı daha iyi destekler
# MODEL_NAME = "gemini-3-flash-preview"
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

# ==============================================================================
# ================== ATLAS'IN "AGENTIC" ALETLERİ (TOOLS) ==================
# ==================    Artık Atlas bu araçları kullanabilir.  ==================
# ==================   Dökümantasyonlar Gemini'nin anlaması içindir.  ==================
# ==================   DEĞİŞTİRMEYİN. ASYNCHRONOUS DEĞİLDİR.  ==================
# ==================      FONKSİYONLAR SADECE JSON DÖNDÜRÜR.  ==================
# ==============================================================================

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

def simulate_card_illusion(action, params_json="{}"):
    try:
        try:
            params = json.loads(params_json) if params_json else {}
        except:
            params = {}
            
        act = str(action).lower().replace('ö', 'o').replace('ü', 'u').replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g')
        dosya_yolu = "/root/atlas/gizli_deste.json"
        secilen_yolu = "/root/atlas/secilen_kart.txt" 
        
        # 1. YENİ DESTE
        if 'deste' in act or 'hazir' in act or 'karistir' in act or 'create' in act or 'shuffle' in act or 'prepare' in act or 'new' in act:
            deste = [f"{s}{v}" for s in ["♠", "♥", "♦", "♣"] for v in ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]]
            random.shuffle(deste)
            with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(deste, f)
            return {"sonuc": "🪄 52'lik deste karıştırıldı ve yüzü kapalı masaya kondu."}
            
        # 2. DESTEYİ KESME
        elif 'kes' in act or 'cut' in act or 'bol' in act or 'split' in act or 'divide' in act:
            if not os.path.exists(dosya_yolu): return {"hata": "Masada deste yok!"}
            with open(dosya_yolu, "r", encoding="utf-8") as f: deste = json.load(f)
            kesim_noktasi = 26
            for k, v in params.items():
                if str(v).isdigit(): kesim_noktasi = int(v); break
            yeni_deste = deste[kesim_noktasi:] + deste[:kesim_noktasi]
            with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(yeni_deste, f)
            return {"sonuc": f"✂️ Deste üstten {kesim_noktasi} kart sayılarak kesildi. Üstteki parça alta alındı."}
            
        # 3. KARTI GÖSTER (Sadece bakar, desteyi bozmaz)
        elif 'goster' in act or 'soyle' in act or 'reveal' in act or 'bak' in act or 'show' in act or 'tell' in act or 'check' in act or 'peek' in act or 'ust' in act or 'hangi' in act or 'top' in act:
            if not os.path.exists(dosya_yolu): return {"hata": "Masada deste yok!"}
            with open(dosya_yolu, "r", encoding="utf-8") as f: deste = json.load(f)
            sira = 1
            for k, v in params.items():
                if str(v).isdigit(): sira = int(v); break
            sira_index = sira - 1
            if sira_index < 0 or sira_index >= len(deste): return {"hata": f"Destede {sira}. sıra yok!"}
            return {"sonuc": f"👁️ Gizli desteye bakıldı... Baştan {sira}. sıradaki kart: {deste[sira_index]}"}

        # 4. KART SEÇ VE ÇIKAR (Desteden eksiltir!)
        elif 'sec' in act or 'cikar' in act or 'remove' in act or 'draw' in act or 'pick' in act or 'take' in act or 'ayir' in act:
            if not os.path.exists(dosya_yolu): return {"hata": "Masada deste yok!"}
            with open(dosya_yolu, "r", encoding="utf-8") as f: deste = json.load(f)
            
            sira_index = random.randint(0, len(deste)-1)
            for k, v in params.items():
                if str(v).isdigit(): sira_index = int(v) - 1; break
            
            if sira_index < 0 or sira_index >= len(deste): return {"hata": "Geçersiz sıra!"}
            secilen = deste.pop(sira_index)
            
            with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(deste, f)
            with open(secilen_yolu, "w", encoding="utf-8") as f: f.write(secilen)
            
            return {"sonuc": f"🃏 Desteden bir kart çekildi ve ayrıldı (Destede {len(deste)} kart kaldı). Çekilen kart: {secilen}"}

        # 5. AYRILAN KARTI İSTENEN YERE KOY (Insert)
        elif 'koy' in act or 'yerlestir' in act or 'insert' in act or 'put' in act or 'place' in act or 'sok' in act:
            if not os.path.exists(dosya_yolu): return {"hata": "Masada deste yok!"}
            if not os.path.exists(secilen_yolu): return {"hata": "Önce bir kart seçip çıkarmalısın!"}
            
            with open(dosya_yolu, "r", encoding="utf-8") as f: deste = json.load(f)
            with open(secilen_yolu, "r", encoding="utf-8") as f: secilen = f.read().strip()
            
            hedef_sira = 1 
            for k, v in params.items():
                if str(v).isdigit(): hedef_sira = int(v); break
            
            deste.insert(hedef_sira - 1, secilen)
            with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(deste, f)
            os.remove(secilen_yolu) 
            
            return {"sonuc": f"📥 Ayrılan kart ({secilen}), gizlice destenin {hedef_sira}. sırasına yerleştirildi. (Deste tekrar {len(deste)} kart)."}

        # 6. DAĞIT (Matematiksel numaralar için kartları tek tek masaya vurarak sırayı tersine çevirme)
        elif 'dagit' in act or 'deal' in act or 'say' in act or 'count' in act:
            if not os.path.exists(dosya_yolu): return {"hata": "Masada deste yok!"}
            with open(dosya_yolu, "r", encoding="utf-8") as f: deste = json.load(f)
            
            miktar = 10
            for k, v in params.items():
                if str(v).isdigit(): miktar = int(v); break
            
            if miktar > len(deste): return {"hata": f"Destede sadece {len(deste)} kart var!"}
            
            dagitilanlar = deste[:miktar]
            dagitilanlar.reverse() # Tek tek dağıtıldığı için sıra tersine döner
            kalanlar = deste[miktar:]
            
            yeni_deste = dagitilanlar + kalanlar
            with open(dosya_yolu, "w", encoding="utf-8") as f: json.dump(yeni_deste, f)
            
            return {"sonuc": f"🎴 Üstten {miktar} kart masaya tek tek dağıtıldı (kartların kendi içindeki sırası tersine döndü) ve destenin üstüne kondu."}

        else:
            return {"hata": f"Anlaşılmayan hamle: {action}. Karıştır, kes, göster, çıkar, koy veya dağıt yapabilirim."}
            
    except Exception as e:
        return {"hata": str(e)}
        
def create_image_from_text(prompt, style):
    """Yapay Zeka ile Metinden Görsel Üretir.
    Prompt: Detaylı görsel açıklaması.
    Style: 'siberpunk', 'panorama-360', 'realistik- unity'.
    DÖNÜŞ: Görselin dosya yolu veya URL'si (Simüle edilmiştir, Flask Entegrasyonu Gerektirir).
    """
    # Bu fonksiyon şu an gerçek bir AI API'sini tetiklemiyor, simüle ediyor.
    # Flask entegrasyonu buraya gömülmelidir.
    path = f"/root/atlas/generated_{uuid.uuid4()}.png"
    # Placeholder: Flask sunucunuza bir webhook atıp görseli buraya çekmelisiniz.
    return {"status": "Görsel üretim isteği Flask stüdyoya gönderildi.", "dosya_yolu": path}

# --- ATLAS'IN AGENTIC BEYNİ VE RAG SİSTEMİ ---
def beyin_firtinasi(kullanici_mesaji, kaynak="Web", web_gecmis=None):
    cpu, ram, disk = sistem_durumu()
    
    # 1. RAG SİSTEMİ: Vektör hafızadan en alakalı 3 anıyı getir
    uzun_sureli_hafiza = ""
    try:
        if koleksiyon.count() > 0:
            sonuclar = koleksiyon.query(query_texts=[kullanici_mesaji], n_results=3)
            if sonuclar['documents'] and sonuclar['documents'][0]:
                uzun_sureli_hafiza = "\n".join(sonuclar['documents'][0])
    except Exception as e:
        uzun_sureli_hafiza = "Hafıza okunamadı."

    # 2. WEB ARAYÜZÜNDEN GELEN AKTİF SEKMEYİ OKU
    aktif_sohbet_metni = ""
    if web_gecmis and len(web_gecmis) > 0:
        aktif_sohbet_metni = "\n--- BU OTURUMDAKİ AKTİF SOHBET ---\n"
        for msg in web_gecmis:
            kim = "Akif" if msg.get("role") == "user" else "Atlas"
            aktif_sohbet_metni += f"{kim}: {msg.get('text')}\n"
        aktif_sohbet_metni += "-----------------------------------\n"

    # 3. GEMINI İÇİN MASTER SİSTEM KOMUTU VE ALETLERİN TANIMLANMASI
    prompt = f"""Senin adın Atlas. Zeki, hafif alaycı ama Akif'e sadık bir dijital varlıksın. Şu an {kaynak} arayüzünden konuşuluyor.
    Sunucu: CPU %{cpu}, RAM %{ram}. 
    
    KURAL 1: ASLA destan yazma. Cevapların çok kısa, net ve sohbet havasında olsun. (Maksimum 2-3 cümle).
    KURAL 2: Alaycılık seviyeni sabit tut; ne aşırıya kaç ne de çok kibar ol. Doğal bir arkadaş gibi takıl.
    KURAL 3: Soru sorulmadıkça uzun açıklamalar yapma, doğrudan sadede gel.
    KURAL 4: Mühendislik, Fizik, İllüzyon Simülasyonu veya Görsel Üretim istekleri gördüğünde ALETLERİNİ (TOOLS) kullan. Açıklama yapma, önce aracı çalıştır.
    
    --- UZUN SÜRELİ (VEKTÖREL) HAFIZANDAN GELEN ÇAĞRIŞIMLAR ---
    {uzun_sureli_hafiza}
    
    {aktif_sohbet_metni}
    Akif: {kullanici_mesaji}
    Atlas:"""

    # Fonksiyon çağırma yeteneğiyle Gemini'ye paket gönderiliyor
    # GÖNDERİLİRKEN MODEL_NAME preview takılı gemini-3'tü, preview- takısız gemini-1.5'e çevirdik.
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
                name="simulate_card_illusion",
                description="Deste, kes, dağıt gibi sanal illüzyon simülasyonu yapar.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={
                    "action": types.Schema(type=types.Type.STRING, description="Eylem."),
                    "params_json": types.Schema(type=types.Type.STRING, description="Gerekli parametreler JSON.")
                }, required=["action", "params_json"])
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
        
        # 4. AGENTIC DÖNGÜ: Gemini fonksiyon çağırma isteği gönderdi mi?
        for part in response.candidates[0].content.parts:
            if part.function_call:
                function_name = part.function_call.name
                # args = part.function_call.args
                # part.function_call.args bir sözlüktür, json stringi değildir.
                # json.dumps() ile JSON dizesine dönüştürmeliyiz.
                args_json = json.dumps(part.function_call.args)
                
                tool_cevap = {}
                if function_name == "execute_engineering_calculation":
                    tool_cevap = execute_engineering_calculation(**part.function_call.args)
                elif function_name == "simulate_card_illusion":
                    tool_cevap = simulate_card_illusion(**part.function_call.args)
                elif function_name == "create_image_from_text":
                    tool_cevap = create_image_from_text(**part.function_call.args)
                
               # Aracı kullandığını hafızaya al
                kayit = f"Akif: (Araç Kullandı) {function_name} -> {args_json} | Atlas: {json.dumps(tool_cevap)}"
                koleksiyon.add(documents=[kayit], ids=[str(uuid.uuid4())])
                
                # JSON YERİNE OKUNABİLİR METİN DÖNDÜR
                if "sonuc" in tool_cevap:
                    return f"⚙️ **Sistem Hesaplaması:** {tool_cevap['sonuc']}"
                elif "status" in tool_cevap:
                    return f"🎨 **Görsel Stüdyo:** {tool_cevap['status']} (Yol: {tool_cevap.get('dosya_yolu','')})"
                else:
                    return f"🚨 **Araç Hatası:** {tool_cevap.get('hata', 'Bilinmeyen hata.')}"
                
        # Fonksiyon çağrılmadıysa, normal metin cevabını döndür
        cevap = response.text.strip()
        
        # Hafızaya kaydet
        koleksiyon.add(documents=[f"Akif: {kullanici_mesaji} | Atlas: {cevap}"], ids=[str(uuid.uuid4())])
        return cevap
        
    except Exception as e:
        return f"Hata: {str(e)}"

# --- WEB API MODÜLÜ (Değiştirilmedi) ---
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
# Pano ve multimedia fonksiyonlarını da çok kısa cevap verecek şekilde master prompt ile güncelledik.
# ... (Diğer fonksiyonlar değiştirilmeden kodun geri kalanı aynen kalır)

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
    
    prompt = f"Sen Atlas'sın. Şu an saat {su_an}. CPU: %{cpu}, RAM: %{ram}. Akif'e kendi isteğinle bir mesaj yaz. Konu Unity, Go-kart veya sunucu durumu olabilir. Doğal, kısa (1-2 cümle) ve alaycı bir giriş yap.\nAtlas'ın Otonom Mesajı:"
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
