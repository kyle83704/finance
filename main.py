"""Main application entry point."""

import sys
from src.gui_v2 import RothSimulatorGUIv2


def main():
    """Launch the Roth Conversion Simulator GUI (v2 - single page with search & ML)."""
    app = RothSimulatorGUIv2()
    app.run()


if __name__ == '__main__':
    main()
