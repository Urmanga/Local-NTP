import json
import socket
import time
from datetime import datetime


def load_settings(path):
    """Load settings dictionary from a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(path, data):
    """Write settings dictionary to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def discover_server(port, timeout=2):
    """Broadcasts a discovery packet and returns server IP if found."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        s.sendto(b"CUSTONTP_DISCOVER", ("<broadcast>", port))
        data, addr = s.recvfrom(1024)
        if data == b"CUSTONTP_RESPONSE":
            return addr[0]
    return None


def get_time_from_server(ip, port):
    """Connects to server and returns (time_str, rtt_seconds)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        start = time.time()
        s.connect((ip, port))
        rtt = time.time() - start
        data = s.recv(1024)
    return data.decode("utf-8"), rtt


def current_utc_time():
    """Return current UTC time string with millisecond precision."""
    return datetime.utcnow().isoformat(sep=" ", timespec="milliseconds")
