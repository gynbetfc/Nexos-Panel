import time
import subprocess
import json
import requests
import os
import uuid
import base64
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

URL_SERVIDOR = "https://nexos-panel.onrender.com/update"
URL_UPLOAD_LOTE = "https://nexos-panel.onrender.com/api/upload_lote"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")
ARQUIVO_FOTO_FRONTAL = os.path.expanduser("~/nexos_frontal.jpg")
ARQUIVO_FOTO_TRASEIRA = os.path.expanduser("~/nexos_traseira.jpg")

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
ultimo_gps_valido = None
headers_json = {"Content-Type": "application/json"}
inicio_operacao = datetime.now()

# Cache para evitar leituras repetidas
_cache_temperatura = {"valor": "N/A", "timestamp": datetime.now()}
_cache_rede = {"valor": "WiFi", "timestamp": datetime.now()}
_cache_ram = {"valor": "N/A", "timestamp": datetime.now()}

def obter_temperatura():
    global _cache_temperatura
    agora = datetime.now()
    if (agora - _cache_temperatura["timestamp"]).seconds < 10:
        return _cache_temperatura["valor"]
    
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", 'r') as f:
            temp = int(f.read().strip()) / 1000
            _cache_temperatura = {"valor": f"{temp:.1f}", "timestamp": agora}
            return _cache_temperatura["valor"]
    except:
        return _cache_temperatura["valor"]

def obter_status_rede():
    global _cache_rede
    agora = datetime.now()
    if (agora - _cache_rede["timestamp"]).seconds < 15:
        return _cache_rede["valor"]
    
    wifi = run_command("termux-wifi-connectioninfo")
    if wifi:
        try:
            info = json.loads(wifi)
            ssid = info.get("ssid", "")
            if ssid and ssid != "<unknown ssid>":
                _cache_rede = {"valor": f"WiFi: {ssid}", "timestamp": agora}
                return _cache_rede["valor"]
        except: pass
    _cache_rede = {"valor": "Dados Moveis", "timestamp": agora}
    return _cache_rede["valor"]

def obter_ram():
    global _cache_ram
    agora = datetime.now()
    if (agora - _cache_ram["timestamp"]).seconds < 8:
        return _cache_ram["valor"]
    
    mem = run_command("free -h | grep Mem")
    if mem:
        parts = mem.split()
        if len(parts) >= 4:
            _cache_ram = {"valor": f"{parts[3]} livres", "timestamp": agora}
            return _cache_ram["valor"]
    return _cache_ram["valor"]

def calcular_velocidade(lat1, lon1, lat2, lon2, t1, t2):
    if lat1 == lat2 and lon1 == lon2:
        return "0.0"
    delta_segundos = (t2 - t1).total_seconds()
    if delta_segundos <= 0:
        return "0.0"
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distancia_km = R * c
    velocidade_kmh = (distancia_km / delta_segundos) * 3600
    return f"{velocidade_kmh:.1f}"

