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
    # Se já existir o ID salvo no celular, apenas lê ele para manter sempre o mesmo
    if os.path.exists(ARQUIVO_ID):
        with open(ARQUIVO_ID, "r") as f:
            return f.read().strip()
    
    # Se não existir (primeira vez rodando), gera um ID aleatório ultra seguro de 6 dígitos
    novo_id = f"NX-{str(uuid.uuid4())[:6].upper()}"
    
    # Salva no arquivo para as próximas vezes
    with open(ARQUIVO_ID, "w") as f:
        f.write(novo_id)
    return novo_id

# ATRIBUI O ID ALEATÓRIO SALVO
DEVICE_ID = obter_ou_criar_id_unico()

print("\n" + "="*45)
print(f"🤖  SISTEMA NEXOS INICIADO COM SUCESSO!")
print(f"🔑  SEU TARGET ID ÚNICO E EXCLUSIVO É: {DEVICE_ID}")
print("👉  COPIE ESTE ID E COLOQUE NO SITE PARA RASTREAR")
print("="*45 + "\n")

def coletar_e_enviar():
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
        "lon": lon
    }

    try:
        response = requests.post(URL_SERVIDOR, json=payload, timeout=8)
        if response.status_code == 200: 
            print(f"📡 Sinal enviado! Posição: {lat}, {lon} | Bat: {battery}%")
    except Exception as e:
        print(f"❌ Falha de comunicação: {e}")

while True:
    coletar_e_enviar()
    time.sleep(10)
