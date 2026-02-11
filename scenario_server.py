"""
Scenario server that serves the Modbus sniffer page and broadcasts
the current test scenario number — all from one URL.

Usage:
    "C:\Program Files\Typhoon HIL Control Center 2025.4\python3_portable\python.exe" scenario_server.py

    Then open http://localhost:8765 in Chrome/Edge.
    Press "Start Log" in the browser to begin scenarios.
    Press "Stop Log" or wait for all scenarios to finish.
"""

import http.server
import json
import os
import threading
import time

PORT = 8765
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(SCRIPT_DIR, "Modbus_Bus_Sniffer.html")

current_scenario = {"scenario": 0, "label": "Waiting for Start Log...", "running": False}
sse_clients = []
lock = threading.Lock()

# Control signals
start_event = threading.Event()
stop_event = threading.Event()


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
            stop_event.clear()
            start_event.set()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            print("  >> Start received from browser")

        elif self.path == "/stop":
            stop_event.set()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            print("  >> Stop received from browser")

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


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


def sleep_or_stop(duration):
    """Sleep for duration seconds, but return True immediately if stop is requested."""
    end = time.time() + duration
    while time.time() < end:
        if stop_event.is_set():
            return True
        time.sleep(0.2)
    return False


def run_scenarios():
    """Runs through the test sequence from SystemLevel_Scenarios.py."""
    scenarios = []
    n = 1

    for sn, r in [(1,10),(2,8),(3,6),(4,5),(5,4),(6,3),(7,2),(8,1),(9,0.5),(10,0.2)]:
        scenarios.append((n, f"SA_CurrentLimit_Line_R_{sn}", 25))
        n += 1

    for sn, r in [(1,10),(2,8),(3,6),(4,5),(5,4),(6,3),(7,2),(8,1),(9,0.5),(10,0.2)]:
        scenarios.append((n, f"SA_CurrentLimit_Phase_R_{sn}", 27))
        n += 1

    for sn in range(1, 17):
        scenarios.append((n, f"GridConnection_LineLoad_{sn}", 107))
        n += 1

    for sn in range(1, 17):
        scenarios.append((n, f"GridConnection_PhaseLoad_{sn}", 107))
        n += 1

    for sn in range(1, 5):
        scenarios.append((n, f"GC_currentlimit_{sn}", 100))
        n += 1

    for sn in range(1, 11):
        scenarios.append((n, f"Startup_GC_Bat_first_{sn}", 30))
        n += 1

    print(f"\nTotal scenarios: {len(scenarios)}")
    print(f"Open http://localhost:{PORT} in Chrome/Edge")

    while True:
        # Wait for start signal from browser
        broadcast(0, "Waiting for Start Log...", running=False)
        print("\nWaiting for Start Log button...\n")
        start_event.wait()
        start_event.clear()
        stop_event.clear()

        print("Starting scenario sequence!\n")
        broadcast(0, "Starting...", running=True)
        time.sleep(1)

        stopped = False
        for num, label, duration in scenarios:
            if stop_event.is_set():
                stopped = True
                break
            print(f"  [{num:2d}/{len(scenarios)}] {label}  ({duration}s)")
            broadcast(num, label, running=True)
            if sleep_or_stop(duration):
                stopped = True
                break

        if stopped:
            broadcast(0, "Stopped by user", running=False)
            print("\n  Stopped by user.")
        else:
            broadcast(0, "All tests complete", running=False)
            print("\n  All scenarios complete!")

        stop_event.clear()


def main():
    server = http.server.ThreadingHTTPServer(("localhost", PORT), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Scenario server running on http://localhost:{PORT}")

    try:
        run_scenarios()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
