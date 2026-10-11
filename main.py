"""Empire Commanders - entry point.   Usage: python main.py [--frames N]"""
import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Empire Commanders")
    parser.add_argument("--frames", type=int, default=None,
                        help="run this many frames then exit (smoke testing)")
    args = parser.parse_args()

    try:
        import pygame  # noqa: F401
    except ImportError:
        print("Pygame is not installed. Run:  pip install -r requirements.txt", file=sys.stderr)
        return 1

    from game.config import DataError
    from game.game import Game

    try:
        game = Game()
    except DataError as exc:
        print(f"Could not start: {exc}", file=sys.stderr)
        return 1
    game.run(max_frames=args.frames)
    return 0


if __name__ == "__main__":
    sys.exit(main())
