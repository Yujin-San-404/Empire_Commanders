import json
import tempfile
import unittest
from pathlib import Path

from entities.entity import UnitStats
from game.camera import Viewport
from game.config import DataError, Settings, load_battle_data, load_settings
from game.game_loop import FixedTimestep
from systems.ai_system import AIConfig


class TimestepTests(unittest.TestCase):
    def test_steps_match_elapsed_time(self):
        ts = FixedTimestep(step=0.1)
        total = sum(ts.advance(0.05) for _ in range(20))   # 1.0 s total
        self.assertEqual(total, 10)

    def test_large_frame_spike_is_clamped(self):
        ts = FixedTimestep(step=1 / 60, max_frame_time=0.25, max_steps=5)
        self.assertLessEqual(ts.advance(30.0), 5)
        self.assertEqual(ts.advance(0.0), 0)      # surplus was discarded, no backlog

    def test_negative_dt_ignored(self):
        self.assertEqual(FixedTimestep().advance(-1.0), 0)

    def test_invalid_args(self):
        with self.assertRaises(ValueError):
            FixedTimestep(step=0)


class ViewportTests(unittest.TestCase):
    def test_identity_at_native_size(self):
        v = Viewport()
        v.update(1280, 720)
        self.assertEqual(v.to_logical(640, 360), (640, 360))

    def test_letterboxing_and_mouse_mapping(self):
        v = Viewport()
        v.update(1920, 1200)            # 16:10 window: scale 1.5, bars top/bottom
        self.assertAlmostEqual(v.scale, 1.5)
        self.assertEqual(v.offset_x, 0)
        self.assertEqual(v.offset_y, 60)
        self.assertEqual(v.to_logical(0, 60), (0, 0))
        self.assertEqual(v.to_logical(1920, 1140), (1280, 720))
        self.assertFalse(v.contains_window_point(10, 10))

    def test_tiny_window_does_not_crash(self):
        v = Viewport()
        v.update(0, 0)
        self.assertGreater(v.scale, 0)


class ConfigTests(unittest.TestCase):
    def test_shipped_data_loads(self):
        d = load_battle_data()
        self.assertIn("skirmish", d.scenarios)
        self.assertIn("bolo_fighter", d.troop_stats)

    def test_settings_fallback_for_missing_and_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_settings(Path(tmp) / "nope.json"), Settings())
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json")
            self.assertEqual(load_settings(bad), Settings())
            weird = Path(tmp) / "weird.json"
            weird.write_text(json.dumps({"window_width": "wide"}))
            self.assertEqual(load_settings(weird), Settings())

    def test_settings_valid_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.json"
            p.write_text(json.dumps({"window_width": 1600, "window_height": 900}))
            self.assertEqual(load_settings(p).window_width, 1600)

    def test_unit_stats_validation(self):
        good = dict(max_health=10, damage=1, attack_range=5, attack_cooldown=1, speed=50)
        self.assertEqual(UnitStats.from_dict("x", good).max_health, 10)
        with self.assertRaises(ValueError):
            UnitStats.from_dict("x", {k: v for k, v in good.items() if k != "speed"})
        with self.assertRaises(ValueError):
            UnitStats.from_dict("x", dict(good, attack_cooldown=0))
        with self.assertRaises(ValueError):
            UnitStats.from_dict("x", dict(good, damage="lots"))

    def test_ai_config_validation(self):
        with self.assertRaises(ValueError):
            AIConfig.from_dict({"bogus": 1})
        with self.assertRaises(ValueError):
            AIConfig.from_dict({"chase_stop_fraction": 1.5})

    def test_missing_data_file_gives_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DataError):
                load_battle_data(Path(tmp))


if __name__ == "__main__":
    unittest.main()
