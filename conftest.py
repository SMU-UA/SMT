"""
pytest configuration plugin for SMT console output streaming.

This plugin captures all pytest output (test results, errors, progress)
and writes it to pytest_console.log in real-time so the browser console
can display it via the scenario server.
"""

import os
import sys
import signal
import threading
import time
import pytest
from _pytest.config import Config
from _pytest.terminal import TerminalReporter


CONSOLE_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pytest_console.log")
HEARTBEAT_INTERVAL = 2  # Send heartbeat every 2 seconds


def send_test_stopped():
    """Send notification to SMT server that tests have stopped."""
    import json
    import urllib.request
    try:
        payload = json.dumps({"scenario": 0, "label": "Tests stopped", "running": False}).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8765/scenario",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass  # Server not running - ignore


def send_heartbeat():
    """Send heartbeat to SMT server to indicate tests are still running."""
    import json
    import urllib.request
    try:
        req = urllib.request.Request(
            "http://localhost:8765/heartbeat",
            data=b'{}',
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass  # Server not running - ignore


def heartbeat_worker(stop_event):
    """Background thread that sends periodic heartbeats while tests run."""
    while not stop_event.is_set():
        send_heartbeat()
        # Use wait() instead of sleep() so we can stop quickly
        stop_event.wait(HEARTBEAT_INTERVAL)


class ConsoleLogger:
    """Captures stdout/stderr and writes to console log file."""

    def __init__(self, original_stream, log_file):
        self.original_stream = original_stream
        self.log_file = log_file

    def write(self, text):
        # Write to original stream (Typhoon IDE console)
        self.original_stream.write(text)
        # Also write to log file for browser console
        try:
            self.log_file.write(text)
            self.log_file.flush()
        except:
            pass

    def flush(self):
        self.original_stream.flush()
        try:
            self.log_file.flush()
        except:
            pass

    def isatty(self):
        return self.original_stream.isatty()


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: Config):
    """Clear the console log file and set up output capture at test session start."""
    # Set up signal handler for Ctrl+C
    original_sigint = signal.getsignal(signal.SIGINT)

    def sigint_handler(sig, frame):
        send_test_stopped()
        # Call original handler
        if callable(original_sigint):
            original_sigint(sig, frame)
        else:
            sys.exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    # Clear/create the log file
    with open(CONSOLE_LOG, 'w', encoding='utf-8') as f:
        f.write(f"=== SMT Test Console Output ===\n")
        f.write(f"Started: {config.args}\n\n")

    # Open log file for appending
    log_file = open(CONSOLE_LOG, 'a', encoding='utf-8', buffering=1)  # Line buffered

    # Wrap stdout and stderr
    sys.stdout = ConsoleLogger(sys.__stdout__, log_file)
    sys.stderr = ConsoleLogger(sys.__stderr__, log_file)

    # Store log file handle for cleanup
    config._console_log_file = log_file

    # Start heartbeat thread
    stop_event = threading.Event()
    heartbeat_thread = threading.Thread(target=heartbeat_worker, args=(stop_event,), daemon=True)
    heartbeat_thread.start()

    # Store for cleanup
    config._heartbeat_stop_event = stop_event
    config._heartbeat_thread = heartbeat_thread


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: Config):
    """Restore original stdout/stderr and close log file."""
    # Stop heartbeat thread
    if hasattr(config, '_heartbeat_stop_event'):
        config._heartbeat_stop_event.set()
        if hasattr(config, '_heartbeat_thread'):
            config._heartbeat_thread.join(timeout=1)

    # Restore original streams
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    # Close log file
    if hasattr(config, '_console_log_file'):
        try:
            config._console_log_file.close()
        except:
            pass

    # Notify SMT server that all tests are complete
    import json
    import urllib.request
    payload = json.dumps({"scenario": 0, "label": "All tests complete", "running": False}).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8765/scenario",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # Server not running - tests still work standalone
