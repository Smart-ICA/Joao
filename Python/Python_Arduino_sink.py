import os
# Use the headless Agg backend before importing pyplot
os.environ['MPLBACKEND'] = 'Agg'

import json
from collections import deque
import matplotlib.pyplot as plt

# Specify that this is a sink agent
agent_type = "sink"

def setup():
    """
    Called once when the sink starts.
    Initializes buffers, figure, axes and lines.
    """
    print("[Python] Setting up sink...")
    print("[Python] Parameters: " + json.dumps(params))
    print("[Python] Topic: " + topic)

    # Max number of points to keep (can be overridden in params)
    max_len = params.get("max_len", 100)
    # Path to save the live plot image
    state['output_path'] = params.get("output_path", "/tmp/live_plot.png")

    # ——— Buffers ———
    state['t_data']     = deque(maxlen=max_len)
    state['X']          = deque(maxlen=max_len)
    state['Y']          = deque(maxlen=max_len)
    state['Z']          = deque(maxlen=max_len)
    state['magnitude']  = deque(maxlen=max_len)
    state['vibration']  = deque(maxlen=max_len)
    state['sht31_temp'] = deque(maxlen=max_len)
    state['sht31_hum']  = deque(maxlen=max_len)
    state['dht_temp']   = deque(maxlen=max_len)
    state['dht_hum']    = deque(maxlen=max_len)
    state['sound_level']= deque(maxlen=max_len)

    # ——— Figure & Axes ———
    fig, axes = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
    state['fig']  = fig
    state['axes'] = axes

    lines = []
    # 1) Accelerometer X/Y/Z
    axes[0].set_ylabel('Accel (g)')
    lines += axes[0].plot([], [], label='X')
    lines += axes[0].plot([], [], label='Y')
    lines += axes[0].plot([], [], label='Z')
    axes[0].legend(loc='upper right')

    # 2) Magnitude / Vibration
    axes[1].set_ylabel('Magnitude / Vib')
    lines += axes[1].plot([], [], label='Magnitude')
    lines += axes[1].plot([], [], label='Vibration')
    axes[1].legend(loc='upper right')

    # 3) Temperatures
    axes[2].set_ylabel('Temperature (°C)')
    lines += axes[2].plot([], [], label='SHT31 Temp')
    lines += axes[2].plot([], [], label='DHT Temp')
    axes[2].legend(loc='upper right')

    # 4) Humidities
    axes[3].set_ylabel('Humidity (%)')
    lines += axes[3].plot([], [], label='SHT31 Hum')
    lines += axes[3].plot([], [], label='DHT Hum')
    axes[3].legend(loc='upper right')

    # 5) Sound Level
    axes[4].set_ylabel('Sound Level')
    lines += axes[4].plot([], [], label='Sound')
    axes[4].set_xlabel('Time (ms)')
    axes[4].legend(loc='upper right')

    state['lines'] = lines

    # Layout tweak
    plt.tight_layout()


def deal_with_data():
    """
    Called for each incoming data packet.
    Updates buffers, redraws lines, adjusts axes, and saves the plot.
    """
    # Parse incoming data
    try:
        t = data['millis']
        d = data['data']
    except (KeyError, TypeError):
        return

    # Append to buffers
    state['t_data'].append(t)
    state['X'].append(d['X']);    state['Y'].append(d['Y']);    state['Z'].append(d['Z'])
    state['magnitude'].append(d['magnitude'])
    state['vibration'].append(d['vibration'])
    state['sht31_temp'].append(d['sht31_temperature'])
    state['sht31_hum'].append(d['sht31_humidity'])
    state['dht_temp'].append(d['dht_temperature'])
    state['dht_hum'].append(d['dht_humidity'])
    state['sound_level'].append(d['sound_level'])

    # Update each line in order
    idx = 0
    def upd(series):
        nonlocal idx
        state['lines'][idx].set_data(state['t_data'], series)
        idx += 1

    for series in (
        state['X'], state['Y'], state['Z'],
        state['magnitude'], state['vibration'],
        state['sht31_temp'], state['dht_temp'],
        state['sht31_hum'], state['dht_hum'],
        state['sound_level'],
    ):
        upd(series)

    # Adjust axes limits and autoscale
    t_min, t_max = min(state['t_data']), max(state['t_data'])
    for ax in state['axes']:
        ax.set_xlim(t_min, t_max)
        ax.relim()
        ax.autoscale_view()

    # Redraw canvas and save headless image
    state['fig'].canvas.draw()
    output_path = state['output_path']
    state['fig'].savefig(output_path)
    print(f"[Python] Saved live plot to {output_path}")