"""
pytest configuration plugin for SMT console output streaming.

This plugin captures all pytest output (test results, errors, progress)
and writes it to pytest_console.log in real-time so the browser console
can display it via the scenario server.
"""

import os
import sys
import pytest
from _pytest.config import Config
from _pytest.terminal import TerminalReporter


CONSOLE_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pytest_console.log")


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


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: Config):
    """Restore original stdout/stderr and close log file."""
    # Restore original streams
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    # Close log file
    if hasattr(config, '_console_log_file'):
        try:
            config._console_log_file.close()
        except:
            pass
