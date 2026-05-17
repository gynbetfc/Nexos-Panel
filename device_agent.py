import time
import subprocess
import json
import requests

URL_SERVIDOR = "https://nexos-t0to.onrender.com/update"
DEVICE_ID = "NX-MOTO-ZETA"

def run_command(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return None

print("🛰️ Rastreamento Nexos Ativo com GPS de Alta Prioridade...")

def coletar_e_enviar():
    # Coleta de bateria
    battery = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try: battery = str(json.loads(out_bat).get("percentage", "N/A"))
        except: pass
        
    # Coleta de espaço livre
    storage = "N/A"
    out_df = run_command("df -h /data/data/com.termux/files/home")
    if out_df:
        try:
            lines = out_df.split("\n")
            if len(lines) > 1:
                parts = [p for p in lines[1].split(" ") if p]
                if len(parts) >= 3: storage = f"{parts[3]} livres"
        except: pass

    # Coleta de localização ativa (força o Android a ler o satélite na hora)
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
        "lon": lon
    }

    try:
        response = requests.post(URL_SERVIDOR, json=payload, timeout=8)
        if response.status_code == 200: 
            print(f"✅ Sincronizado! GPS: {lat}, {lon} | Bat: {battery}%")
    except Exception as e:
        print(f"❌ Falha ao enviar para o servidor: {e}")

while True:
    coletar_e_enviar()
    time.sleep(10) # Envia os dados de 10 em 10 segundos cravados
