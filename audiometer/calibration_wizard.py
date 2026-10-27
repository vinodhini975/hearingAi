"""
Calibration Wizard for Clinical Software Audiometer.
Guides the operator through sound level meter (SLM) or artificial ear reference calibration,
plays 0 dBFS pure tones at each frequency, and computes dBFS_to_SPL_reference.
"""

import sys
import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QProgressBar, QGroupBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from audiometer.calibration import CalibrationManager, STANDARD_FREQUENCIES, BC_FREQUENCIES
from audiometer.audio_engine import AudioEngine

logger = logging.getLogger(__name__)


class CalibrationWizardDialog(QDialog):
    """
    Step-by-step transducer calibration wizard.
    """

    def __init__(self, cal_mgr: CalibrationManager, audio_engine: AudioEngine, parent=None):
        super().__init__(parent)
        self.cal = cal_mgr
        self.audio = audio_engine
        self.setWindowTitle("Audiometer Calibration Wizard — ISO 389 Reference Setup")
        self.setMinimumSize(850, 650)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QLabel {
                color: #f8fafc;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #38bdf8;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px 16px;
                color: #f8fafc;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
            }
            QPushButton:pressed {
                background-color: #0284c7;
            }
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                gridline-color: #334155;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                font-weight: bold;
                border: 1px solid #334155;
                padding: 6px;
            }
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 6px;
                color: #f8fafc;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
        """)

        self.test_frequency = 1000
        self.is_tone_playing = False
        self.setup_ui()
        self.load_profile_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title and Instructions Banner
        title = QLabel("TRANSOUCER CALIBRATION & RETSPL ALIGNMENT")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8; letter-spacing: 1px;")
        layout.addWidget(title)

        desc = QLabel(
            "Follow the clinical protocol: Connect your 6cc/2cc acoustic coupler or Sound Level Meter (SLM). "
            "For each octave, play a full-scale (0 dBFS) sine wave. Enter the measured SPL on the meter. "
            "The system will compute and lock the transfer function dBFS = target_SPL - dBFS_ref."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.4;")
        layout.addWidget(desc)

        # Profile selection row
        prof_box = QGroupBox("Select / Create Transducer Profile")
        p_layout = QHBoxLayout(prof_box)

        p_layout.addWidget(QLabel("Active Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setStyleSheet("background-color: #1e293b; color: white; padding: 5px; border: 1px solid #475569;")
        for pid, pname in self.cal.list_profiles().items():
            self.profile_combo.addItem(pname, pid)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        p_layout.addWidget(self.profile_combo)

        self.btn_new_profile = QPushButton("+ New Profile")
        self.btn_new_profile.clicked.connect(self.create_new_profile_dialog)
        p_layout.addWidget(self.btn_new_profile)
        p_layout.addStretch()

        layout.addWidget(prof_box)

        # Calibration Table
        table_box = QGroupBox("Frequency Calibration Matrix (0 dBFS -> Measured dB SPL)")
        t_layout = QVBoxLayout(table_box)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Frequency (Hz)", "RETSPL (dB SPL)", "Ref at 0 dBFS (dB SPL)", "Play Calibration Tone", "Enter Measured SPL"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        t_layout.addWidget(self.table)

        layout.addWidget(table_box)

        # Tone status & safety warnings
        status_bar = QHBoxLayout()
        self.lbl_tone_status = QLabel("Ready to calibrate. Audio output amplitude locked digitally.")
        self.lbl_tone_status.setStyleSheet("color: #22c55e; font-weight: bold;")
        status_bar.addWidget(self.lbl_tone_status)
        status_bar.addStretch()

        self.btn_stop_all = QPushButton("STOP AUDIO [Esc]")
        self.btn_stop_all.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold;")
        self.btn_stop_all.clicked.connect(self.stop_tone)
        status_bar.addWidget(self.btn_stop_all)
        layout.addLayout(status_bar)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        self.btn_save = QPushButton("Save Calibration & Apply")
        self.btn_save.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 10px 20px;")
        self.btn_save.clicked.connect(self.save_and_close)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def load_profile_data(self):
        """Populates the table with frequencies, RETSPLs, and current references."""
        profile = self.cal.get_active_profile()
        is_bc = profile.get("is_bone_conduction", False)
        freqs = BC_FREQUENCIES if is_bc else STANDARD_FREQUENCIES

        self.table.setRowCount(len(freqs))
        retspls = profile.get("retspl", {})
        dbfs_refs = profile.get("dbfs_to_spl_reference", {})

        for row, f in enumerate(freqs):
            str_f = str(f)
            # 0: Freq
            item_f = QTableWidgetItem(f"{f} Hz")
            item_f.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_f.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, item_f)

            # 1: RETSPL
            retspl_val = retspls.get(str_f, 10.0)
            item_r = QTableWidgetItem(f"{retspl_val:.1f}")
            item_r.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_r.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, item_r)

            # 2: Current Ref
            ref_val = dbfs_refs.get(str_f, 110.0)
            item_ref = QTableWidgetItem(f"{ref_val:.1f}")
            item_ref.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_ref.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, item_ref)

            # 3: Play Button
            btn_play = QPushButton("▶ Play 0 dBFS")
            btn_play.setStyleSheet("background-color: #0369a1; padding: 4px;")
            btn_play.clicked.connect(lambda checked, freq=f: self.play_calibration_tone(freq))
            self.table.setCellWidget(row, 3, btn_play)

            # 4: Measured SPL input
            edit_measured = QLineEdit(f"{ref_val:.1f}")
            edit_measured.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 4, edit_measured)

    def on_profile_changed(self, idx):
        pid = self.profile_combo.currentData()
        if pid:
            self.cal.set_active_profile(pid)
            self.load_profile_data()

    def play_calibration_tone(self, frequency: int):
        """Plays 0 dBFS sine wave (amplitude = 1.0) for calibration reading."""
        self.stop_tone()
        self.lbl_tone_status.setText(f"Playing 0 dBFS tone at {frequency} Hz... Measure with SLM.")
        self.lbl_tone_status.setStyleSheet("color: #f59e0b; font-weight: bold;")
        self.is_tone_playing = True

        # Generate stereo buffer with tone on both channels for coupler calibration
        tone = self.audio.generate_pure_tone(frequency, duration_s=6.0, amplitude=1.0)
        stereo = np.column_stack([tone, tone])
        self.audio.play_buffer(stereo, blocking=False)

    def stop_tone(self):
        self.audio.stop()
        self.is_tone_playing = False
        self.lbl_tone_status.setText("Tone stopped.")
        self.lbl_tone_status.setStyleSheet("color: #94a3b8;")

    def save_and_close(self):
        """Saves measured values to calibration profile."""
        profile = self.cal.get_active_profile()
        is_bc = profile.get("is_bone_conduction", False)
        freqs = BC_FREQUENCIES if is_bc else STANDARD_FREQUENCIES

        for row, f in enumerate(freqs):
            widget = self.table.cellWidget(row, 4)
            if isinstance(widget, QLineEdit):
                try:
                    val = float(widget.text().strip())
                    self.cal.calibrate_frequency_point(f, val)
                except ValueError:
                    pass

        self.cal.save_profiles()
        QMessageBox.information(self, "Calibration Saved", "Transducer profile successfully calibrated and saved!")
        self.accept()

    def create_new_profile_dialog(self):
        """Quick dialog to register new headphone / earbud profile."""
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Profile", "Enter Transducer Model Name:")
        if ok and name.strip():
            pid = name.strip().replace(" ", "_")
            self.cal.create_custom_profile(
                profile_id=pid,
                name=name.strip(),
                transducer_type="air_conduction",
                is_bone_conduction=False,
                retspl_map={str(f): 10.0 for f in STANDARD_FREQUENCIES},
                dbfs_ref_map={str(f): 110.0 for f in STANDARD_FREQUENCIES}
            )
            self.profile_combo.addItem(name.strip(), pid)
            self.profile_combo.setCurrentIndex(self.profile_combo.count() - 1)
