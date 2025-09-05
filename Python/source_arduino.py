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
import os
import errno

import serial
from serial.tools import list_ports

# Declare this as a source agent
agent_type = "source"

# Serial port object will be initialized in setup()
ser = None
_port_lock_fh = None  # file-handle do lock (fallback), mantido aberto enquanto a porta estiver em uso

def _open_serial_with_exclusive(port_path, baudrate=115200, timeout=1):
    """
    Tenta abrir a porta serial com exclusividade entre processos (quando suportado).
    - Se pyserial suportar exclusive=True, usa essa flag para impedir múltiplos acessos.
    - Caso não suporte, abre normalmente (e contamos com o file lock externo).
    """
    try:
        # PySerial >= 3.3 em POSIX: exclusive=True usa TIOCEXCL e evita múltiplos opens
        return serial.Serial(port_path, baudrate, timeout=timeout, exclusive=True)
    except TypeError:
        # Versões antigas do pyserial não suportam exclusive
        return serial.Serial(port_path, baudrate, timeout=timeout)

def _try_acquire_file_lock(port_path):
    """
    Fallback de exclusão via lockfile para coordenar processos quando exclusive=True
    não estiver disponível/suportado. Usa flock (POSIX) implicitamente.
    """
    import fcntl
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

def _release_file_lock(fh):
    if not fh:
        return
    try:
        import fcntl
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        fh.close()
    except Exception:
        pass

def _list_candidate_ports():
    """
    Lista portas seriais prováveis de Arduinos e similares.
    Combina enumeração real do sistema com alguns caminhos comuns.
    """
    detected = [p.device for p in list_ports.comports() if p.device and ("/ttyACM" in p.device or "/ttyUSB" in p.device)]
    # Ordem estável: ACMs primeiro, depois USBs, ordenados
    detected = sorted(detected, key=lambda x: ("/ttyACM" not in x, x))

    common = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]
    # Mantém a ordem dos detectados e adiciona os comuns que não estejam na lista
    for c in common:
        if c not in detected and os.path.exists(c):
            detected.append(c)
    return detected

def _probe_for_valid_json(connection, max_lines=10, settle_seconds=2.0):
    """
    Após abrir a porta, aguarda estabilização, descarta ruído e tenta ler algumas linhas.
    Retorna True se conseguir decodificar algum JSON válido, caso contrário False.
    """
    # Muitos Arduinos resetam ao abrir a porta; aguarde estabilizar
    time.sleep(settle_seconds)
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
            # ignora linhas que não parecem JSON
            continue
        try:
            json.loads(raw)
            return True
        except json.JSONDecodeError:
            # linha ainda incompleta/corrompida; continue tentando
            continue
        except Exception:
            continue
    return False

def auto_detect_port():
    """
    Tenta conectar em portas seriais de forma segura:
    - Garante exclusividade (exclusive=True quando disponível + lockfile /tmp).
    - Só aceita a porta se conseguir ler um JSON válido após abrir.
    - Se a porta estiver ocupada por outro processo, tenta a próxima.
    """
    print("[INFO] Attempting to auto-detect Arduino serial port with exclusivity...")
    global _port_lock_fh

    for port_path in _list_candidate_ports():
        lock_fh = _try_acquire_file_lock(port_path)
        if lock_fh is None:
            print(f"[INFO] Skipping {port_path}: appears to be locked by another process.")
            continue

        connection = None
        try:
            connection = _open_serial_with_exclusive(port_path, 115200, timeout=1)
        except serial.SerialException as e:
            # Dispositivos ocupados costumam dar EBUSY ou "Device or resource busy"
            msg = str(e)
            print(f"[INFO] {port_path} not available: {msg}")
            _release_file_lock(lock_fh)
            continue
        except Exception as e:
            print(f"[INFO] {port_path} open error: {e}")
            _release_file_lock(lock_fh)
            continue

        # Validar porta lendo JSON
        ok = False
        try:
            ok = _probe_for_valid_json(connection, max_lines=15, settle_seconds=2.0)
        except Exception as e:
            print(f"[INFO] {port_path} probe error: {e}")

        if ok:
            print(f"[INFO] Connected to {port_path}")
            _port_lock_fh = lock_fh  # mantém o lock enquanto o processo estiver vivo
            return connection
        else:
            print(f"[INFO] {port_path} did not yield valid JSON; releasing and trying next.")
            try:
                connection.close()
            except Exception:
                pass
            _release_file_lock(lock_fh)

    print("[ERROR] Could not find a suitable serial port with available valid JSON.")
    raise RuntimeError("No Arduino serial port found.")

def setup():
    global ser
    print("[PYTHON] Setting up source agent...")
    print("[PYTHON] Parameters: " + json.dumps(params))

    # Se usuário passar explicitamente params["serial_port"], honramos (ainda automático nos demais casos)
    port = params.get("serial_port") if isinstance(params, dict) else None
    if port:
        print(f"[INFO] Trying explicit serial port: {port}")
        # Tenta mesma lógica de lock e exclusive para a porta indicada
        lock_fh = _try_acquire_file_lock(port)
        if lock_fh is None:
            raise RuntimeError(f"Serial port {port} is locked by another process.")
        try:
            s = _open_serial_with_exclusive(port, 115200, timeout=1)
            if not _probe_for_valid_json(s, max_lines=15, settle_seconds=2.0):
                try:
                    s.close()
                except Exception:
                    pass
                _release_file_lock(lock_fh)
                raise RuntimeError(f"Could not get valid JSON from {port}.")
            global _port_lock_fh
            _port_lock_fh = lock_fh
            ser = s
        except Exception as e:
            _release_file_lock(lock_fh)
            raise
    else:
        try:
            ser = auto_detect_port()
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            raise

    try:
        ser.reset_input_buffer()
    except Exception:
        pass
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
