"""
Source agent that reads JSON lines from an Arduino-like MCU over serial.

Features:
- Minimal logging with colors
- Fail-fast: exits immediately if no port is available or if the port disconnects
- Prefers /dev/serial/by-id; attempts exclusive open when available
- Prints the real device path (e.g., /dev/ttyACM0)

To run this script in MADS:
    mads python -s tcp://mads-broker.local:9092 -n python_source -m source_arduino
"""

import json
import os
import errno
import time

import serial
from serial.tools import list_ports

# ---- MADS declaration ----
agent_type = "source"

# ---- Globals ----
ser = None
_exited_once = False

# ---- Colors ----
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"


# ===================== Lockfile (fallback) =====================

def _lockfile_path_for(port_path: str) -> str:
    return f"/tmp/mads-serial-lock-{port_path.replace('/', '_')}"


def _try_acquire_lockfile(lockpath: str) -> bool:
    """Simple lock using O_CREAT|O_EXCL. True = acquired; False = already locked."""
    try:
        fd = os.open(lockpath, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.write(fd, b"mads-serial-lock")
        os.close(fd)
        return True
    except OSError as e:
        if e.errno in (errno.EEXIST, errno.EACCES):
            return False
        raise


def _safe_close_serial():
    """Close and cleanup lockfile, if any."""
    global ser
    if ser is None:
        return
    try:
        if getattr(ser, "is_open", False):
            ser.close()
    except Exception:
        pass
    finally:
        lockfile = getattr(ser, "_mads_lockfile", None)
        if lockfile:
            try:
                os.unlink(lockfile)
            except FileNotFoundError:
                pass
        ser = None


# ===================== Port discovery & opening =====================

def list_candidate_ports() -> list[str]:
    """Return candidate device paths, preferring /dev/serial/by-id, then ttyACM/ttyUSB, then fallbacks."""
    candidates: list[str] = []

    # 1) /dev/serial/by-id/*
    by_id_dir = "/dev/serial/by-id"
    if os.path.isdir(by_id_dir):
        try:
            for e in sorted(os.listdir(by_id_dir)):
                candidates.append(os.path.join(by_id_dir, e))
        except Exception:
            pass

    # 2) ttyACM/ttyUSB detected by pyserial
    seen = set(candidates)
    for p in list_ports.comports():
        dev = p.device or ""
        if ("/ttyACM" in dev or "/ttyUSB" in dev) and dev not in seen:
            candidates.append(dev)
            seen.add(dev)

    # 3) hardcoded fallback
    for h in ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]:
        if h not in seen and os.path.exists(h):
            candidates.append(h)
            seen.add(h)

    return candidates


def open_serial_exclusive(port_path: str, baud: int = 115200, timeout: float = 1.0) -> serial.Serial:
    """
    Try to open the port with exclusive access (Linux + pyserial>=3.5).
    If not supported, use a userland lockfile.
    """
    try:
        return serial.Serial(port_path, baudrate=baud, timeout=timeout, exclusive=True)
    except TypeError:
        # Older pyserial: use lockfile
        lockpath = _lockfile_path_for(port_path)
        if not _try_acquire_lockfile(lockpath):
            raise serial.SerialException("busy")
        try:
            s = serial.Serial(port_path, baudrate=baud, timeout=timeout)
            s._mads_lockfile = lockpath  # type: ignore[attr-defined]
            return s
        except Exception:
            try:
                os.unlink(lockpath)
            except FileNotFoundError:
                pass
            raise


def auto_detect_port() -> serial.Serial | None:
    """Try to open the first available port. Returns None if none can be opened."""
    candidates = list_candidate_ports()
    if not candidates:
        return None

    for port_path in candidates:
        try:
            s = open_serial_exclusive(port_path, baud=115200, timeout=1.0)
            time.sleep(1.2)  # many MCUs reset on open
            return s
        except Exception:
            continue

    return None


# ===================== MADS lifecycle =====================

def setup():
    """Fail fast: if no port is available, exit immediately."""
    global ser
    ser = auto_detect_port()
    if ser is None:
        print(f"\n{RED}[ERROR]{RESET} No serial ports found.")
        os._exit(1)

    try:
        ser.reset_input_buffer()
    except Exception:
        pass

    state["n"] = 0
    # Print the real device (e.g., /dev/ttyACM0), not the by-id symlink.
    print(f"\n{GREEN}[OK]{RESET} Serial: {os.path.realpath(ser.port)}")


def get_output():
    """Read one JSON line from the serial port. If the port disappears, print once and exit."""
    global ser, _exited_once

    if ser is None or not getattr(ser, "is_open", False):
        if not _exited_once:
            _exited_once = True
            print(f"\n{RED}[ERROR]{RESET} Serial disconnected.")
            _safe_close_serial()
            os._exit(1)
        return json.dumps({"processed": False})

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

    except json.JSONDecodeError:
        return json.dumps({"processed": False})

    except serial.SerialException:
        if not _exited_once:
            _exited_once = True
            print(f"\n{RED}[ERROR]{RESET} Serial error.")
            _safe_close_serial()
            os._exit(1)
        return json.dumps({"processed": False})

    except Exception:
        if not _exited_once:
            _exited_once = True
            print(f"\n{RED}[ERROR]{RESET} Unexpected error.")
            _safe_close_serial()
            os._exit(1)
        return json.dumps({"processed": False})
