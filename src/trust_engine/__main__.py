"""Entry point for `python -m trust_engine`."""

from trust_engine import __version__


def main() -> None:
    print(f"Trust Engine v{__version__}")


if __name__ == "__main__":
    main()
