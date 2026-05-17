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
print(f"🛰️  MOTOR DE GPS NEXOS CALIBRADO // FIXO")
print(f"🔑  SEU MONITOR ID CONTINUA: {DEVICE_ID}")
print("="*45 + "\n")

# PASSO MESTRE: Liga a escuta contínua do chip de satélite em segundo plano.
# O Android vai manter o canal do GPS aquecido e ativo o tempo todo!
print("📡 Sintonizando satélites em background...")
subprocess.Popen("termux-location -p gps -r listen", shell=True)
time.sleep(3) # Pequena pausa apenas no início para o hardware sincronizar

while True:
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

    # Puxa instantaneamente a última coordenada real e aquecida do cache de hardware
    # Sem forçar o Android a reiniciar o chip a cada ciclo
    lat, lon = -16.6869, -49.2648
    out_loc = run_command("termux-location -p gps -r last")
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
        response = requests.post(URL_SERVIDOR, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ [AQUECIDO] Sinal enviado: [{lat}, {lon}] | Bat: {battery}%")
    except Exception as e:
        print(f"❌ Aguardando rede: {e}")

    time.sleep(10)
