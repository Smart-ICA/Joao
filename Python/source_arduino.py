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

# Declare this as a source agent
agent_type = "source"

# Serial port object will be initialized in setup()
ser = None

def auto_detect_port():
    """
    Attempt to connect to common Arduino serial ports in sequence.
    Returns the first successful Serial connection.
    Raises a RuntimeError if none are available.
    """
    candidates = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]
    print("[INFO] Attempting to auto-detect Arduino serial port...")
    for port_path in candidates:
        try:
            connection = serial.Serial(port_path, 115200, timeout=1)
            print(f"[INFO] Connected to {port_path}")
            return connection
        except serial.SerialException:
            print(f"[INFO] {port_path} not available.")
    print("[ERROR] Could not find a suitable serial port (ACM0/1 or USB0/1).")
    raise RuntimeError("No Arduino serial port found.")

def setup():
    global ser
    print("[PYTHON] Setting up source agent...")
    print("[PYTHON] Parameters: " + json.dumps(params))

    try:
        ser = auto_detect_port()
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        # Depending on your use case, you may want to exit or retry
        raise

    ser.reset_input_buffer()
    state["n"] = 0
    print(f"[PYTHON] Successfully initialized serial connection on {ser.port}")

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
