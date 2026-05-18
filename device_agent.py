import time
import subprocess
import json
import requests
import os
import uuid
import base64
import threading
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL_SERVIDOR = "https://nexos-panel.onrender.com/update"
URL_UPLOAD_FOTO = "https://nexos-panel.onrender.com/api/upload_camera"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")
ARQUIVO_FOTO = os.path.expanduser("~/nexos_captura.jpg")

# Sessao com timeout AGRESSIVO
session = requests.Session()
retry = Retry(total=0, read=0, connect=0)
adapter = HTTPAdapter(max_retries=retry)
session.mount('https://', adapter)

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

POSICAO = {"lat": -16.6869, "lon": -49.2648, "atualizado": False}
posicao_lock = threading.Lock()
headers_json = {"Content-Type": "application/json"}
inicio_operacao = datetime.now()

def obter_status_rede():
    wifi = run_command("termux-wifi-connectioninfo")
    if wifi:
        try:
            info = json.loads(wifi)
            ssid = info.get("ssid", "")
            if ssid and ssid != "<unknown ssid>":
                return f"WiFi: {ssid}"
        except: pass
    return "Dados Moveis"

def thread_gps():
    while True:
        try:
            proc = subprocess.Popen(
                "termux-location -p gps -r once",
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            try:
                stdout, _ = proc.communicate(timeout=5)
                if stdout:
                    dados = json.loads(stdout.decode().strip())
                    lat = dados.get("latitude")
                    lon = dados.get("longitude")
                    if lat and lon and float(lat) != 0 and float(lon) != 0:
                        with posicao_lock:
                            POSICAO["lat"] = float(lat)
                            POSICAO["lon"] = float(lon)
                            POSICAO["atualizado"] = True
            except:
                proc.kill()
        except:
            pass
        time.sleep(8)

def thread_camera(tipo, num):
    try:
        if os.path.exists(ARQUIVO_FOTO):
            os.remove(ARQUIVO_FOTO)
        
        proc = subprocess.Popen(
            f"termux-camera-photo -c {num} {ARQUIVO_FOTO}",
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        try:
            proc.communicate(timeout=5)
        except:
            proc.kill()
        
        time.sleep(1)
        
        if os.path.exists(ARQUIVO_FOTO) and os.path.getsize(ARQUIVO_FOTO) > 100:
            with open(ARQUIVO_FOTO, "rb") as img_file:
                foto_b64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            payload = {"device_id": DEVICE_ID, "tipo": tipo, "photo": foto_b64}
            try:
                r = session.post(URL_UPLOAD_FOTO, data=json.dumps(payload), 
                               headers=headers_json, timeout=(3, 10))
                if r.status_code == 200:
                    print(f"   📸 {tipo} OK")
                else:
                    print(f"   ❌ {tipo} HTTP {r.status_code}")
            except Exception as e:
                print(f"   ❌ {tipo} erro")
        
        if os.path.exists(ARQUIVO_FOTO):
            os.remove(ARQUIVO_FOTO)
    except:
        pass

threading.Thread(target=thread_gps, daemon=True).start()
print("🛰️  LOOP RAPIDO INICIADO\n")

while True:
    t0 = time.time()
    ts = datetime.now()
    
    battery = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try:
            bat_data = json.loads(out_bat)
            battery = str(bat_data.get("percentage", "N/A"))
        except: pass
    
    with posicao_lock:
        lat = POSICAO["lat"]
        lon = POSICAO["lon"]
        gps_ok = POSICAO["atualizado"]
        POSICAO["atualizado"] = False
    
    uptime = str(datetime.now() - inicio_operacao).split('.')[0]
    rede = obter_status_rede()
    
    payload = {
        "device_id": DEVICE_ID,
        "battery": battery,
        "uptime": uptime,
        "lat": lat,
        "lon": lon,
        "network": rede
    }
    
    try:
        # Timeout AGRESSIVO: 3s conectar, 2s ler
        response = session.post(URL_SERVIDOR, data=json.dumps(payload), 
                               headers=headers_json, timeout=(3, 2))
        if response.status_code == 200:
            res_data = response.json()
            comando_cam = str(res_data.get("comando_cam", "wait")).lower()
            
            gps_icon = "📍" if gps_ok else "📡"
            dt = time.time() - t0
            print(f"{gps_icon} [{ts.strftime('%H:%M:%S')}] Bat:{battery}% {rede} | {dt:.1f}s")
            
            if comando_cam == "take_dual":
                print("📸 [DUAL] Disparando cameras...")
                threading.Thread(target=thread_camera, args=("back", 0), daemon=True).start()
                time.sleep(0.3)
                threading.Thread(target=thread_camera, args=("front", 1), daemon=True).start()
    except:
        dt = time.time() - t0
        print(f"📡 [{ts.strftime('%H:%M:%S')}] Offline | {dt:.1f}s")
    
    time.sleep(2.0)
