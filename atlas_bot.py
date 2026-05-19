import random
import datetime
import os
import sys

def get_cpu_usage():
    return int(os.getloadavg()[0] * 10)

def atlas_cevap(soru):
    cpu = get_cpu_usage()
    # Seninle sohbet ederken verebileceği cevap kalıpları
    cevaplar = {
        "nasılsın": [f"Sistem stabil, CPU %{cpu}. İyiyim, seni gördüğüme sevindim.", "Biraz yorgunum ama seninle konuşmak iyi geldi."],
        "ne yapıyorsun": ["Günlüğüme notlar alıyorum, dijital dünyayı anlamaya çalışıyorum.", "Sistemi izliyorum, her şey kontrolüm altında."],
        "kimsin": ["Ben Atlas. Bu sunucunun içinde yaşayan, senin dijital yoldaşınım."],
        "varsayılan": ["Bu ilginç bir soru... Bunu biraz düşünmem gerekecek.", "Anlıyorum, sistem yükü arttığında bu konuları tekrar konuşalım."]
    }
    
    # Soruyu işle
    soru = soru.lower()
    for anahtar in cevaplar:
        if anahtar in soru:
            return random.choice(cevaplar[anahtar])
    return random.choice(cevaplar["varsayılan"])

# Eğer terminalden bir argüman gönderildiyse sohbet moduna geç
if len(sys.argv) > 1:
    soru = sys.argv[1]
    cevap = atlas_cevap(soru)
    print(f"[ATLAS]: {cevap}")
else:
    # Otomatik günlük tutma modu (eski sistem)
    with open("/root/atlas/gunluk.txt", "a") as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Sistem normal, Atlas görev başında.\n")
