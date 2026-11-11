"""Main application entry point."""

import sys
from src.gui import RothSimulatorGUI


def main():
    """Launch the Roth Conversion Simulator GUI."""
    app = RothSimulatorGUI()
    app.run()


if __name__ == '__main__':
    main()
