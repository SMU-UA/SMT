"""
Scenario server that serves the Modbus sniffer page and broadcasts
the current test scenario number — all from one URL.

Usage:
    "C:\\Program Files\\Typhoon HIL Control Center 2025.4\\python3_portable\\python.exe" scenario_server.py

    Then open http://localhost:8765 in Chrome/Edge.

    Run pytest SystemLevel_Scenarios.py separately to execute tests.
    The server will receive and broadcast scenario updates.
"""

import http.server
import json
import os
import threading
import time

PORT = 8765
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(SCRIPT_DIR, "Modbus_Bus_Sniffer.html")
CONSOLE_LOG = os.path.join(SCRIPT_DIR, "pytest_console.log")

current_scenario = {"scenario": 0, "label": "Ready - Run pytest to start", "running": False}
sse_clients = []
lock = threading.Lock()

console_clients = []
console_lock = threading.Lock()


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


def broadcast_console(line):
    """Broadcast a console line to all console SSE clients."""
    msg = f"data: {json.dumps({'line': line})}\n\n".encode()
    with console_lock:
        dead = []
        for client in console_clients:
            try:
                client.write(msg)
                client.flush()
            except:
                dead.append(client)
        for d in dead:
            console_clients.remove(d)


def monitor_console_log():
    """Monitor pytest_console.log and broadcast new lines."""
    file_pos = 0
    while True:
        try:
            if os.path.exists(CONSOLE_LOG):
                with open(CONSOLE_LOG, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(file_pos)
                    new_lines = f.readlines()
                    file_pos = f.tell()
                    for line in new_lines:
                        broadcast_console(line.rstrip())
        except Exception as e:
            pass
        time.sleep(0.5)


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

        elif self.path == "/console":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            with console_lock:
                console_clients.append(self.wfile)

            try:
                while True:
                    time.sleep(1)
            except:
                pass
            finally:
                with console_lock:
                    if self.wfile in console_clients:
                        console_clients.remove(self.wfile)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/scenario":
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

    # Start console log monitor
    console_thread = threading.Thread(target=monitor_console_log, daemon=True)
    console_thread.start()

    print(f"Scenario server running on http://localhost:{PORT}")
    print(f"Open http://localhost:{PORT} in Chrome/Edge.")
    print("Run 'pytest SystemLevel_Scenarios.py' to execute tests.")
    print("Console output will stream to browser if written to pytest_console.log")
    print("Press Ctrl+C to stop the server.\n")

    broadcast(0, "Ready - Run pytest to start", running=False)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
