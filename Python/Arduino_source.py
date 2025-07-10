import json
import time
import random
from datetime import datetime
import serial

# Specify that this is a source agent
agent_type = "source"

# We'll open the serial port once in setup()
ser = None

def setup():
    global ser
    print("[Python] Setting up source...")
    print("[Python] Parameters: " + json.dumps(params))
    # Open the serial port and clear any pending input
    ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
    ser.reset_input_buffer()
    state["n"] = 0

def get_output():
    global ser
    try:
        # Read one line (bytes) from the serial port
        raw_bytes = ser.readline()
        if not raw_bytes:
            # Nothing arrived → return a valid JSON string
            return json.dumps({"processed": False})

        # Decode to str, ignoring any invalid UTF-8 byte sequences
        raw = raw_bytes.decode('utf-8', errors='ignore').strip()

        # Skip any lines that don't look like JSON : Arduino running before py_source generates a first bad Json
        if not raw.startswith('{'):
            return json.dumps({"processed": False})

        # Parse the JSON payload
        data = json.loads(raw)
        
        # Update our counter
        state["n"] += 1
        
        # Mark it as unprocessed and return
        data["processed"] = False
        return json.dumps(data)

    except json.JSONDecodeError as e:
        # Malformed JSON → log and return a safe JSON string
        print(f"[Python] JSONDecodeError: {e}; raw was: {raw!r}")
        return json.dumps({"processed": False})

    except Exception as e:
        # Any other serial/I/O error → log and return a safe JSON string
        print(f"[Python] Serial error: {e}")
        return json.dumps({"processed": False})
