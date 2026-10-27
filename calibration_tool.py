"""
Standalone Transducer Calibration Wizard.
Launches the ISO 389 reference setup dialog directly for laboratory or field calibration.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from audiometer.calibration import CalibrationManager
from audiometer.audio_engine import AudioEngine
from audiometer.calibration_wizard import CalibrationWizardDialog

def main():
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    cal_mgr = CalibrationManager()
    audio = AudioEngine(cal_mgr)

    wizard = CalibrationWizardDialog(cal_mgr, audio)
    wizard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
