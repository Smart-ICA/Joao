'''
This script implements a web-based dashboard to display real-time current readings from an Arduino device.
It uses Flask to serve a simple HTML page that updates the readings every 250 milliseconds.
It expects the data to be in a specific format, with readings for three channels (I1, I2, I3).

To run this script, use the following command:
-> mads python -s tcp://mads-broker.local:9092 -n python_sink -m sink_arduino_web

Where python_sink is the name of the agent (mads.ini), and sink_arduino_web is the name of the script (.py).
'''

import json
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template_string

# === Agent configuration (injected by MADS) ===
agent_type = "sink"
#params = {}
#topic = None
#data = {}

# === Shared state for the latest readings ===
latest_readings = {
    "I1": 0.0,
    "I2": 0.0,
    "I3": 0.0,
    "timestamp": ""
}

# === HTML template with embedded CSS & JS ===
PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Real-Time Current Dashboard</title>
  <style>
    body {
      margin: 0;
      padding: 0;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #eef2f5;
      color: #333;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }
    header {
      background-color: #4a90e2;
      color: white;
      padding: 1rem;
      text-align: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    main {
      flex: 1;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    .card-container {
      display: flex;
      gap: 2rem;
    }
    .card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      width: 250px;
      padding: 1rem;
      text-align: center;
    }
    .label {
      font-size: 1rem;
      text-transform: uppercase;
      margin-bottom: 0.5rem;
      color: #777;
    }
    .value {
      font-size: 5rem;
      font-weight: bold;
      margin: 0;
    }
    footer {
      text-align: center;
      font-size: 0.9rem;
      padding: 0.5rem;
      background-color: #fff;
      border-top: 1px solid #ddd;
    }
  </style>
  <script>
    async function fetchData() {
      try {
        const res = await fetch('/api/readings');
        const json = await res.json();
        document.getElementById('i1').textContent = json.I1.toFixed(2);
        document.getElementById('i2').textContent = json.I2.toFixed(2);
        document.getElementById('i3').textContent = json.I3.toFixed(2);
        document.getElementById('ts').textContent = json.timestamp;
      } catch (err) {
        console.error("Failed to fetch data:", err);
      }
    }
    setInterval(fetchData, 250);
    window.addEventListener('load', fetchData);
  </script>
</head>
<body>
  <header>
    <h1>Real-Time Current Monitor</h1>
  </header>
  <main>
    <div class="card-container">
      <div class="card">
        <div class="label">Channel I1 (A)</div>
        <p class="value" id="i1">0.000</p>
      </div>
      <div class="card">
        <div class="label">Channel I2 (A)</div>
        <p class="value" id="i2">0.000</p>
      </div>
      <div class="card">
        <div class="label">Channel I3 (A)</div>
        <p class="value" id="i3">0.000</p>
      </div>
    </div>
  </main>
  <footer>
    Last update: <span id="ts">–</span>
  </footer>
</body>
</html>
"""

# === Flask application ===
app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string(PAGE_TEMPLATE)

@app.route('/api/readings')
def api_readings():
    return jsonify(latest_readings)

def run_web_server():
    app.run(host='localhost', port=5000, debug=False)

# === MADS agent hooks ===
def setup():
    print("[Python] Starting web dashboard sink...")
    print("[Python] Parameters:", json.dumps(params))
    print("[Python] Topic:", topic)
    threading.Thread(target=run_web_server, daemon=True).start()
    print("[Python] Open your browser at http://<server_ip>:5000")

def deal_with_data():
    global latest_readings
    try:
        payload = data.get('data', {})
        i1 = float(payload.get('I1', 0.0))
        i2 = float(payload.get('I2', 0.0))
        i3 = float(payload.get('I3', 0.0))
    except Exception as e:
        print("[Python] Error parsing data:", e)
        return

    # Update shared state
    latest_readings = {
        "I1": i1,
        "I2": i2,
        "I3": i3,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }