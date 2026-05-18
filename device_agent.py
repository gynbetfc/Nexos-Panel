import time
import subprocess
import json
import requests
import os
import uuid
import base64
import glob

URL_SERVIDOR = "https://nexos-panel.onrender.com/update"
URL_UPLOAD_AUDIO = "https://nexos-panel.onrender.com/api/upload_audio"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")

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
print(f"🛰️  MOTOR NEXOS AUDIO COMPRESSED // LIGHTWEIGHT")
print(f"🔑  SEU MONITOR ID DE PROD: {DEVICE_ID}")
print("="*45 + "\n")

ultima_lat_valida = -16.6869
ultima_lon_valida = -49.2648
headers_json = {"Content-Type": "application/json"}

while True:
    # 1. Bateria
    battery = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try: battery = str(json.loads(out_bat).get("percentage", "N/A"))
        except: pass
        
    # 2. Armazenamento
    storage = "N/A"
    out_df = run_command("df -h /data/data/com.termux/files/home")
    if out_df:
        try:
            lines = out_df.split("\n")
            if len(lines) > 1:
                parts = [p for p in lines[1].split(" ") if p]
                if len(parts) >= 3: storage = f"{parts[3]} livres"
        except: pass

    # 3. GPS
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

    # 4. Sincronismo Geral
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
            print(f"🛰️ [OK] Sincronizado. Status Escuta: {comando_audio.upper()}")
            
            if comando_audio == "start":
                print("🎙️ [AÇÃO] Gravando em modo ultra-leve (Bitrate Reduzido)...")
                run_command("termux-microphone-record -q")
                
                # NOVIDADE: Força o Android a gravar em 16kbps (qualidade de rádio/fone), reduzindo o peso em 90%
                run_command("termux-microphone-record --bitrate 16000")
                
                time.sleep(3.0) 
                run_command("termux-microphone-record -q")
                print("🎙️ [AÇÃO] Gravacao finalizada.")
                
                # Caça o arquivo gerado
                arquivos_gravados = glob.glob("/storage/emulated/0/TermuxAudioRecording_*.m4a")
                if arquivos_gravados:
                    ultimo_audio = max(arquivos_gravados, key=os.path.getctime)
                    
                    if os.path.exists(ultimo_audio) and os.path.getsize(ultimo_audio) > 0:
                        with open(ultimo_audio, "rb") as audio_file:
                            audio_b64 = base64.b64encode(audio_file.read()).decode('utf-8')
                        
                        # Transmite com margem de segurança de 10 segundos para conexões oscilantes de motoboy
                        payload_audio = {"device_id": DEVICE_ID, "audio": audio_b64}
                        requests.post(URL_UPLOAD_AUDIO, data=json.dumps(payload_audio), headers=headers_json, timeout=10)
                        print("🚀 [OK] Lote de áudio ultra-leve enviado pro painel!")
                        
                        os.remove(ultimo_audio)
                        
    except Exception as e:
        print(f"⚠️ Alerta de ciclo: {e}")

    time.sleep(2.0)
