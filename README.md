# PowerStatus App

> **Start here:** run `python power_status.py` (see Usage below); open work is tracked at <https://github.com/kaanchan/powerstat/issues>.

A Python application for Windows that announces power state changes (battery/AC) via voice and console notifications.

## Features
- Detects power state changes using `psutil`
- Announces changes using `pyttsx3` (speech)
- Console notifications

## Status (2026-10-12)
- Shipped: system tray (`system_tray.py`, #9), toast notifications (`notifications.py`), Windows service scaffolding (`service.py`, #10/#13)
- Open: professional packaging and installer (#11, under the service epic #7)

## Requirements
- Python 3.8+
- psutil
- pyttsx3

## Usage

### Activating Virtual Environment
**PowerShell:**
```
.venv\Scripts\activate; python power_status.py
```

**Bash/Git Bash:**
```
source .venv/Scripts/activate && python power_status.py
```

### Running the Application
Run `python power_status.py` to start monitoring power state changes.

### Installation
1. Activate the virtual environment (see above)
2. Install dependencies: `pip install -r requirements.txt`
