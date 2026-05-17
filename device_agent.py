import time
import subprocess
import json
import requests
import sys

URL_SERVIDOR = "https://nexos-t0to.onrender.com/update"

def run_command(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return ""

def extrair_id_unico():
    # 1. TENTATIVA: Pegar o número do chip/telefone (via API do Termux se tiver permissão)
    out_telephony = run_command("termux-telephony-deviceinfo")
    if out_telephony:
        try:
            tele_data = json.loads(out_telephony)
            # Tenta buscar o número da linha ou o ID do assinante do chip
            num_sim = tele_data.get("phone_number") or tele_data.get("subscriber_id")
            if num_sim and num_sim != "unknown" and len(num_sim) > 3:
                return f"NX-CHIP-{num_sim[-8:].upper()}" # Usa os últimos 8 dígitos do chip
        except: pass

    # 2. TENTATIVA: Se o chip falhar, pega o Serial de Hardware do Android
    serial = run_command("getprop ro.serialno")
    if serial and serial != "unknown" and len(serial) > 3:
        return f"NX-SERIAL-{serial.upper()}"

    # 3. TENTATIVA: Se o serial falhar, pega o Secure Android ID (Único por aparelho)
    android_id = run_command("settings get secure android_id")
    if android_id and android_id != "unknown" and len(android_id) > 3:
        return f"NX-ID-{android_id[:10].upper()}"

    # CADASTRADO DE EMERGÊNCIA (Se tudo der negado no Android)
    return "NX-DISP-DESCONHECIDO"

# GERA E MOSTRA O ID LOGO NO ARRANQUE DO SCRIPT
DEVICE_ID = extrair_id_unico()

print("\n" + "="*45)
print(f"🤖  SISTEMA NEXOS INICIADO COM SUCESSO!")
print(f"🔑  SEU TARGET ID ÚNICO É: {DEVICE_ID}")
print("👉  COPIE ESTE ID E COLOQUE NO SITE PARA RASTREAR")
print("="*45 + "\n")

def coletar_e_enviar():
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

    lat, lon = -16.6869, -49.2648
    out_loc = run_command("termux-location -p gps -r once")
    if out_loc:
        try:
            loc_data = json.loads(out_loc)
            lat = loc_data.get("latitude", lat)
            lon = loc_data.get("longitude", lon)
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
        response = requests.post(URL_SERVIDOR, json=payload, timeout=8)
        if response.status_code == 200: 
            print(f"📡 Sinal enviado! Posição: {lat}, {lon} | Bat: {battery}%")
    except Exception as e:
        print(f"❌ Falha de comunicação: {e}")

while True:
    coletar_e_enviar()
    time.sleep(10)
