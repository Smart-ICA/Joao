'''
This is a sink agent for Arduino data.
It displays the current values of three channels (I1, I2, I3) in 
large ASCII art format using the `pyfiglet` library.

You can install `pyfiglet` using pip:
-> pip install pyfiglet
    
To run this script, use the following command:
-> mads python -s tcp://mads-broker.local:9092 -n python_sink -m sink_Arduino

Where `python_sink` is the name of the agent (mads.ini), and `sink_Arduino` is the name of the script (.py).
'''

import json
import os
import subprocess

# Specifies that this is a sink agent
agent_type = "sink"

def setup():
    """
    Initializes state, checks availability of pyfiglet, and sets the font.
    """
    print("[Python] Setting up sink...")
    print("[Python] Parameters: " + json.dumps(params))
    print("[Python] Topic: " + topic)

    # Try importing pyfiglet
    try:
        from pyfiglet import Figlet
        state['figlet'] = Figlet(font=params.get("font", "standard"))
        state['use_pyfiglet'] = True
    except ImportError:
        state['use_pyfiglet'] = False

def render_big(text: str) -> str:
    """
    Returns the text formatted as large ASCII art, if possible.
    """
    if state.get('use_pyfiglet'):
        return state['figlet'].renderText(text)
    # Fallback to calling figlet via subprocess
    try:
        out = subprocess.check_output(['figlet', text])
        return out.decode('utf-8')
    except Exception:
        # No figlet available: return normal text
        return text

def deal_with_data():
    """
    For each packet: clears the screen and prints I1, I2, I3 in large ASCII art.
    """
    try:
        t  = data.get('millis', 0)
        d  = data.get('data', {})
        i1 = d.get('I1', 0.0)
        i2 = d.get('I2', 0.0)
        i3 = d.get('I3', 0.0)
    except Exception as e:
        print(f"[Python] Error parsing data: {e}")
        return

    # Clear terminal
    os.system('cls' if os.name == 'nt' else 'clear')

    # Simple timestamp
    print(f"Timestamp: {t} ms\n")

    # Print each channel in ASCII art
    print(render_big(f"I1 {i1:.3f}"))
    print(render_big(f"I2 {i2:.3f}"))
    print(render_big(f"I3 {i3:.3f}"))
