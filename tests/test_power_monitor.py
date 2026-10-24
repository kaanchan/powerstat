"""Regression tests for issue #6: voice engine init must not block startup."""
import time
import threading
import unittest
from unittest.mock import patch

import power_status as ps


class TestPowerMonitorAsyncVoiceInit(unittest.TestCase):
    def test_initialize_does_not_block_on_voice_engine(self):
        voice_engine_started = threading.Event()
        release_voice_engine = threading.Event()

        def slow_voice_init():
            voice_engine_started.set()
            release_voice_engine.wait(timeout=2)
            return True

        with patch.object(ps, 'get_power_status', return_value='AC Power'), \
             patch.object(ps, 'initialize_voice_engine', side_effect=slow_voice_init), \
             patch.object(ps, 'announce') as mock_announce:
            monitor = ps.PowerMonitor(console_output=False)
            start = time.time()
            result = monitor.initialize()
            elapsed = time.time() - start

            self.assertTrue(result)
            self.assertLess(elapsed, 1.0, "initialize() should return before voice engine finishes")
            self.assertFalse(monitor.voice_ready, "voice_ready should still be False right after initialize()")

            self.assertTrue(voice_engine_started.wait(timeout=1), "voice engine init should have started in background")
            release_voice_engine.set()

            for _ in range(40):
                if monitor.voice_ready:
                    break
                time.sleep(0.05)

            self.assertTrue(monitor.voice_ready, "voice_ready should flip true once background init completes")
            mock_announce.assert_called_once()

    def test_initialize_returns_false_without_battery_info(self):
        with patch.object(ps, 'get_power_status', return_value=None):
            monitor = ps.PowerMonitor(console_output=False, voice_enabled=False)
            self.assertFalse(monitor.initialize())


if __name__ == '__main__':
    unittest.main()
