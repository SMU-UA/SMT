# SMU Modbus Bus Sniffer + Scenario Test Runner

A browser-based Modbus RTU bus sniffer with integrated test scenario sequencing for SMU (Smart Management Unit) system-level testing.

## Overview

This tool sniffs Modbus RTU traffic on the serial bus between three slaves (S1_INV, S2_CH, S3_HMI) and synchronizes data logging with a predefined sequence of 66 test scenarios. All HMI status register values are logged alongside the active scenario number, producing a timestamped CSV for post-test analysis.

## Quick Start

1. Double-click **`START_SMU_Sniffer.bat`**
2. Browser opens automatically at `http://localhost:8765`
3. Click **Connect Serial** and select the Modbus RTU COM port
4. Go to the **Data Log** tab
5. Click **Start Test** to begin scenario sequencing and data recording
6. CSV is saved automatically when all scenarios complete or when you press **Stop Test**

## Requirements

- **Typhoon HIL Control Center** (any version) - provides the bundled Python runtime
- **Chrome or Edge** browser - required for Web Serial API support

No other software or Python packages need to be installed.

## Files

| File | Description |
|------|-------------|
| `START_SMU_Sniffer.bat` | One-click launcher - finds Typhoon Python, starts server, opens browser |
| `scenario_server.py` | Python HTTP server - serves the HTML page, broadcasts scenario numbers via SSE |
| `Modbus_Bus_Sniffer.html` | Browser UI - Modbus sniffer, live register display, data logging |
| `SystemLevel_Scenarios.py` | Original Typhoon HIL test definitions (reference only, not executed) |
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
- Auto-saves CSV on test completion or manual stop
- CSV filename includes date/time: `HMI_DataLog_2026-02-10_22-15-30.csv`

### Scenario Sequencer
- 66 test scenarios across 6 test groups:
  - SA_CurrentLimit_Line (10 scenarios, 25s each)
  - SA_CurrentLimit_Phase (10 scenarios, 27s each)
  - GridConnection_LineLoad (16 scenarios, 107s each)
  - GridConnection_PhaseLoad (16 scenarios, 107s each)
  - GC_currentlimit (4 scenarios, 100s each)
  - Startup_GC_Bat_first (10 scenarios, 30s each)
- Browser controls start/stop - Python waits for the Start Test button
- Live scenario indicator bar shows current scenario number and name

## Architecture

```
Browser (Chrome/Edge)          Python Server (localhost:8765)
+-----------------------+      +-------------------------+
| Modbus Sniffer (HTML) |      | scenario_server.py      |
|                       |      |                         |
| Web Serial API -----> |      |  GET /        -> HTML   |
|   (COM port sniff)    |      |  GET /events  -> SSE    |
|                       | SSE  |  POST /start  -> begin  |
| EventSource <---------|------|  POST /stop   -> halt   |
|                       |      |                         |
| Start Test  --------->|------|  Scenario sequencer     |
| Stop Test   --------->|------|  (timed steps)          |
+-----------------------+      +-------------------------+
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
