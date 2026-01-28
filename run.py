"""
PyInstaller entry-point for OpenChatDB.

Finds a free port, launches uvicorn on 127.0.0.1, and opens the default
browser once the server is ready.
"""

import socket
import threading
import time
import webbrowser
import urllib.request

import uvicorn
from app import asgi_app


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _open_when_ready(url: str, timeout: float = 30.0):
    """Poll the server and open the browser as soon as it responds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.3)


def main():
    port = _find_free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"Starting OpenChatDB on {url}")

    threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()

    uvicorn.run(asgi_app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
