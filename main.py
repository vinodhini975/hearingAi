"""
Main Desktop Entry Point for Clinical Software Audiometer.
Launches the PyQt6 diagnostic audiometer application with high-DPI scaling.
"""

import sys
import os
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from audiometer.gui import AudiometerMainWindow

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Enable High DPI pixmaps
    app = QApplication(sys.argv)
    app.setApplicationName("Clinical Software Audiometer")
    app.setOrganizationName("HearingAI Diagnostics")

    window = AudiometerMainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
