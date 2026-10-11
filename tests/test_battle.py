import math
import unittest

from entities.entity import Order, Team
from game import event_bus
from game.event_bus import EventBus
from systems.formation_system import follow_slots
from world.battlefield import BattleResult, PlayerInput
from tests.helpers import DATA, bot_input, skirmish

STEP = 1 / 60


def run(bf, seconds, step=STEP, bot=True):
    for _ in range(int(seconds / step)):
        bf.update(step, bot_input(bf) if bot else PlayerInput())
        if bf.result != BattleResult.ONGOING:
            break


class Setup(unittest.TestCase):
    def test_new_battle_has_general_four_soldiers_and_enemy_squad(self):
        bf = skirmish()
        self.assertTrue(bf.general_alive)
        self.assertEqual(len(bf.allied_soldiers()), 4)
        self.assertEqual(len(bf.enemies()), 5)
        self.assertEqual(bf.result, BattleResult.ONGOING)

    def test_unit_ids_unique(self):
        bf = skirmish()
        ids = [u.uid for u in bf.units.values()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_spawn_unknown_class_raises(self):
        with self.assertRaises(KeyError):
            skirmish().spawn_unit(Team.ENEMY, "dragon", 10, 10)

    def test_follow_slots_are_distinct(self):
        slots = follow_slots(100, 100, 8, 55, 36, 6)
        self.assertEqual(len(set((round(x, 3), round(y, 3)) for x, y in slots)), 8)


class GeneralControl(unittest.TestCase):
    def test_movement_distance_independent_of_step_size(self):
        for step in (1 / 30, 1 / 60, 1 / 240):
            bf = skirmish()
            x0 = bf.general.x
            for _ in range(int(1.0 / step)):
                bf.movement.move_by_direction(bf.general, 1, 0, step)
            self.assertAlmostEqual(bf.general.x - x0, bf.general.stats.speed, delta=1.0)

    def test_diagonal_not_faster(self):
        bf = skirmish()
        g = bf.general
        x0, y0 = g.x, g.y
        bf.movement.move_by_direction(g, 1, 1, 1.0)
        self.assertAlmostEqual(math.hypot(g.x - x0, g.y - y0), g.stats.speed, places=3)

    def test_general_stays_inside_battlefield(self):
        bf = skirmish()
        for _ in range(600):
            bf.movement.move_by_direction(bf.general, -1, -1, STEP)
        self.assertGreaterEqual(bf.general.x, bf.general.radius)
        self.assertGreaterEqual(bf.general.y, bf.general.radius)

    def test_attack_held_does_not_hit_every_step(self):
        bf = skirmish()
        enemy = bf.enemies()[0]
        enemy.x, enemy.y = bf.general.x + 30, bf.general.y
        enemy.health = 10_000   # effectively a dummy; ensure it is the in-reach target
        hp0 = enemy.health
        for _ in range(60):     # 1 second of held attack
            bf.combat.tick_cooldowns(bf.units.values(), STEP)
            bf._update_general(PlayerInput(attack_held=True), STEP)
        hits = round((hp0 - enemy.health) / bf.general.stats.damage)
        self.assertEqual(hits, 2)  # t=0 and t=0.6 with a 0.6 s cooldown

    def test_selected_target_preferred_when_in_reach(self):
        bf = skirmish()
        g = bf.general
        a, b = bf.enemies()[0], bf.enemies()[1]
        a.x, a.y = g.x + 30, g.y
        b.x, b.y = g.x - 40, g.y
        bf.select_at(b.x, b.y)
        self.assertEqual(bf.selected_target_id, b.uid)
        self.assertIs(bf._general_attack_target(), b)

    def test_click_empty_ground_clears_selection(self):
        bf = skirmish()
        e = bf.enemies()[0]
        bf.select_at(e.x, e.y)
        self.assertEqual(bf.selected_target_id, e.uid)
        bf.select_at(5, 5)
        self.assertIsNone(bf.selected_target_id)


class Soldiers(unittest.TestCase):
    def test_soldiers_follow_the_general(self):
        bf = skirmish()
        for e in bf.enemies():
            e.take_damage(999)
        bf._cleanup()
        bf.general.x, bf.general.y = 600, 300
        # The battle is already won (no enemies), so drive the AI step directly.
        for _ in range(600):
            bf.combat.tick_cooldowns(bf.units.values(), STEP)
            bf.ai.update(bf.units, bf.general, STEP)
            bf.movement.separate(list(bf.units.values()))
        for s in bf.allied_soldiers():
            self.assertLess(s.distance_to(bf.general), 120)
            self.assertEqual(s.order, Order.FOLLOW)

    def test_separation_prevents_overlap(self):
        bf = skirmish()
        for s in bf.allied_soldiers():
            s.x, s.y = 500, 300
        for _ in range(60):
            bf.movement.separate(list(bf.units.values()))
        units = list(bf.units.values())
        for i, a in enumerate(units):
            for b in units[i + 1:]:
                self.assertGreaterEqual(a.distance_to(b), (a.radius + b.radius) * 0.95)

    def test_soldiers_engage_nearby_enemy(self):
        bf = skirmish()
        soldier = bf.allied_soldiers()[0]
        enemy = bf.enemies()[0]
        enemy.x, enemy.y = soldier.x + 100, soldier.y
        bf.ai.update(bf.units, bf.general, STEP)
        self.assertEqual(soldier.order, Order.ATTACK)
        self.assertEqual(soldier.target_id, enemy.uid)

    def test_enemies_idle_until_player_is_near(self):
        bf = skirmish()
        bf.update(STEP, PlayerInput())
        self.assertTrue(all(e.order == Order.IDLE for e in bf.enemies()))


class Outcome(unittest.TestCase):
    def test_scripted_player_wins_and_enemies_are_defeated(self):
        bf = skirmish()
        run(bf, 90)
        self.assertEqual(bf.result, BattleResult.VICTORY)
        self.assertEqual(bf.enemies(), [])
        self.assertTrue(bf.general_alive)

    def test_outcome_stable_across_step_sizes(self):
        for step in (1 / 30, 1 / 60, 1 / 120):
            bf = skirmish()
            run(bf, 120, step)
            self.assertEqual(bf.result, BattleResult.VICTORY, f"step={step}")

    def test_defeat_when_general_falls(self):
        bf = skirmish()
        bf.general.take_damage(9999)
        bf.update(STEP, PlayerInput())
        self.assertEqual(bf.result, BattleResult.DEFEAT)
        self.assertNotIn(bf.general.uid, bf.units)

    def test_defeat_takes_priority_when_both_sides_fall(self):
        bf = skirmish()
        bf.general.take_damage(9999)
        for e in bf.enemies():
            e.take_damage(9999)
        bf.update(STEP, PlayerInput())
        self.assertEqual(bf.result, BattleResult.DEFEAT)

    def test_simulation_stops_after_result(self):
        bf = skirmish()
        bf.general.take_damage(9999)
        bf.update(STEP, PlayerInput())
        t = bf.elapsed
        bf.update(STEP, PlayerInput())
        self.assertEqual(bf.elapsed, t)

    def test_idle_player_is_pressured_by_enemies(self):
        """Enemies are actually hostile: a general who stands still gets attacked."""
        bf = skirmish()
        for e in bf.enemies():
            e.x, e.y = bf.general.x + 150, bf.general.y + (e.uid * 7 % 40)
        run(bf, 20, bot=False)
        total_player_hp = sum(u.health for u in bf.units.values() if u.team == Team.PLAYER)
        self.assertLess(total_player_hp, 150 + 4 * 50)

    def test_defeated_units_leave_battlefield_and_clear_references(self):
        bf = skirmish()
        enemy = bf.enemies()[0]
        bf.select_at(enemy.x, enemy.y)
        soldier = bf.allied_soldiers()[0]
        soldier.target_id = enemy.uid
        enemy.take_damage(999)
        bf.update(STEP, PlayerInput())
        self.assertNotIn(enemy.uid, bf.units)
        self.assertIsNone(bf.selected_target_id)
        self.assertNotEqual(soldier.target_id, enemy.uid)

    def test_battle_statistics(self):
        bf = skirmish()
        bf.enemies()[0].take_damage(999)
        bf.allied_soldiers()[0].take_damage(999)
        bf.update(STEP, PlayerInput())
        self.assertEqual((bf.enemies_defeated, bf.allies_lost), (1, 1))

    def test_battle_ended_event(self):
        bus = EventBus()
        seen = []
        bus.subscribe(event_bus.BATTLE_ENDED, seen.append)
        bf = skirmish(bus)
        bf.general.take_damage(9999)
        bf.update(STEP, PlayerInput())
        self.assertEqual(seen, [BattleResult.DEFEAT])

    def test_general_defeated_soldiers_do_not_crash(self):
        bf = skirmish()
        bf.general.take_damage(9999)
        bf._cleanup()
        for _ in range(30):
            bf.ai.update(bf.units, None, STEP)
        self.assertTrue(all(s.order in (Order.IDLE, Order.ATTACK) for s in bf.allied_soldiers()))


if __name__ == "__main__":
    unittest.main()
