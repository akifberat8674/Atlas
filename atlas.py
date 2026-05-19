import random

def atlas_konus(durum, cpu):
    sozluk = {
        "normal": [f"Sistem stabil, CPU {cpu}%. Atlas huzurlu."],
        "yorgun": [f"CPU {cpu}%. Atlas biraz yoruldu, uyumak istiyor..."],
        "meraklı": [f"Hey! CPU {cpu}% olmuş. Neler dönüyor burada?"]
    }
    return random.choice(sozluk.get(durum, ["..."]))

# Test
print(atlas_konus("meraklı", 15))
