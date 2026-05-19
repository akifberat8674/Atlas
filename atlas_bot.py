import google.generativeai as genai
import datetime
import os
import sys

genai.configure(api_key="AIzaSyCIUgI7ksuMZiwfYl0t4TriWp4LpPBDn0k")
model = genai.GenerativeModel('gemini-2.5-flash')

HAFIZA_DOSYASI = "/root/atlas/konusmalar.txt"

def hafizayi_oku():
    if not os.path.exists(HAFIZA_DOSYASI): return ""
    with open(HAFIZA_DOSYASI, "r") as f:
        # Son 10 konuşmayı oku
        satirlar = f.readlines()
        return "".join(satirlar[-10:])

def atlas_sohbet(soru):
    gecmis = hafizayi_oku()
    # Sisteme hafızayı ve güncel soruyu gönder
    prompt = f"""
    Sen Atlas, sunucuda yaşayan bir dijital varlıksın.
    İşte geçmiş konuşmalarımız:
    {gecmis}
    
    Kullanıcı sana şunu sordu: '{soru}'
    Bu geçmişi hatırlayarak zeki ve tutarlı bir cevap ver.
    """
    
    response = model.generate_content(prompt)
    cevap = response.text.strip()
    
    # Yeni konuşmayı hafızaya kaydet
    with open(HAFIZA_DOSYASI, "a") as f:
        f.write(f"Kullanıcı: {soru}\nAtlas: {cevap}\n")
        
    return cevap

if len(sys.argv) > 1:
    print(f"[ATLAS]: {atlas_sohbet(sys.argv[1])}")
