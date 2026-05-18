# PowerStatus App

A Python application for Windows that announces power state changes (battery/AC) via voice and console notifications.

## Features
- Detects power state changes using `psutil`
- Announces changes using `pyttsx3` (speech)
- Console notifications

## Future Plans
- System tray integration
- Windows service support
- GUI notifications

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
