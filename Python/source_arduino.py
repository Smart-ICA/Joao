"""
Source agent that reads JSON lines from an Arduino over a serial port.

Behavior:
- Auto-detects an available serial port (/dev/ttyACMx or /dev/ttyUSBx).
- Uses pySerial exclusive=True (when supported) to avoid multi-process conflicts.
- Accepts an explicit port via params["serial_port"], validated before use.
- Confirms a port only after reading a valid JSON line.
- Automatically retries connection if no port is available or after a disconnect.

To run this script, use the following command:
-> mads python -s tcp://mads-broker.local:9092 -n python_source -m source_arduino

Where python_source is the name of the agent (mads.ini), and source_arduino is the name of the script (.py).
"""

import json
import time
import os
import serial
from serial.tools import list_ports

agent_type = "source"

ser = None
_configured_port = None
_last_connect_attempt = 0.0
_RETRY_INTERVAL_SECONDS = 3.0


def list_candidate_ports():
    """Return a prioritized list of likely Arduino serial ports."""
    detected = [
        p.device for p in list_ports.comports()
        if p.device and ("/ttyACM" in p.device or "/ttyUSB" in p.device)
    ]
    detected = sorted(detected, key=lambda x: ("/ttyACM" not in x, x))  # ACM first, then USB

    common = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]
    for c in common:
        if c not in detected and os.path.exists(c):
            detected.append(c)
    return detected


def open_serial(port_path, baudrate=115200, timeout=1):
    """Open the serial port with exclusivity when supported by pySerial."""
    try:
        return serial.Serial(port_path, baudrate, timeout=timeout, exclusive=True)
    except TypeError:
        # Older pySerial does not support 'exclusive'
        return serial.Serial(port_path, baudrate, timeout=timeout)


def probe_valid_json(connection, max_lines=12, settle_seconds=2.0):
    """
    After opening the port, wait briefly and try to read a valid JSON line.
    Returns True if a JSON object is parsed successfully.
    """
    time.sleep(settle_seconds)  # many Arduinos reset on open
    try:
        connection.reset_input_buffer()
    except Exception:
        pass

    for _ in range(max_lines):
        raw_bytes = connection.readline()
        if not raw_bytes:
            continue
        try:
            raw = raw_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            continue
        if not raw or not raw.startswith("{"):
            continue
        try:
            json.loads(raw)
            return True
        except json.JSONDecodeError:
            continue
        except Exception:
            continue
    return False


def close_current_serial():
    """Close the current serial connection, if any."""
    global ser
    try:
        if ser:
            try:
                ser.close()
            except Exception:
                pass
    finally:
        ser = None


def ensure_serial_open(force=False):
    """
    Ensure 'ser' is open and ready. If not, try to auto-detect and open.
    Throttles connection attempts unless 'force' is True.
    """
    global ser, _last_connect_attempt

    if ser and getattr(ser, "is_open", False):
        return True

    now = time.time()
    if not force and (now - _last_connect_attempt) < _RETRY_INTERVAL_SECONDS:
        return False
    _last_connect_attempt = now

    # Build candidate list: explicit port first (if any), then detected ports
    candidates = []
    if _configured_port:
        candidates.append(_configured_port)
    for p in list_candidate_ports():
        if p not in candidates:
            candidates.append(p)

    for port in candidates:
        conn = None
        try:
            conn = open_serial(port, 115200, timeout=1)
        except serial.SerialException as e:
            print(f"[INFO] {port} unavailable: {e}")
            continue
        except Exception as e:
            print(f"[INFO] {port} open error: {e}")
            continue

        ok = probe_valid_json(conn, max_lines=15, settle_seconds=2.0)
        if ok:
            ser = conn
            try:
                ser.reset_input_buffer()
            except Exception:
                pass
            print(f"[INFO] Serial connected on {ser.port}")
            return True
        else:
            try:
                conn.close()
            except Exception:
                pass

    # No suitable port found
    close_current_serial()
    return False


def setup():
    """
    Called by the MADS framework to initialize the source.
    Expects a global 'params' dict and 'state' dict provided by MADS.
    """
    global _configured_port
    print("[PYTHON] Setting up source agent...")
    try:
        print("[PYTHON] Parameters: " + json.dumps(params))
    except Exception:
        print("[PYTHON] Parameters: {}")

    # Optional explicit port via params
    _configured_port = params.get("serial_port") if "params" in globals() and isinstance(params, dict) else None

    # Try to connect immediately; don't raise if not found (we'll retry in get_output)
    connected = ensure_serial_open(force=True)
    if not connected:
        print("[INFO] No serial port available yet; will keep retrying.")

    try:
        state["n"] = 0
    except Exception:
        pass


def get_output():
    """
    Called repeatedly by MADS to retrieve the next JSON message from the device.
    Returns a JSON string.
    """
    # Ensure we have a connection; if not, retry periodically
    if not ensure_serial_open():
        return json.dumps({"processed": False})

    try:
        raw_bytes = ser.readline()
        if not raw_bytes:
            return json.dumps({"processed": False})

        raw = raw_bytes.decode("utf-8", errors="ignore").strip()
        if not raw.startswith("{"):
            return json.dumps({"processed": False})

        data = json.loads(raw)
        try:
            state["n"] = state.get("n", 0) + 1
        except Exception:
            pass
        data["processed"] = False
        return json.dumps(data)

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSONDecodeError: {e}")
        return json.dumps({"processed": False})

    except (serial.SerialException, OSError) as e:
        print(f"[ERROR] Serial error (will reconnect): {e}")
        # Device likely disconnected; close and mark for reconnect
        close_current_serial()
        return json.dumps({"processed": False})

    except Exception as e:
        print(f"[ERROR] Serial error: {e}")
        return json.dumps({"processed": False})
