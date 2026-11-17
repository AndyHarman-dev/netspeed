import argparse

from netspeed import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="netspeed")
    parser.add_argument("--version", action="version", version=f"netspeed {__version__}")
    parser.parse_args(argv)
    return 0
