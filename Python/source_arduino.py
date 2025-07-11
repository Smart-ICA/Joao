"""
This is a source agent that reads data from an Arduino via a serial port.
It expects the Arduino to send JSON-formatted data, which it processes and returns.
It will read data from the Arduino, parse it, and return it in the MADS Network.

Note: This code does the same as the Arduino source agent, but in Python.

To run this script, use the following command:
-> mads python -s tcp://mads-broker.local:9092 -n python_source -m source_arduino

Where python_source is the name of the agent (mads.ini), and source_arduino is the name of the script (.py).
"""

import json
import time
import random
from datetime import datetime
import serial
import serial.tools.list_ports

# Declare this as a source agent
agent_type = "source"

# Serial port object will be initialized in setup()
ser = None

def choose_port():
    """
    List available serial ports and prompt the user for a device suffix
    until a valid port is opened.
    """
    while True:
        print("[INFO] Available serial ports:")
        for port_info in serial.tools.list_ports.comports():
            print(f"  {port_info.device} – {port_info.description}")

        suffix = input(
            "[INPUT] Enter only the device suffix for Arduino serial port "
            "(e.g. ACM0 for /dev/ttyACM0, USB1 for /dev/ttyUSB1): "
        ).strip()
        port_path = f"/dev/tty{suffix}"

        try:
            connection = serial.Serial(port_path, 115200, timeout=1)
            return connection
        except serial.SerialException as e:
            print(f"\n[ERROR] Could not open {port_path}: {e}")
            print("[ERROR] Please verify the suffix and ensure the port is not in use. Retrying...\n")
            time.sleep(1)

def setup():
    global ser
    print("[PYTHON] Setting up source agent...")
    print("[PYTHON] Parameters: " + json.dumps(params))

    ser = choose_port()
    ser.reset_input_buffer()
    state["n"] = 0
    print(f"[PYTHON] Successfully connected to {ser.port}")

def get_output():
    global ser
    try:
        # Read one line of bytes from the serial port
        raw_bytes = ser.readline()
        if not raw_bytes:
            # No data received → return a safe JSON
            return json.dumps({"processed": False})

        # Decode bytes to string, ignoring invalid UTF-8 sequences
        raw = raw_bytes.decode('utf-8', errors='ignore').strip()

        # If the line doesn't start with '{', skip it
        if not raw.startswith('{'):
            return json.dumps({"processed": False})

        # Parse the JSON payload
        data = json.loads(raw)

        # Increment our counter
        state["n"] += 1

        # Mark the data as unprocessed and return it
        data["processed"] = False
        return json.dumps(data)

    except json.JSONDecodeError as e:
        # Malformed JSON → log and return safe JSON
        print(f"[ERROR] JSONDecodeError: {e}; raw was: {raw!r}")
        return json.dumps({"processed": False})

    except Exception as e:
        # Any other serial/I/O error → log and return safe JSON
        print(f"[ERROR] Serial error: {e}")
        return json.dumps({"processed": False})
