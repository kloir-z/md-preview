"""
md_open.pyw - Markdown file opener
Opens a .md file in the browser via md_server.
Starts the server automatically if not running.
Uses only stdlib socket check (no subprocess, no PowerShell).
"""
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DEFAULT_PORT as PORT

SERVER_SCRIPT = str(Path(__file__).parent / "md_server.py")


def server_running():
    try:
        s = socket.create_connection(("127.0.0.1", PORT), timeout=0.2)
        s.close()
        return True
    except OSError:
        return False


def main():
    if len(sys.argv) < 2:
        return

    filepath = str(Path(sys.argv[1]).resolve())

    if not server_running():
        subprocess.Popen(
            [sys.executable, SERVER_SCRIPT, "--port", str(PORT)],
            creationflags=0x00000008,  # DETACHED_PROCESS
        )
        # Wait for server to start
        import time
        for _ in range(20):
            if server_running():
                break
            time.sleep(0.1)

    webbrowser.open(f"http://localhost:{PORT}/view?path={filepath}")


if __name__ == "__main__":
    main()
