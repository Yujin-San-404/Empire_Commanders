"""Smoke test with REAL pygame (headless 'dummy' video driver). Skipped if pygame is absent."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame  # noqa: F401
    HAVE_PYGAME = True
except ImportError:
    HAVE_PYGAME = False


@unittest.skipUnless(HAVE_PYGAME, "pygame is not installed")
class SmokeTest(unittest.TestCase):
    def test_launch_play_to_victory_and_restart(self):
        from game.game import Game
        from tests.helpers import bot_input
        from world.battlefield import BattleResult

        game = Game()
        try:
            for _ in range(10):                       # idle frames render without error
                game.step_frame(1 / 60, [])
            game.input.scripted = lambda: bot_input(game.battle)
            for _ in range(60 * 60):
                game.step_frame(1 / 60, [])
                if game.battle_over:
                    break
            self.assertEqual(game.battle.result, BattleResult.VICTORY)
            game.step_frame(1 / 60, [])               # result overlay renders
            game.new_battle()
            self.assertEqual(game.battle.result, BattleResult.ONGOING)
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
