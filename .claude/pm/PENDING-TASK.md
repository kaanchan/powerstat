# Pending task — swarm 20260907T064155-powerstat

- Issue: https://github.com/kaanchan/powerstat/issues/6 (Optimize startup: start monitoring before voice engine initialization)
- Branch: swarm/20260907-6 (to be created)
- Plan: move `initialize_voice_engine()` off the blocking `PowerMonitor.initialize()` path
  into a daemon thread; `self.voice_ready` flips true when the engine finishes; the
  startup voice announcement fires from the background thread once ready instead of
  synchronously. Monitoring loop and status display start immediately either way.
- Test-first: `tests/test_power_monitor.py` (new) — characterizes that `initialize()`
  returns before a slow voice-engine init completes, and that `voice_ready` flips
  asynchronously. Run with: `.venv/Scripts/python.exe -m pytest tests/ -v`
- Resume: if interrupted, check `git log -1` on `swarm/20260907-6` — if the test file
  exists but power_status.py is unchanged, tests should currently FAIL (red) — implement
  the fix next. If both exist and tests pass, just commit + update PROGRESS.jsonl.
