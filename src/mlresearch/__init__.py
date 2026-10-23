"""Reproducible budgeted perturbation-transfer research."""

__version__ = "0.2.0"


def main() -> None:
    """Run the command-line interface."""
    from mlresearch.cli import main as cli_main

    cli_main()
