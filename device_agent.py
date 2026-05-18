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

ultima_lat_valida = -16.6869
ultima_lon_valida = -49.2648
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

def obter_gps_forcado():
    """Força uma NOVA leitura do GPS a cada chamada"""
    try:
        # Mata qualquer processo de GPS pendente
        run_command("pkill -f termux-location 2>/dev/null")
        time.sleep(0.5)
        
        # Força uma nova consulta
        resultado = run_command("termux-location -p gps -r once")
        
        if resultado:
            dados = json.loads(resultado)
            lat = dados.get("latitude")
            lon = dados.get("longitude")
            
            # Só aceita valores válidos e diferentes de zero
            if lat and lon and float(lat) != 0 and float(lon) != 0:
                return float(lat), float(lon)
    except:
        pass
    
    return None, None

def capturar_e_enviar_foto(tipo, numero_camera):
    if os.path.exists(ARQUIVO_FOTO):
        os.remove(ARQUIVO_FOTO)
    
    run_command(f"termux-camera-photo -c {numero_camera} {ARQUIVO_FOTO}")
    time.sleep(1.5)
    
    if os.path.exists(ARQUIVO_FOTO) and os.path.getsize(ARQUIVO_FOTO) > 0:
        with open(ARQUIVO_FOTO, "rb") as img_file:
            foto_b64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        payload = {"device_id": DEVICE_ID, "tipo": tipo, "photo": foto_b64}
        try:
            response = requests.post(URL_UPLOAD_FOTO, data=json.dumps(payload), headers=headers_json, timeout=30)
            return response.status_code == 200
        except:
            pass
    return False

print("🛰️  INICIANDO MONITORAMENTO GPS...\n")

# Loop principal
while True:
    timestamp_atual = datetime.now()
    
    # BATERIA
    battery = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try:
            bat_data = json.loads(out_bat)
            battery = str(bat_data.get("percentage", "N/A"))
        except: pass
    
    # GPS FORÇADO - Nova leitura a cada ciclo
    lat_novo, lon_novo = obter_gps_forcado()
    
    if lat_novo and lon_novo:
        ultima_lat_valida = lat_novo
        ultima_lon_valida = lon_novo
        gps_ok = True
    else:
        gps_ok = False
    
    # UPTIME
    uptime = str(datetime.now() - inicio_operacao).split('.')[0]
    
    # REDE
    rede = obter_status_rede()
    
    payload = {
        "device_id": DEVICE_ID,
        "battery": battery,
        "uptime": uptime,
        "lat": ultima_lat_valida,
        "lon": ultima_lon_valida,
        "network": rede,
        "gps_ativo": gps_ok,
        "timestamp": timestamp_atual.isoformat()
    }
    
    try:
        response = requests.post(URL_SERVIDOR, data=json.dumps(payload), headers=headers_json, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            comando_cam = str(res_data.get("comando_cam", "wait")).lower()
            
            gps_icon = "📍" if gps_ok else "📡"
            print(f"{gps_icon} [{timestamp_atual.strftime('%H:%M:%S')}] Bat:{battery}% | {rede}")
            if gps_ok:
                print(f"   GPS: {ultima_lat_valida:.6f}, {ultima_lon_valida:.6f}")
            else:
                print(f"   GPS: Aguardando sinal...")
            
            if comando_cam == "take_dual":
                print("📸 [DUAL] Capturando...")
                ok1 = capturar_e_enviar_foto("back", 0)
                time.sleep(0.5)
                ok2 = capturar_e_enviar_foto("front", 1)
                
                if ok1 or ok2:
                    print("   ✅ Fotos enviadas!")
                else:
                    print("   ❌ Falha nas fotos")
                
                if os.path.exists(ARQUIVO_FOTO):
                    os.remove(ARQUIVO_FOTO)
    except Exception as e:
        print(f"⚠️ {str(e)[:50]}")
    
    time.sleep(5.0)
