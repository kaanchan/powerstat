"""Tests for the issue #16 cable-detection probe. OS calls are never made here."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import probe


class TestCollect(unittest.TestCase):
    def test_maps_names_to_values(self):
        out = probe.collect({"a": lambda: 1, "b": lambda: None})
        self.assertEqual(out, {"a": 1, "b": None})

    def test_failing_reader_becomes_error_string_and_does_not_raise(self):
        def boom():
            raise OSError("no api")

        out = probe.collect({"ok": lambda: 0, "bad": boom})
        self.assertEqual(out["ok"], 0)
        self.assertIsInstance(out["bad"], str)
        self.assertTrue(out["bad"].startswith("error: "))
        self.assertIn("no api", out["bad"])


class TestVerdict(unittest.TestCase):
    def test_all_agree_ac(self):
        r = {"win_acline": 1, "psutil": True, "cim_battery": 2}
        self.assertEqual(probe.verdict(r), ("AC", True))

    def test_cim_charging_codes_count_as_ac(self):
        for code in (2, 6, 7, 8, 9):
            r = {"win_acline": 1, "psutil": True, "cim_battery": code}
            self.assertEqual(probe.verdict(r), ("AC", True), code)

    def test_all_agree_battery(self):
        r = {"win_acline": 0, "psutil": False, "cim_battery": 1}
        self.assertEqual(probe.verdict(r), ("BATTERY", True))

    def test_disagreement(self):
        r = {"win_acline": 1, "psutil": False, "cim_battery": 1}
        state, agree = probe.verdict(r)
        self.assertEqual(state, "UNKNOWN")
        self.assertFalse(agree)

    def test_one_reader_errored_others_decide(self):
        r = {"win_acline": 1, "psutil": "error: boom", "cim_battery": 2}
        self.assertEqual(probe.verdict(r), ("AC", True))

    def test_all_unknown(self):
        r = {"win_acline": 255, "psutil": None, "cim_battery": None}
        self.assertEqual(probe.verdict(r), ("UNKNOWN", False))

    def test_all_errored(self):
        r = {"win_acline": "error: x", "psutil": "error: y", "cim_battery": "error: z"}
        self.assertEqual(probe.verdict(r), ("UNKNOWN", False))


if __name__ == "__main__":
    unittest.main()
