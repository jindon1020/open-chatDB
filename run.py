"""
PyInstaller entry-point for OpenChatDB.

Finds a free port, launches uvicorn in a background thread,
and opens a native macOS / Windows window via pywebview.
"""

import socket
import sys
import threading
import time
import urllib.request

import uvicorn
from app import asgi_app


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 30.0):
    """Block until the server responds or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def _start_server(port: int):
    uvicorn.run(asgi_app, host="127.0.0.1", port=port, log_level="warning")


def main():
    port = _find_free_port()
    url = f"http://127.0.0.1:{port}"

    # Start uvicorn in a daemon thread
    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to be ready
    _wait_for_server(url)

    # Open native window
    import webview
    window = webview.create_window(
        "OpenChatDB",
        url,
        width=1280,
        height=800,
        min_size=(900, 600),
    )
    webview.start()

    # When the window closes, exit the process
    sys.exit(0)


if __name__ == "__main__":
    main()
