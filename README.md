# SMT - System Monitoring Tool

A browser-based Modbus RTU bus sniffer with integrated test scenario sequencing for SMU (System Master Unit) system-level testing.

## Overview

This tool sniffs Modbus RTU traffic on the serial bus between three slaves (S1_INV, S2_CH, S3_HMI) and synchronizes data logging with a predefined sequence of 66 test scenarios. All HMI status register values are logged alongside the active scenario number, producing a timestamped CSV for post-test analysis.

## Quick Start

1. Double-click **`START_SMU_Sniffer.bat`**
2. Browser opens automatically at `http://localhost:8765`
3. Click **Connect Serial** and select the Modbus RTU COM port
4. Run `pytest SystemLevel_Scenarios.py` from Typhoon HIL IDE console
5. Data logging starts automatically when first scenario arrives
6. CSV is saved automatically when all scenarios complete (use **Download CSV** for manual saves)

## Requirements

- **Typhoon HIL Control Center** (any version) - provides the bundled Python runtime
- **Chrome or Edge** browser - required for Web Serial API support

No other software or Python packages need to be installed.

## Files

| File | Description |
|------|-------------|
| `START_SMU_Sniffer.bat` | One-click launcher - finds Typhoon Python, starts server, opens browser |
| `scenario_server.py` | Python HTTP server - serves HTML, relays scenario updates and console output via SSE |
| `Modbus_Bus_Sniffer.html` | Browser UI - Modbus sniffer, live register display, data logging, console output |
| `SystemLevel_Scenarios.py` | Typhoon HIL pytest test suite - reports scenarios to server via HTTP POST |
| `conftest.py` | pytest plugin - captures console output to `pytest_console.log` for browser streaming |
| `run_server.ps1` | PowerShell helper to run the server manually |

## Features

### Modbus Sniffer
- Real-time decoding of Modbus RTU frames (Function Code 0x10 - Write Multiple Registers)
- Three slave tabs: **S1_INV** (Inverter), **S2_CH** (Charger), **S3_HMI** (HMI Status)
- Live register values with labels and scaling
- Raw frame log with slave-based filtering

### Data Logging
- Logs all S3_HMI Status registers (29 parameters) every second
- Analog values (VDC, IINV1, IINV2, VO1, VO2, VG1, VG2, FRQI, FRQG, etc.) are scaled by /10
- Status registers (SSRS, FCODE, STATE, INVCOMMAND, etc.) logged as raw integers
- Relative time in seconds from test start
- Auto-starts when first scenario arrives (manual **Start Log**/**Stop Log** buttons also available)
- Auto-saves CSV when all scenarios complete naturally
- Manual download available via **Download CSV** button
- CSV filename includes date/time: `HMI_DataLog_2026-02-10_22-15-30.csv`

### Scenario Sequencer
- 66 test scenarios across 6 test groups:
  - SA_CurrentLimit_Line (10 scenarios)
  - SA_CurrentLimit_Phase (10 scenarios)
  - GridConnection_LineLoad (16 scenarios)
  - GridConnection_PhaseLoad (16 scenarios)
  - GC_currentlimit (4 scenarios)
  - Startup_GC_Bat_first (10 scenarios)
- Run `pytest SystemLevel_Scenarios.py` from Typhoon HIL IDE console
- Each test function reports its scenario to the server via HTTP POST
- Live scenario indicator bar shows current scenario number and name
- Tests also work standalone without the server (scenario reporting will silently fail)

### Console Output
- Real-time display of pytest console output in the browser
- Shows test progress, errors, and all pytest output
- Automatically captured via `conftest.py` plugin
- Output appears in both Typhoon IDE console and browser Console tab

## Architecture

```
Browser (Chrome/Edge)          Python Server (localhost:8765)        Typhoon HIL IDE
+-----------------------+      +-------------------------+      +-------------------------+
| Modbus Sniffer (HTML) |      | scenario_server.py      |      | pytest console          |
|                       |      |                         |      |                         |
| Web Serial API -----> |      |  GET /         -> HTML  |      | > pytest SystemLevel... |
|   (COM port sniff)    |      |  GET /events   -> SSE   |      |                         |
|                       | SSE  |  GET /console  -> SSE   |      | SystemLevel_Scenarios   |
| Scenario SSE <--------|------|  POST /scenario <- recv |<-----| + conftest.py           |
| Console SSE  <--------|------|                         |      |   report_scenario()     |
|                       |      |  monitor_console_log()  |      |   write console log     |
| Start/Stop Log        |      |    (file watcher)       |<-----| pytest_console.log      |
| (local only)          |      +-------------------------+      +-------------------------+
+-----------------------+                                                   |
                                                                           v
                                                              Typhoon HIL Hardware
```

## Modbus Slave Addresses

| Slave | ID | Register Start | Description |
|-------|----|---------------|-------------|
| S1_INV | 0x11 | 20100 | Inverter data |
| S2_CH | 0x21 | 20100 | Charger data |
| S3_HMI | 0x02 | 200 (write) | HMI status registers |

## Logged Parameters

**Scaled /10:** VDC, IINV1, IINV2, VO1, VO2, VG1, VG2, FRQI, FRQG, TEMP, VDCC, VBC, IBC, IBRI1C, IBRI2C, POWER1, BVTOTAL, BCTOTAL

**Raw integers:** SSRS, FCODE, FTRIG, FFLAG, GENS, STATE, FCC, FFC, INVCOMMAND, CHCOMMAND, HRELAY
