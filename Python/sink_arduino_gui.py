'''
This is a Python sink for the Arduino GUI.
It displays the current values of three channels (I1, I2, I3) in
large ASCII art format using the `pyfiglet` library.

You can install `pyfiglet` using pip:
-> pip install pyfiglet

To run this script, use the following command:
-> mads python -s tcp://mads-broker.local:9092 -n python_sink -m sink_arduino_gui

Where `python_sink` is the name of the agent (mads.ini), 
and `sink_arduino_gui` is the name of the script (.py).
'''

import json
import os
from pyfiglet import Figlet

agent_type = "sink"

def setup():
    """
    Called once at startup.
    Initializes PyFiglet with a 'big' font (or override via params).
    """
    print("[Python] Setting up sink...")
    font_name = params.get("font", "big")
    state['figlet'] = Figlet(font=font_name)

def deal_with_data():
    """
    Called on every incoming packet.
    Clears the screen, prints a timestamp and each channel/value
    in large ASCII letters with two decimal places.
    """
    # extract
    t   = data.get('millis', 0)
    payload = data.get('data', {})
    readings = [
        ("I1", float(payload.get("I1", 0.0))),
        ("I2", float(payload.get("I2", 0.0))),
        ("I3", float(payload.get("I3", 0.0))),
    ]

    # clear terminal
    os.system('cls' if os.name == 'nt' else 'clear')

    # header
    print(f"Timestamp: {t} ms\n")

    # render each channel + value
    for name, val in readings:
        line = f"{name}: {val:.2f}"
        print(state['figlet'].renderText(line))