import os
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Banco de dados temporário em memória para suportar múltiplos dispositivos simultâneos
db_dispositivos = {}

HTML_DASHBOARD = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXOS CORE // MONITORING</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #070f15; color: #e2e8f0; font-family: 'Courier New', monospace; padding: 15px; }
        .wrapper { max-width: 600px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 20px; padding: 10px; border-bottom: 2px solid #1e293b; }
        .header h1 { font-size: 22px; color: #38bdf8; letter-spacing: 3px; font-weight: bold; }
        .device-section { border: 1px solid #1e293b; border-radius: 12px; background: #0d1925; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
        .device-title { font-size: 14px; color: #38bdf8; text-transform: uppercase; border-bottom: 1px solid #1e293b; padding-bottom: 6px; margin-bottom: 12px; display: flex; justify-content: space-between; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
        .info-box { background: #070f15; border: 1px solid #1e293b; padding: 10px; border-radius: 6px; }
        .info-box span { font-size: 11px; color: #64748b; display: block; text-transform: uppercase; }
        .info-box strong { font-size: 16px; color: #f1f5f9; }
        .map-container { width: 100%; height: 280px; border-radius: 8px; background: #040a0f; border: 1px solid #1e293b; }
        .status-tag { background: #166534; color: #4ade80; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        .no-data { text-align: center; padding: 40px; color: #64748b; }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <h1>NEXOS // CORE SYSTEMS</h1>
        </div>
        
        {% if not dispositivos %}
            <div class="device-section no-data">
                <h3>AGUARDANDO CONEXÃO DE DISPOSITIVOS...</h3>
                <p style="font-size: 12px; margin-top: 10px;">Nenhum sinal recebido pelo Termux ainda.</p>
            </div>
        {% endif %}

        {% for dev_id, info in dispositivos.items() %}
            <div class="device-section">
                <div class="device-title">
                    <span>ID: {{ dev_id }}</span>
                    <span class="status-tag">ONLINE</span>
                </div>
                <div class="info-grid">
                    <div class="info-box"><span>Bateria</span><strong style="color: #22c55e;">{{ info.battery }}%</strong></div>
                    <div class="info-box"><span>Espaço Livre</span><strong>{{ info.storage }}</strong></div>
                    <div class="info-box"><span>Uptime</span><strong>{{ info.uptime }}</strong></div>
                    <div class="info-box"><span>Sinal</span><strong style="color: #38bdf8;">100%</strong></div>
                </div>
                <div id="map_{{ dev_id }}" class="map-container"></div>
            </div>

            <script>
                (function() {
                    const lat = {{ info.lat }};
                    const lon = {{ info.lon }};
                    const map = L.map('map_{{ dev_id }}', { zoomControl: false }).setView([lat, lon], 16);
                    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                        attribution: 'Nexos'
                    }).addTo(map);
                    L.marker([lat, lon]).addTo(map);
                })();
            </script>
        {% endfor %}
    </div>

    <script>
        setTimeout(() => { window.location.reload(); }, 15000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_DASHBOARD, dispositivos=db_dispositivos)

@app.route('/update', methods=['POST'])
def update():
    global db_dispositivos
    data = request.json
    if not data or 'device_id' not in data:
        return jsonify({"status": "error", "message": "Missing device_id"}), 400
    
    device_id = data['device_id']
    db_dispositivos[device_id] = {
        "battery": data.get("battery", "N/A"),
        "storage": data.get("storage", "N/A"),
        "uptime": data.get("uptime", "Ativo"),
        "lat": float(data.get("lat", -16.6869)),
        "lon": float(data.get("lon", -49.2648))
    }
    return jsonify({"status": "success", "message": "Data synced"}), 200

if __name__ == '__main__':
    # PEGA A PORTA QUE O RENDER MANDAR DINAMICAMENTE, SE NÃO ACHA, USA A 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
