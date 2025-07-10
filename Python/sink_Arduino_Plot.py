'''
This script is a sink agent for visualizing current data from an Arduino device.
It uses Matplotlib to plot the data and display a table of the latest values.

It expects the data to be in a specific format, with timestamps and current values for three channels (I1, I2, I3).

To run this script (in a Raspberry for example), use the following command:
-> mads python -s tcp://mads-broker.local:9092 -n python_sink -m sink_Arduino_Plot

Where python_sink is the name of the agent (mads.ini), and sink_Arduino_Plot is the name of the script (.py).
'''

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
    keys = ['t_data', 'I1', 'I2', 'I3']
    for k in keys:
        state[k] = deque(maxlen=max_len)

    # ——— matplotlib + GridSpec setup ———
    plt.ion()
    fig = plt.figure(figsize=(8, 10))  # increase height for a larger table area
    gs  = gridspec.GridSpec(
        2, 1,
        height_ratios=[4, 2],           # give the table more space
        bottom=0.05, top=0.95, left=0.08, right=0.95
    )

    # one axis for the current plots
    axes = [fig.add_subplot(gs[0, 0])]
    # one axis for the table of latest values
    table_ax = fig.add_subplot(gs[1, 0])
    table_ax.axis('off')

    state['fig']      = fig
    state['axes']     = axes
    state['table_ax'] = table_ax

    # ——— Create empty lines and legend ———
    lines = []
    axes[0].set_ylabel('Current (A)')
    axes[0].set_xlabel('Time (ms)')
    lines += axes[0].plot([], [], label='I1')
    lines += axes[0].plot([], [], label='I2')
    lines += axes[0].plot([], [], label='I3')
    axes[0].legend(loc='upper left')

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

    # append to buffers
    state['t_data'].append(t)
    state['I1'].append(d['I1'])
    state['I2'].append(d['I2'])
    state['I3'].append(d['I3'])

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

    for series in (state['I1'], state['I2'], state['I3']):
        upd(series)

    # adjust axes limits
    if t_win:
        xmin, xmax = t_win[0], t_win[-1]
        for ax in state['axes']:
            ax.set_xlim(xmin, xmax)
            ax.relim()
            ax.autoscale_view()

    # — update table with the latest values —
    labels = ['I1', 'I2', 'I3']
    latest = [state['I1'][-1], state['I2'][-1], state['I3'][-1]]

    ax_table = state['table_ax']
    ax_table.clear()
    ax_table.axis('off')

    tbl = ax_table.table(
        cellText=[[f"{v:.2f}" for v in latest]],
        colLabels=labels,
        loc='center',
        cellLoc='center',   # center the cell contents
        colLoc='center'     # center the column labels
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(20)
    tbl.scale(1, 4)

    # draw on the GUI
    state['fig'].canvas.draw()
    state['fig'].canvas.flush_events()
