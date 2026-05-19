import time
import subprocess
import json
import os
import uuid
import base64
from datetime import datetime

URL_SERVIDOR = "https://nexos-panel.onrender.com/update"
URL_UPLOAD_FOTO = "https://nexos-panel.onrender.com/api/upload_camera"
URL_PING = "https://nexos-panel.onrender.com/"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")

def run(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return ""

def obter_id():
    if os.path.exists(ARQUIVO_ID):
        with open(ARQUIVO_ID) as f: return f.read().strip()
    novo = f"NX-{str(uuid.uuid4())[:6].upper()}"
    with open(ARQUIVO_ID, "w") as f: f.write(novo)
    return novo

DEVICE_ID = obter_id()

print("\n" + "="*50)
print(f"🛰️  MOTOR NEXOS DUAL STREAM CARD OPERACIONAL")
print(f"🔑  SEU MONITOR ID DE PROD: {DEVICE_ID}")
print("="*50 + "\n")

ultima_lat = -16.6869
ultima_lon = -49.2648
gps_ok = False
inicio = datetime.now()
ultimo_ping = 0

def obter_rede():
    w = run("termux-wifi-connectioninfo")
    if w:
        try:
            i = json.loads(w)
            s = i.get("ssid","")
            if s and s != "<unknown ssid>": return f"WiFi: {s}"
        except: pass
    return "Dados Moveis"

def obter_gps():
    global ultima_lat, ultima_lon, gps_ok
    out = run("termux-location -p gps -r once", timeout=6)
    if out:
        try:
            d = json.loads(out)
            lat = d.get("latitude")
            lon = d.get("longitude")
            if lat and lon and float(lat) != 0 and float(lon) != 0:
                ultima_lat = float(lat)
                ultima_lon = float(lon)
                gps_ok = True
                return
        except: pass
    gps_ok = False

def post_json(url, data, timeout=5):
    """Usa CURL que respeita timeout no Termux"""
    json_str = json.dumps(data).replace("'", "'\\''")
    cmd = f"curl -s -X POST '{url}' -H 'Content-Type: application/json' -d '{json_str}' --connect-timeout {timeout} --max-time {timeout}"
    resp = run(cmd, timeout=timeout+2)
    try:
        return json.loads(resp)
    except:
        return None

print("🛰️  INICIADO (curl)\n")

while True:
    t0 = time.time()
    
    # PING a cada 4 min
    agora = time.time()
    if agora - ultimo_ping > 240:
        run(f"curl -s -o /dev/null --connect-timeout 10 --max-time 15 {URL_PING}", timeout=12)
        ultimo_ping = agora
    
    # BATERIA
    bat = "N/A"
    out = run("termux-battery-status")
    if out:
        try: bat = str(json.loads(out).get("percentage", "N/A"))
        except: pass
    
    # GPS
    obter_gps()
    
    # REDE
    rede = obter_rede()
    
    # ENVIA DADOS VIA CURL
    payload = {
        "device_id": DEVICE_ID,
        "battery": bat,
        "uptime": str(datetime.now() - inicio).split('.')[0],
        "lat": ultima_lat,
        "lon": ultima_lon,
        "network": rede
    }
    
    resp = post_json(URL_SERVIDOR, payload, timeout=5)
    
    dt = time.time() - t0
    icone = "📍" if gps_ok else "📡"
    
    if resp and resp.get("status") == "success":
        comando = resp.get("comando_cam", "wait")
        print(f"{icone} [{datetime.now().strftime('%H:%M:%S')}] Bat:{bat}% {rede} | {dt:.1f}s")
        
        if comando == "take_dual":
            print("📸 Capturando...")
            for tipo, num in [("back",0), ("front",1)]:
                arq = os.path.expanduser(f"~/nexos_{tipo}.jpg")
                if os.path.exists(arq): os.remove(arq)
                run(f"termux-camera-photo -c {num} {arq}", timeout=6)
                time.sleep(1)
                if os.path.exists(arq) and os.path.getsize(arq) > 100:
                    with open(arq, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                    fp = {"device_id": DEVICE_ID, "tipo": tipo, "photo": b64}
                    r = post_json(URL_UPLOAD_FOTO, fp, timeout=10)
                    print(f"   {'✅' if r else '❌'} {tipo}")
                else:
                    print(f"   ❌ {tipo}")
                if os.path.exists(arq): os.remove(arq)
    else:
        print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Offline | {dt:.1f}s")
    
    time.sleep(2.0)
