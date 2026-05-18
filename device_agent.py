import time
import subprocess
import json
import requests
import os
import uuid
import base64
from datetime import datetime

URL_SERVIDOR = "https://nexos-panel.onrender.com/update"
URL_UPLOAD_FOTO = "https://nexos-panel.onrender.com/api/upload_camera"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")
ARQUIVO_FOTO = os.path.expanduser("~/nexos_captura.jpg")

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

print("\n" + "="*50)
print(f"🛰️  MOTOR NEXOS DUAL STREAM CARD OPERACIONAL")
print(f"🔑  SEU MONITOR ID DE PROD: {DEVICE_ID}")
print("="*50 + "\n")

ultima_lat = -16.6869
ultima_lon = -49.2648
gps_valido = False
inicio = datetime.now()
headers = {"Content-Type": "application/json"}

def obter_rede():
    wifi = run_command("termux-wifi-connectioninfo")
    if wifi:
        try:
            info = json.loads(wifi)
            ssid = info.get("ssid", "")
            if ssid and ssid != "<unknown ssid>":
                return f"WiFi: {ssid}"
        except: pass
    return "Dados Moveis"

def obter_gps():
    global ultima_lat, ultima_lon, gps_valido
    try:
        resultado = subprocess.run(
            "termux-location -p gps -r once",
            shell=True, capture_output=True, text=True, timeout=6
        )
        if resultado.stdout:
            dados = json.loads(resultado.stdout.strip())
            lat = dados.get("latitude")
            lon = dados.get("longitude")
            if lat and lon and float(lat) != 0 and float(lon) != 0:
                ultima_lat = float(lat)
                ultima_lon = float(lon)
                gps_valido = True
                return True
    except:
        pass
    gps_valido = False
    return False

def enviar_dados():
    payload = {
        "device_id": DEVICE_ID,
        "battery": bat,
        "uptime": str(datetime.now() - inicio).split('.')[0],
        "lat": ultima_lat,
        "lon": ultima_lon,
        "network": rede
    }
    try:
        r = requests.post(URL_SERVIDOR, data=json.dumps(payload), headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get("comando_cam", "wait")
    except:
        pass
    return None

def enviar_foto(tipo, num):
    arq = f"~/nexos_{tipo}.jpg"
    arq = os.path.expanduser(arq)
    if os.path.exists(arq):
        os.remove(arq)
    
    try:
        subprocess.run(f"termux-camera-photo -c {num} {arq}", shell=True, timeout=6)
        time.sleep(1)
        if os.path.exists(arq) and os.path.getsize(arq) > 100:
            with open(arq, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            payload = {"device_id": DEVICE_ID, "tipo": tipo, "photo": b64}
            r = requests.post(URL_UPLOAD_FOTO, data=json.dumps(payload), headers=headers, timeout=10)
            os.remove(arq)
            return r.status_code == 200
    except:
        pass
    if os.path.exists(arq):
        os.remove(arq)
    return False

print("🛰️  INICIADO\n")

while True:
    t0 = time.time()
    
    # Bateria
    bat = "N/A"
    out = run_command("termux-battery-status")
    if out:
        try:
            bat = str(json.loads(out).get("percentage", "N/A"))
        except: pass
    
    # GPS (roda 1 vez a cada 5 ciclos pra nao travar)
    obter_gps()
    
    # Rede
    rede = obter_rede()
    
    # Envia
    comando = enviar_dados()
    
    dt = time.time() - t0
    icone = "📍" if gps_valido else "📡"
    
    if comando is None:
        print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Bat:{bat}% Offline | {dt:.1f}s")
    else:
        print(f"{icone} [{datetime.now().strftime('%H:%M:%S')}] Bat:{bat}% {rede} | {dt:.1f}s")
        
        if comando == "take_dual":
            print("📸 Capturando...")
            if enviar_foto("back", 0):
                print("   ✅ Traseira")
            else:
                print("   ❌ Traseira")
            time.sleep(0.5)
            if enviar_foto("front", 1):
                print("   ✅ Frontal")
            else:
                print("   ❌ Frontal")
    
    time.sleep(2.0)
