"""
Source agent that reads JSON lines from an Arduino over a serial port.

Behavior:
- Auto-detects an available serial port (/dev/ttyACMx or /dev/ttyUSBx).
- Ensures process exclusivity per port (pySerial exclusive=True when available, plus a simple /tmp file lock when supported).
- Accepts a port explicitly via params["serial_port"] if provided.
- Confirms a port only after reading a valid JSON line.
To run this script, use the following command:
-> mads python -s tcp://mads-broker.local:9092 -n python_source -m source_arduino

Where python_source is the name of the agent (mads.ini), and source_arduino is the name of the script (.py).
"""

import json
import time
import os
import serial
from serial.tools import list_ports

# Optional file-lock support (Linux/Unix)
try:
    import fcntl
    HAS_FCNTL = True
except Exception:
    HAS_FCNTL = False

agent_type = "source"  # required by MADS
ser = None
_port_lock_fh = None  # keep the lock handle open while using the port


def list_candidate_ports():
    """Return a prioritized list of likely Arduino serial ports."""
    detected = [p.device for p in list_ports.comports() if p.device and ("/ttyACM" in p.device or "/ttyUSB" in p.device)]
    detected = sorted(detected, key=lambda x: ("/ttyACM" not in x, x))  # ACM first, then USB
    common = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]
    for c in common:
        if c not in detected and os.path.exists(c):
            detected.append(c)
    return detected


def acquire_file_lock(port_path):
    """Acquire a non-blocking file lock for the port. Returns file handle or None."""
    if not HAS_FCNTL:
        return None
    lock_path = f"/tmp/serial-lock-{os.path.basename(port_path)}.lock"
    fh = open(lock_path, "w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fh.write(str(os.getpid()))
        fh.flush()
        return fh
    except BlockingIOError:
        try:
            fh.close()
        except Exception:
            pass
        return None


def release_file_lock(fh):
    if not fh or not HAS_FCNTL:
        return
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        fh.close()
    except Exception:
        pass


def open_serial(port_path, baudrate=115200, timeout=1):
    """Open the serial port with exclusivity when supported."""
    try:
        # pySerial on POSIX supports exclusive=True (TIOCEXCL) in newer versions
        return serial.Serial(port_path, baudrate, timeout=timeout, exclusive=True)
    except TypeError:
        # Older pySerial: fall back without the exclusive flag
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


def auto_detect_port():
    """
    Find the first available port that:
    - Is not locked by another process.
    - Can be opened (ideally with exclusive access).
    - Produces at least one valid JSON line.
    """
    print("[INFO] Auto-detecting serial port...")
    global _port_lock_fh

    for port in list_candidate_ports():
        # Try to lock the port to avoid multi-process conflicts
        lock_fh = acquire_file_lock(port)
        if HAS_FCNTL and lock_fh is None:
            print(f"[INFO] Skipping {port}: locked by another process.")
            continue

        conn = None
        try:
            conn = open_serial(port, 115200, timeout=1)
        except serial.SerialException as e:
            print(f"[INFO] {port} unavailable: {e}")
            release_file_lock(lock_fh)
            continue
        except Exception as e:
            print(f"[INFO] {port} open error: {e}")
            release_file_lock(lock_fh)
            continue

        ok = probe_valid_json(conn, max_lines=15, settle_seconds=2.0)
        if ok:
            print(f"[INFO] Connected to {port}")
            _port_lock_fh = lock_fh  # keep the lock while using the port
            return conn
        else:
            print(f"[INFO] {port} did not yield valid JSON. Trying next...")
            try:
                conn.close()
            except Exception:
                pass
            release_file_lock(lock_fh)

    raise RuntimeError("No suitable serial port found.")


def setup():
    """
    Called by the MADS framework to initialize the source.
    Expects a global 'params' dict and 'state' dict provided by MADS.
    """
    global ser
    print("[PYTHON] Setting up source agent...")
    print("[PYTHON] Parameters: " + json.dumps(params))

    # Optional explicit port via params
    explicit_port = params.get("serial_port") if isinstance(params, dict) else None
    if explicit_port:
        print(f"[INFO] Using explicit serial port: {explicit_port}")
        lock_fh = acquire_file_lock(explicit_port)
        if HAS_FCNTL and lock_fh is None:
            raise RuntimeError(f"Serial port {explicit_port} is locked by another process.")
        try:
            candidate = open_serial(explicit_port, 115200, timeout=1)
            if not probe_valid_json(candidate, max_lines=15, settle_seconds=2.0):
                try:
                    candidate.close()
                except Exception:
                    pass
                release_file_lock(lock_fh)
                raise RuntimeError(f"Could not read valid JSON from {explicit_port}.")
            ser = candidate
            global _port_lock_fh
            _port_lock_fh = lock_fh
        except Exception:
            release_file_lock(lock_fh)
            raise
    else:
        ser = auto_detect_port()

    try:
        ser.reset_input_buffer()
    except Exception:
        pass

    state["n"] = 0
    print(f"[PYTHON] Serial initialized on {ser.port}")


def get_output():
    """
    Called repeatedly by MADS to retrieve the next JSON message from the device.
    Returns a JSON string.
    """
    try:
        raw_bytes = ser.readline()
        if not raw_bytes:
            return json.dumps({"processed": False})

        raw = raw_bytes.decode("utf-8", errors="ignore").strip()
        if not raw.startswith("{"):
            return json.dumps({"processed": False})

        data = json.loads(raw)
        state["n"] += 1
        data["processed"] = False
        return json.dumps(data)

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSONDecodeError: {e}")
        return json.dumps({"processed": False})

    except Exception as e:
        print(f"[ERROR] Serial error: {e}")
        return json.dumps({"processed": False})
