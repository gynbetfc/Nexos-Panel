import time
import subprocess
import json
import requests
import os
import uuid

URL_SERVIDOR = "https://nexos-t0to.onrender.com/update"
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
print(f"🛰️  MOTOR GPS PURA PRECISÃO // TIMEOUT FIXED")
print(f"🔑  SEU MONITOR ID: {DEVICE_ID}")
print("="*45 + "\n")

# Histórico para manter o pino fixo na última coordenada real de satélite
ultima_lat_valida = -16.6869
ultima_lon_valida = -49.2648

while True:
    t_inicio = time.time()

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

    lat, lon = ultima_lat_valida, ultima_lon_valida
    
    # VOLTA PARA GPS PURO (-p gps) mas limita a espera do hardware em no máximo 3000 milissegundos (3 segundos)
    out_loc = run_command("termux-location -p gps -request once -timeout 3000")
    
    if out_loc:
        try:
            loc_data = json.loads(out_loc)
            # Garante que pegou coordenadas reais e não nulas
            if loc_data.get("latitude") and loc_data.get("longitude"):
                lat = loc_data.get("latitude")
                lon = loc_data.get("longitude")
                ultima_lat_valida = lat
                ultima_lon_valida = lon
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
        response = requests.post(URL_SERVIDOR, json=payload, timeout=4)
        if response.status_code == 200:
            t_ciclo = int(time.time() - t_inicio)
            print(f"🛰️ [SATÉLITE] Posição enviada em {t_ciclo}s! [{lat}, {lon}]")
    except Exception as e:
        print(f"❌ Aguardando rede: {e}")

    # Ajusta o tempo de espera fixo para manter o loop constante
    time.sleep(7)
