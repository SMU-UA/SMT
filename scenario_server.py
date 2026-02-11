"""
Scenario server that serves the Modbus sniffer page and broadcasts
the current test scenario number — all from one URL.

Usage:
    "C:\\Program Files\\Typhoon HIL Control Center 2025.4\\python3_portable\\python.exe" scenario_server.py

    Then open http://localhost:8765 in Chrome/Edge.
    Press "Start Test" to launch pytest and begin scenarios.
    Press "Stop Test" to terminate the test run.
"""

import http.server
import json
import os
import subprocess
import sys
import threading
import time

PORT = 8765
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(SCRIPT_DIR, "Modbus_Bus_Sniffer.html")
TEST_FILE = os.path.join(SCRIPT_DIR, "SystemLevel_Scenarios.py")

current_scenario = {"scenario": 0, "label": "Waiting for Start Test...", "running": False}
sse_clients = []
lock = threading.Lock()

# Pytest subprocess management
pytest_process = None
pytest_lock = threading.Lock()
_user_stopped = threading.Event()


def _kill_pytest():
    """Terminate the pytest subprocess if it is running."""
    global pytest_process
    with pytest_lock:
        if pytest_process is not None:
            try:
                pytest_process.terminate()
                pytest_process.wait(timeout=5)
            except Exception:
                try:
                    pytest_process.kill()
                except Exception:
                    pass
            pytest_process = None


def broadcast(scenario_num, label, running=True):
    global current_scenario
    current_scenario = {"scenario": scenario_num, "label": label, "running": running}
    msg = f"data: {json.dumps(current_scenario)}\n\n".encode()
    with lock:
        dead = []
        for client in sse_clients:
            try:
                client.write(msg)
                client.flush()
            except:
                dead.append(client)
        for d in dead:
            sse_clients.remove(d)


def monitor_pytest():
    """Wait for the pytest subprocess to exit and broadcast the result."""
    global pytest_process
    with pytest_lock:
        proc = pytest_process
    if proc is None:
        return

    # Read stdout to prevent pipe buffer deadlock
    try:
        for line in proc.stdout:
            decoded = line.decode("utf-8", errors="replace").rstrip()
            if decoded:
                print(f"  [pytest] {decoded}")
    except Exception:
        pass

    exit_code = proc.wait()

    with pytest_lock:
        if pytest_process is proc:
            pytest_process = None

    # If user already stopped, don't broadcast again
    if _user_stopped.is_set():
        return

    if exit_code == 0:
        broadcast(0, "All tests complete", running=False)
        print("  >> All tests complete")
    else:
        broadcast(0, f"Tests finished (exit code {exit_code})", running=False)
        print(f"  >> Tests finished with exit code {exit_code}")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            with open(HTML_FILE, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)

        elif self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            with lock:
                sse_clients.append(self.wfile)

            try:
                msg = f"data: {json.dumps(current_scenario)}\n\n"
                self.wfile.write(msg.encode())
                self.wfile.flush()
            except:
                return

            try:
                while True:
                    time.sleep(1)
            except:
                pass
            finally:
                with lock:
                    if self.wfile in sse_clients:
                        sse_clients.remove(self.wfile)

        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(current_scenario).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/start":
            _kill_pytest()
            _user_stopped.clear()
            broadcast(0, "Starting...", running=True)

            try:
                global pytest_process
                with pytest_lock:
                    pytest_process = subprocess.Popen(
                        [sys.executable, "-m", "pytest",
                         TEST_FILE, "-v", "--tb=short"],
                        cwd=SCRIPT_DIR,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                    )
                threading.Thread(target=monitor_pytest, daemon=True).start()
                print(f"  >> Started pytest (PID {pytest_process.pid})")
            except Exception as e:
                broadcast(0, f"Failed to start: {e}", running=False)
                print(f"  >> Failed to start pytest: {e}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        elif self.path == "/stop":
            _user_stopped.set()
            _kill_pytest()
            broadcast(0, "Stopped by user", running=False)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            print("  >> Stop received from browser")

        elif self.path == "/scenario":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                scenario_num = data.get("scenario", 0)
                label = data.get("label", "")
                broadcast(scenario_num, label, running=True)
                print(f"  >> Scenario {scenario_num}: {label}")
            except Exception as e:
                print(f"  >> Bad /scenario payload: {e}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    server = http.server.ThreadingHTTPServer(("localhost", PORT), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Scenario server running on http://localhost:{PORT}")
    print(f"Open http://localhost:{PORT} in Chrome/Edge.")
    print("Press Ctrl+C to stop the server.\n")

    broadcast(0, "Waiting for Start Test...", running=False)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        _kill_pytest()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
