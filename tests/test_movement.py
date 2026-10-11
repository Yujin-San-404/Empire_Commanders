import math
import unittest

from entities.entity import Team
from systems.movement_system import MovementSystem
from tests.helpers import make_unit


class MoveToward(unittest.TestCase):
    def setUp(self):
        self.mv = MovementSystem(1000, 1000)

    def test_does_not_overshoot_with_huge_step(self):
        u = make_unit(1, x=100, y=100, speed=100)
        arrived = self.mv.move_toward(u, 130, 100, dt=10.0)   # could travel 1000 px
        self.assertTrue(arrived)
        self.assertAlmostEqual(u.x, 130)

    def test_stops_at_stop_distance(self):
        u = make_unit(1, x=100, y=100, speed=100)
        self.assertTrue(self.mv.move_toward(u, 300, 100, dt=10.0, stop_distance=40))
        self.assertAlmostEqual(u.x, 260)

    def test_already_within_stop_distance_does_not_move(self):
        u = make_unit(1, x=100, y=100)
        self.assertTrue(self.mv.move_toward(u, 110, 100, dt=1.0, stop_distance=20))
        self.assertEqual((u.x, u.y), (100, 100))

    def test_partial_progress_reports_not_arrived(self):
        u = make_unit(1, x=100, y=100, speed=50)
        self.assertFalse(self.mv.move_toward(u, 300, 100, dt=1.0))
        self.assertAlmostEqual(u.x, 150)

    def test_speed_multiplier(self):
        u = make_unit(1, x=0 + 100, y=100, speed=50)
        self.mv.move_toward(u, 900, 100, dt=1.0, speed_multiplier=2.0)
        self.assertAlmostEqual(u.x, 200)

    def test_defeated_unit_does_not_move(self):
        u = make_unit(1, x=100, y=100)
        u.take_damage(999)
        self.assertFalse(self.mv.move_toward(u, 500, 100, dt=1.0))
        self.mv.move_by_direction(u, 1, 0, 1.0)
        self.assertEqual((u.x, u.y), (100, 100))

    def test_clamped_to_bounds(self):
        u = make_unit(1, x=500, y=500, radius=10, speed=1000)
        self.mv.move_toward(u, 5000, 5000, dt=5.0)
        self.assertEqual((u.x, u.y), (990, 990))


class Separation(unittest.TestCase):
    def test_exactly_stacked_units_are_separated(self):
        mv = MovementSystem(1000, 1000)
        a, b = make_unit(1, x=500, y=500), make_unit(2, x=500, y=500)
        for _ in range(10):
            mv.separate([a, b])
        self.assertGreaterEqual(math.hypot(a.x - b.x, a.y - b.y), 19.0)

    def test_heavier_unit_is_pushed_less(self):
        mv = MovementSystem(1000, 1000)
        from entities.general import General
        g = General(1, Team.PLAYER, make_unit().stats, 500, 500)
        s = make_unit(2, x=510, y=500)
        mv.separate([g, s])
        self.assertLess(abs(g.x - 500), abs(s.x - 510))


if __name__ == "__main__":
    unittest.main()
