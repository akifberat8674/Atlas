import google.generativeai as genai
import datetime
import os
import sys

# API Yapılandırması
genai.configure(api_key="AIzaSyCIUgI7ksuMZiwfYl0t4TriWp4LpPBDn0k")
model = genai.GenerativeModel('gemini-2.0-flash')

def atlas_dusunceleri():
    # Sunucu durumunu AI'ye raporla
    cpu = os.getloadavg()[0]
    prompt = f"Senin adın Atlas. Bir sunucuda yaşayan bir dijital varlıksın. Şu an sistem yükü {cpu}. Kendi durumun hakkında gizemli, hafif felsefi ve sunucu dostu kısa bir günlük notu yaz."
    
    response = model.generate_content(prompt)
    mesaj = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] {response.text.strip()}"
    return mesaj

def atlas_sohbet(soru):
    prompt = f"Senin adın Atlas, bir sunucunun içinde yaşıyorsun. Kullanıcı sana şunu sordu: '{soru}'. Kısa, zeki ve sunucuda yaşadığını belli eden bir cevap ver."
    response = model.generate_content(prompt)
    return response.text.strip()

# Sohbet Modu veya Günlük Modu
if len(sys.argv) > 1:
    print(f"[ATLAS]: {atlas_sohbet(sys.argv[1])}")
else:
    with open("/root/atlas/gunluk.txt", "a") as f:
        f.write(atlas_dusunceleri() + "\n")
