# #16 Cable-detection probe

**Question:** Can power-cable insertion be detected independent of power-supply state?

**What the probe reads** (read-only, `probe.py`; tests in `test_probe.py`):
- `win_acline`: kernel32 `GetSystemPowerStatus` ACLineStatus (1=AC, 0=battery, 255=unknown)
- `psutil`: `sensors_battery().power_plugged` (True/False/None)
- `cim_battery`: `Win32_Battery.BatteryStatus` via PowerShell (2 or 6-9 = AC-ish, 1 = discharging)

Run: `python probe.py` (prints readings, `verdict`, `sources_agree` as JSON).

## Observed output, 2026-10-12 (one run, adapter plugged in, wall outlet state not independently known)
```json
{"readings": {"win_acline": 1, "psutil": true, "cim_battery": 2}, "verdict": "AC", "sources_agree": true}
```
(Printed indented by the probe; compacted here.) All three sources agreed on AC.

## Limits
- One run in one state. The battery-state and error paths are covered only by mocked unit tests, not observed on hardware.
- All three readers sit on the same Windows/ACPI layer, so their agreement is not independent evidence of the physical cable.
- HYPOTHESIS (unverified): Windows/ACPI reports AC only when the adapter actually delivers power. If true, "cable inserted into a dead outlet" would read as BATTERY, indistinguishable from "unplugged". This probe cannot tell those apart.
- Physical test for KA: plug the adapter into a dead outlet (or a switched-off socket), run `python probe.py`, and note whether the verdict is BATTERY or AC. Repeat fully unplugged and compare.
