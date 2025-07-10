import os
os.environ['QT_QPA_PLATFORM'] = 'xcb'

import json
from collections import deque
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ——— Specifies that this script is a sink agent ———
agent_type = "sink"

def setup():
    """
    Called once at sink initialization.
    Initializes deques, creates figure/axes/lines and enables interactive mode.
    """
    print("[Python] Setting up sink...")
    print("[Python] Parameters: " + json.dumps(params))
    print("[Python] Topic: " + topic)

    # how many samples to store and display
    max_len   = params.get("max_len", 20)
    view_len  = params.get("view_len", max_len)
    state['view_len'] = view_len

    # ——— data buffers ———
    keys = [
        't_data','X','Y','Z','magnitude','vibration',
        'sht31_temp','sht31_hum','dht_temp','dht_hum','sound_level'
    ]
    for k in keys:
        state[k] = deque(maxlen=max_len)

    # ——— matplotlib + GridSpec setup ———
    plt.ion()
    fig = plt.figure(figsize=(10, 14))
    gs  = gridspec.GridSpec(
        6, 1,
        height_ratios=[1,1,1,1,1, 0.4],
        bottom=0.05, top=0.95, left=0.08, right=0.98
    )

    # five axes for the plots
    axes = [fig.add_subplot(gs[i,0]) for i in range(5)]
    # single axis for the values table
    table_ax = fig.add_subplot(gs[5,0])
    table_ax.axis('off')

    state['fig']      = fig
    state['axes']     = axes
    state['table_ax'] = table_ax

    # ——— Create empty lines and legends on the left ———
    lines = []
    # 1) Acceleration X/Y/Z
    axes[0].set_ylabel('Accel (g)')
    lines += axes[0].plot([], [], label='X')
    lines += axes[0].plot([], [], label='Y')
    lines += axes[0].plot([], [], label='Z')
    axes[0].legend(loc='upper left')

    # 2) Magnitude / Vibration
    axes[1].set_ylabel('Magnitude / Vib')
    lines += axes[1].plot([], [], label='Magnitude')
    lines += axes[1].plot([], [], label='Vibration')
    axes[1].legend(loc='upper left')

    # 3) Temperatures
    axes[2].set_ylabel('Temperature (°C)')
    lines += axes[2].plot([], [], label='SHT31 Temp')
    lines += axes[2].plot([], [], label='DHT Temp')
    axes[2].legend(loc='upper left')

    # 4) Humidity
    axes[3].set_ylabel('Humidity (%)')
    lines += axes[3].plot([], [], label='SHT31 Hum')
    lines += axes[3].plot([], [], label='DHT Hum')
    axes[3].legend(loc='upper left')

    # 5) Sound level
    axes[4].set_ylabel('Sound Level')
    lines += axes[4].plot([], [], label='Sound')
    axes[4].set_xlabel('Time (ms)')
    axes[4].legend(loc='upper left')

    state['lines'] = lines

    fig.tight_layout()
    fig.show()


def deal_with_data():
    """
    Called whenever a new data packet arrives.
    Updates buffers, redraws lines, adjusts axes and the values table.
    """
    try:
        t = data['millis']
        d = data['data']
    except (KeyError, TypeError):
        return

    # append to deques
    state['t_data'].append(t)
    state['X'].append(d['X']);    state['Y'].append(d['Y']);    state['Z'].append(d['Z'])
    state['magnitude'].append(d['magnitude'])
    state['vibration'].append(d['vibration'])
    state['sht31_temp'].append(d['sht31_temperature'])
    state['sht31_hum'].append(d['sht31_humidity'])
    state['dht_temp'].append(d['dht_temperature'])
    state['dht_hum'].append(d['dht_humidity'])
    state['sound_level'].append(d['sound_level'])

    # prepare display window (only the last view_len samples)
    times = list(state['t_data'])
    n     = len(times)
    v     = state['view_len']
    start = max(0, n - v)
    t_win = times[start:]

    # update each line in the plot
    idx = 0
    def upd(series):
        nonlocal idx
        vals = list(series)[start:]
        state['lines'][idx].set_data(t_win, vals)
        idx += 1

    for series in (
        state['X'], state['Y'], state['Z'],
        state['magnitude'], state['vibration'],
        state['sht31_temp'], state['dht_temp'],
        state['sht31_hum'], state['dht_hum'],
        state['sound_level'],
    ):
        upd(series)

    # adjust axes limits
    if t_win:
        xmin, xmax = t_win[0], t_win[-1]
        for ax in state['axes']:
            ax.set_xlim(xmin, xmax)
            ax.relim()
            ax.autoscale_view()

    # — update table with the latest values —
    labels = [
        'X','Y','Z','Magnitude','Vibration',
        'SHT31 Temp','DHT Temp','SHT31 Hum','DHT Hum','Sound'
    ]
    latest = [
        state['X'][-1], state['Y'][-1], state['Z'][-1],
        state['magnitude'][-1], state['vibration'][-1],
        state['sht31_temp'][-1], state['dht_temp'][-1],
        state['sht31_hum'][-1], state['dht_hum'][-1],
        state['sound_level'][-1]
    ]

    ax_table = state['table_ax']
    ax_table.clear()
    ax_table.axis('off')

    tbl = ax_table.table(
        cellText=[[f"{v:.2f}" for v in latest]],
        colLabels=labels,
        loc='center'
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.5)

    # draw on the GUI
    state['fig'].canvas.draw()
    state['fig'].canvas.flush_events()
