"""Issue #16 probe: read three independent power-source indicators (read-only)."""
import ctypes
import json
import subprocess
from ctypes import wintypes


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", wintypes.BYTE),
        ("BatteryFlag", wintypes.BYTE),
        ("BatteryLifePercent", wintypes.BYTE),
        ("SystemStatusFlag", wintypes.BYTE),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


def read_win_acline():
    """ACLineStatus: 1=AC, 0=battery, 255=unknown."""
    status = SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        raise OSError("GetSystemPowerStatus failed")
    return int(status.ACLineStatus)


def read_psutil():
    """sensors_battery().power_plugged: True/False/None (None = unknown or no battery)."""
    import psutil
    battery = psutil.sensors_battery()
    return None if battery is None else battery.power_plugged


def read_cim_battery():
    """Win32_Battery.BatteryStatus (first battery), or None if no battery reported."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Battery).BatteryStatus"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"powershell exit {result.returncode}")
    lines = result.stdout.split()
    return int(lines[0]) if lines else None


READERS = {
    "win_acline": read_win_acline,
    "psutil": read_psutil,
    "cim_battery": read_cim_battery,
}


def collect(readers):
    """Run each reader; a failing reader yields 'error: <msg>' instead of raising."""
    out = {}
    for name, fn in readers.items():
        try:
            out[name] = fn()
        except Exception as exc:  # probe must never die on one bad source
            out[name] = f"error: {exc}"
    return out


def _vote(name, value):
    """Return 'AC', 'BATTERY', or None (unknown/errored/no data)."""
    if isinstance(value, str) or value is None:
        return None
    if name == "win_acline":
        return {1: "AC", 0: "BATTERY"}.get(value)
    if name == "psutil":
        return {True: "AC", False: "BATTERY"}.get(value)
    if name == "cim_battery":
        if value == 1:
            return "BATTERY"
        if value == 2 or 6 <= value <= 9:
            return "AC"
    return None


def verdict(readings):
    """Return (state, sources_agree). Disagreeing or no usable sources -> UNKNOWN."""
    votes = {v for v in (_vote(n, x) for n, x in readings.items()) if v}
    if len(votes) == 1:
        return votes.pop(), True
    return "UNKNOWN", False


def main():
    readings = collect(READERS)
    state, agree = verdict(readings)
    print(json.dumps({"readings": readings, "verdict": state, "sources_agree": agree}, indent=2))


if __name__ == "__main__":
    main()