def capturar_foto(numero_camera, arquivo_destino):
    if os.path.exists(arquivo_destino):
        os.remove(arquivo_destino)
    run_command(f"termux-camera-photo -c {numero_camera} {arquivo_destino}")
    time.sleep(2)
    if os.path.exists(arquivo_destino) and os.path.getsize(arquivo_destino) > 0:
        with open(arquivo_destino, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    return None

def enviar_fotos_lote(foto_frontal_b64, foto_traseira_b64):
    if not foto_frontal_b64 and not foto_traseira_b64:
        return False
    payload = {
        "device_id": DEVICE_ID,
        "photo_front": foto_frontal_b64 or "",
        "photo_back": foto_traseira_b64 or ""
    }
    try:
        response = requests.post(URL_UPLOAD_LOTE, data=json.dumps(payload), headers=headers_json, timeout=45)
        return response.status_code == 200
    except:
        return False

# Loop principal RÁPIDO
while True:
    timestamp_atual = datetime.now()
    
    # BATERIA - Comando rápido
    battery = "N/A"
    status_bat = "Normal"
    temp_bat = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try:
            bat_data = json.loads(out_bat)
            battery = str(bat_data.get("percentage", "N/A"))
            status_raw = bat_data.get("status", "").upper()
            if "CHARGING" in status_raw: status_bat = "Carregando"
            elif "DISCHARGING" in status_raw: status_bat = "Em uso"
            elif "FULL" in status_raw: status_bat = "Cheia"
            temp_raw = bat_data.get("temperature", 0)
            if temp_raw: temp_bat = f"{float(temp_raw)}"
        except: pass
    
    # ARMAZENAMENTO - Rápido
    storage = "N/A"
    out_df = run_command("df -h /data/data/com.termux/files/home")
    if out_df:
        try:
            lines = out_df.split("\n")
            if len(lines) > 1:
                parts = [p for p in lines[1].split(" ") if p]
                if len(parts) >= 3: storage = f"{parts[3]} livres"
        except: pass
    
    # GPS - SEM ESPERA SE FALHAR
    lat, lon = ultima_lat_valida, ultima_lon_valida
    velocidade = "0.0"
    gps_atualizado = False
    
    out_loc = run_command("termux-location -p gps -r once")
    if out_loc:
        try:
            loc_data = json.loads(out_loc)
            lat_novo = loc_data.get("latitude")
            lon_novo = loc_data.get("longitude")
            if lat_novo and lon_novo and lat_novo != 0 and lon_novo != 0:
                if ultimo_gps_valido:
                    velocidade = calcular_velocidade(ultima_lat_valida, ultima_lon_valida, lat_novo, lon_novo, ultimo_gps_valido, timestamp_atual)
                lat, lon = lat_novo, lon_novo
                ultima_lat_valida, ultima_lon_valida = lat, lon
                ultimo_gps_valido = timestamp_atual
                gps_atualizado = True
        except: pass
    
    # USA CACHE para leituras pesadas
    uptime = str(datetime.now() - inicio_operacao).split('.')[0]
    temperatura = obter_temperatura()
    rede = obter_status_rede()
    ram = obter_ram()
    
    payload = {
        "device_id": DEVICE_ID,
        "battery": battery,
        "battery_status": status_bat,
        "battery_temp": temp_bat,
        "storage": storage,
        "uptime": uptime,
        "lat": lat,
        "lon": lon,
        "speed": velocidade,
        "temperature": temperatura,
        "network": rede,
        "ram": ram,
        "gps_ok": gps_atualizado,
        "timestamp": timestamp_atual.isoformat()
    }
    
    try:
        response = requests.post(URL_SERVIDOR, data=json.dumps(payload), headers=headers_json, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            comando_cam = str(res_data.get("comando_cam", "wait")).lower()
            
            gps_icon = "📍" if gps_atualizado else "📡"
            print(f"{gps_icon} [{timestamp_atual.strftime('%H:%M:%S')}] Bat:{battery}% Vel:{velocidade}km/h {rede}")
            
            if comando_cam == "take_dual":
                print("📸 [DUAL] Capturando...")
                foto_tras = capturar_foto(0, ARQUIVO_FOTO_TRASEIRA)
                foto_front = capturar_foto(1, ARQUIVO_FOTO_FRONTAL)
                print("📤 Enviando lote..." if (foto_tras or foto_front) else "❌ Sem fotos")
                if enviar_fotos_lote(foto_front, foto_tras):
                    print("✅ Fotos enviadas!")
                else:
                    print("❌ Falha")
                for a in [ARQUIVO_FOTO_FRONTAL, ARQUIVO_FOTO_TRASEIRA]:
                    if os.path.exists(a): os.remove(a)
    except Exception as e:
        print(f"⚠️ {str(e)[:50]}")
    
    time.sleep(2.0)
