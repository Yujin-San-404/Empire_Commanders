import unittest

from entities.entity import Order, Team
from game import event_bus
from game.event_bus import EventBus
from systems.combat_system import AttackDenied, CombatSystem
from tests.helpers import make_unit


class CombatRules(unittest.TestCase):
    def setUp(self):
        self.combat = CombatSystem()
        # reach = 20 (range) + 10 + 10 (radii) = 40
        self.a = make_unit(1, Team.PLAYER, 0, 0)
        self.b = make_unit(2, Team.ENEMY, 30, 0)

    def test_attack_in_range_deals_damage_once(self):
        result = self.combat.try_attack(self.a, self.b)
        self.assertIsNotNone(result)
        self.assertEqual(self.b.health, 40)
        self.assertEqual(result.damage, 10)

    def test_range_boundary(self):
        self.b.x = 40.0
        self.assertEqual(self.combat.validate_attack(self.a, self.b), None)
        self.b.x = 40.01
        self.assertEqual(self.combat.validate_attack(self.a, self.b), AttackDenied.OUT_OF_RANGE)

    def test_out_of_range_does_nothing(self):
        self.b.x = 100
        self.assertIsNone(self.combat.try_attack(self.a, self.b))
        self.assertEqual(self.b.health, 50)
        self.assertEqual(self.a.cooldown_remaining, 0)

    def test_cooldown_blocks_second_attack_until_expired(self):
        self.assertIsNotNone(self.combat.try_attack(self.a, self.b))
        self.assertEqual(self.combat.validate_attack(self.a, self.b), AttackDenied.ON_COOLDOWN)
        self.assertIsNone(self.combat.try_attack(self.a, self.b))
        self.assertEqual(self.b.health, 40)
        self.combat.tick_cooldowns([self.a], 0.99)
        self.assertIsNone(self.combat.try_attack(self.a, self.b))
        self.combat.tick_cooldowns([self.a], 0.02)
        self.assertIsNotNone(self.combat.try_attack(self.a, self.b))
        self.assertEqual(self.b.health, 30)

    def test_damage_never_makes_health_negative(self):
        self.b.health = 3
        result = self.combat.try_attack(self.a, self.b)
        self.assertEqual(self.b.health, 0)
        self.assertEqual(result.damage, 3)
        self.assertTrue(result.target_defeated)

    def test_defeated_attacker_cannot_attack(self):
        self.a.take_damage(999)
        self.assertEqual(self.combat.validate_attack(self.a, self.b), AttackDenied.ATTACKER_DEFEATED)
        self.assertIsNone(self.combat.try_attack(self.a, self.b))
        self.assertEqual(self.b.health, 50)

    def test_defeated_target_cannot_be_attacked(self):
        self.b.take_damage(999)
        self.assertEqual(self.combat.validate_attack(self.a, self.b), AttackDenied.TARGET_DEFEATED)

    def test_no_friendly_fire_or_self_attack(self):
        friend = make_unit(3, Team.PLAYER, 10, 0)
        self.assertEqual(self.combat.validate_attack(self.a, friend), AttackDenied.FRIENDLY_FIRE)
        self.assertEqual(self.combat.validate_attack(self.a, self.a), AttackDenied.SELF_TARGET)

    def test_defeat_clears_order_target_and_cooldown(self):
        self.b.order = Order.ATTACK
        self.b.target_id = 1
        self.b.cooldown_remaining = 0.5
        self.b.take_damage(999)
        self.assertFalse(self.b.is_alive)
        self.assertEqual((self.b.order, self.b.target_id, self.b.cooldown_remaining), (Order.IDLE, None, 0))
        self.assertEqual(self.b.take_damage(10), 0)   # no further effect

    def test_events_published(self):
        bus = EventBus()
        seen = []
        bus.subscribe(event_bus.ATTACK, lambda r: seen.append(("attack", r.damage)))
        bus.subscribe(event_bus.UNIT_DEFEATED, lambda u: seen.append(("defeated", u.uid)))
        combat = CombatSystem(bus)
        self.b.health = 5
        combat.try_attack(self.a, self.b)
        self.assertEqual(seen, [("attack", 5), ("defeated", 2)])

    def test_attack_rate_independent_of_frame_rate(self):
        """Holding attack for 5 s lands the same number of hits at 30 or 240 steps/s."""
        def hits(steps_per_second):
            combat = CombatSystem()
            a = make_unit(1, Team.PLAYER, 0, 0, attack_cooldown=0.6)
            b = make_unit(2, Team.ENEMY, 20, 0, max_health=10_000)
            dt, n = 1 / steps_per_second, 0
            for _ in range(int(5 * steps_per_second)):
                combat.tick_cooldowns([a, b], dt)
                if combat.try_attack(a, b):
                    n += 1
            return n
        for rate in (30, 60, 240):
            self.assertIn(hits(rate), (8, 9), f"{rate} steps/s")


class TargetPriority(unittest.TestCase):
    def test_prefers_nearest(self):
        combat = CombatSystem()
        me = make_unit(1, Team.PLAYER, 0, 0)
        near, far = make_unit(2, Team.ENEMY, 50, 0), make_unit(3, Team.ENEMY, 120, 0)
        self.assertIs(combat.find_target(me, [far, near], 300), near)

    def test_prefers_wounded_when_similar_distance(self):
        combat = CombatSystem()
        me = make_unit(1, Team.PLAYER, 0, 0)
        healthy, wounded = make_unit(2, Team.ENEMY, 100, 0), make_unit(3, Team.ENEMY, 105, 0)
        wounded.health = 10
        self.assertIs(combat.find_target(me, [healthy, wounded], 300), wounded)

    def test_ignores_dead_allied_and_distant(self):
        combat = CombatSystem()
        me = make_unit(1, Team.PLAYER, 0, 0)
        dead, ally, far = make_unit(2, Team.ENEMY, 10, 0), make_unit(3, Team.PLAYER, 10, 0), make_unit(4, Team.ENEMY, 500, 0)
        dead.take_damage(999)
        self.assertIsNone(combat.find_target(me, [dead, ally, far], 300))
        self.assertIsNone(combat.find_target(me, [], 300))


if __name__ == "__main__":
    unittest.main()
