import time
import subprocess
import json
import requests
import os
import base64
import uuid

URL_SERVIDOR = "https://nexos-t0to.onrender.com/update"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")
ARQUIVO_AUDIO = os.path.expanduser("~/grampo.wav")

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
print(f"🤖 ECOSSISTEMA NEXOS COM COMANDO REMOTO ATIVO!")
print(f"🔑 TARGET ID DO SEU APARELHO: {DEVICE_ID}")
print("="*45 + "\n")

def executar_ciclo():
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

    # GPS Estável Tradicional (Garante o pino cravado de forma leve)
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
        "audio_b64": "" # Envia em branco no fluxo normal
    }

    try:
        response = requests.post(URL_SERVIDOR, json=payload, timeout=8)
        if response.status_code == 200:
            print(f"📡 Sinal GPS OK! [{lat}, {lon}] | Bateria: {battery}%")
            
            # CHECA SE O SITE MANDOU GRAVAR ÁUDIO
            dados_resposta = response.json()
            if dados_resposta.get("comando_gravacao") == True:
                print("🎙️ [ORDEM RECEBIDA] Gravando 30 segundos de áudio ambiental...")
                run_command("termux-microphone-record -q")
                if os.path.exists(ARQUIVO_AUDIO): os.remove(ARQUIVO_AUDIO)
                
                # Inicia a gravação e faz o Python esperar os 30s solicitados
                subprocess.Popen(f"termux-microphone-record -f {ARQUIVO_AUDIO}", shell=True)
                time.sleep(30)
                run_command("termux-microphone-record -q")
                
                # Transforma o áudio .wav bruto e joga no servidor imediato
                if os.path.exists(ARQUIVO_AUDIO) and os.path.getsize(ARQUIVO_AUDIO) > 500:
                    with open(ARQUIVO_AUDIO, "rb") as f:
                        payload["audio_b64"] = base64.b64encode(f.read()).decode('utf-8')
                    
                    requests.post(URL_SERVIDOR, json=payload, timeout=15)
                    print("✅ Áudio de 30s transmitido com sucesso pro site!")
                    
    except Exception as e:
        print(f"❌ Erro de rede: {e}")

# Loop limpo e leve a cada 10 segundos
while True:
    executar_ciclo()
    time.sleep(10)
