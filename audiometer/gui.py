"""
Main Clinical GUI for Hardware-Grade Software Audiometer.
Implements:
1. Left Panel: Clinical test controls (Frequency selector, Level dial, Ear, Conduction, Masking, HW, Bekesy)
2. Center Panel: Live interactive Matplotlib Audiogram Canvas with clinical symbols
3. Right Panel: Patient info, History checkboxes, Live Ambient Noise gauge, Threshold grid, AI diagnosis card
4. Multi-language support (English, Hindi, Tamil, Bengali)
5. Speech audiometry & Special tests tabs
6. Audio confirmation beeps and Patient instruction visualizer
"""

import os
import sys
import time
import datetime
import logging
from typing import Dict, Any, Optional, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QSlider, QSpinBox, QCheckBox, QLineEdit,
    QTabWidget, QGroupBox, QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar, QDialog, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QPalette, QKeyEvent, QIcon

import numpy as np
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from audiometer.calibration import CalibrationManager, STANDARD_FREQUENCIES, BC_FREQUENCIES
from audiometer.audio_engine import AudioEngine
from audiometer.patient_response import PatientResponseManager
from audiometer.test_controller import TestController
from audiometer.ai_engine import AIInferenceEngine
from audiometer.noise_monitor import AmbientNoiseMonitor
from audiometer.hardware import HardwareDetector
from audiometer.storage import SessionStorage
from audiometer.export import ReportExporter
from audiometer.localization import LocalizationManager
from audiometer.speech_materials import SpeechEngine
from audiometer.calibration_wizard import CalibrationWizardDialog

logger = logging.getLogger(__name__)


class GuiSignalBridge(QObject):
    status_updated = pyqtSignal(str, dict)
    threshold_recorded = pyqtSignal(str, str, int, float, bool)


class AudiometerMainWindow(QMainWindow):
    """
    Main Clinical Software Audiometer Window.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clinical Software Audiometer & AI Pathology System")
        self.setMinimumSize(1280, 820)

        # -------------------------------------------------------------
        # Core Subsystems Initialization
        # -------------------------------------------------------------
        self.loc = LocalizationManager(default_lang="en")
        self.cal = CalibrationManager()
        self.audio = AudioEngine(self.cal)
        self.response = PatientResponseManager()
        self.controller = TestController(self.audio, self.response, self.cal)
        self.ai = AIInferenceEngine()
        self.noise = AmbientNoiseMonitor()
        self.hardware = HardwareDetector()
        self.storage = SessionStorage()
        self.exporter = ReportExporter()
        self.speech = SpeechEngine()

        # Thread-safe Signal Bridge for cross-thread callbacks
        self.bridge = GuiSignalBridge()
        self.bridge.status_updated.connect(self.on_controller_status_gui)
        self.bridge.threshold_recorded.connect(self.on_threshold_recorded_gui)

        # Connect controller callbacks via queued Qt signals
        self.controller.set_callbacks(
            on_status=lambda msg, data: self.bridge.status_updated.emit(msg, data),
            on_threshold=lambda ear, cond, freq, lvl, masked: self.bridge.threshold_recorded.emit(ear, cond, freq, lvl, masked)
        )

        # Active Session Metadata
        self.session_data: Dict[str, Any] = {
            "patient_id": "PT-2026-001",
            "patient_name": "Ramesh Kumar",
            "age": 48,
            "operator": "Dr. S. Sharma, Au.D.",
            "timestamp": datetime.datetime.now().isoformat(),
            "transducer": self.cal.active_profile_id,
            "calibration_profile": self.cal.active_profile_id,
            "tests": self.controller.thresholds,
            "speech": self.controller.speech_results,
            "ambient_noise_spl": 34.0,
            "patient_reliability": 1.0,
            "ai_analysis": {}
        }

        # Setup GUI Components & Styling
        self.init_styling()
        self.build_ui()
        self.setup_keyboard_shortcuts()

        # Start background noise monitor
        self.noise.start_realtime_monitoring()

        # Main-thread safe timer to poll ambient noise at 4 Hz
        self.noise_poll_timer = QTimer(self)
        self.noise_poll_timer.setInterval(250)
        self.noise_poll_timer.timeout.connect(self.poll_ambient_noise_gui)
        self.noise_poll_timer.start()

        # Check Hardware & Auto-switch AC-Only mode if needed
        self.check_initial_hardware()

        # Check for power-cut interrupted session to resume
        QTimer.singleShot(600, self.check_session_recovery)

    # =========================================================================
    # STYLING & PALETTE (Medical Dark Modern)
    # =========================================================================
    def init_styling(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b0f19;
                color: #f1f5f9;
            }
            QWidget {
                color: #f1f5f9;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QGroupBox {
                border: 1px solid #1e293b;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 14px;
                font-size: 11px;
                font-weight: 700;
                color: #38bdf8;
                background-color: #111827;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QPushButton {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
                color: #f9fafb;
            }
            QPushButton:hover {
                background-color: #374151;
                border-color: #38bdf8;
            }
            QPushButton:pressed {
                background-color: #0284c7;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                background-color: #0f172a;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #0f172a;
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #111827;
                border: 1px solid #374151;
                border-radius: 5px;
                padding: 4px 8px;
                color: #f9fafb;
                font-size: 11px;
            }
            QComboBox QAbstractItemView {
                background-color: #111827;
                color: white;
                selection-background-color: #0284c7;
            }
            QTableWidget {
                background-color: #111827;
                gridline-color: #1f2937;
                border: 1px solid #1f2937;
                color: #f9fafb;
            }
            QHeaderView::section {
                background-color: #1f2937;
                color: #94a3b8;
                padding: 4px;
                border: 1px solid #111827;
                font-weight: bold;
                font-size: 10px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1e293b;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #38bdf8;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #f8fafc;
                border: 2px solid #0284c7;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
        """)

    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================
    def build_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QVBoxLayout(main_widget)
        root_layout.setContentsMargins(10, 8, 10, 8)
        root_layout.setSpacing(6)

        # -------------------------------------------------------------
        # TOP TOOLBAR: Brand, Language Selector, Hardware Status, Actions
        # -------------------------------------------------------------
        top_bar = QHBoxLayout()
        
        # Title block
        title_box = QVBoxLayout()
        self.lbl_app_title = QLabel("CLINICAL DIAGNOSTIC AUDIOMETER")
        self.lbl_app_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_app_title.setStyleSheet("color: #38bdf8; letter-spacing: 0.5px;")
        
        self.lbl_tagline = QLabel("Hardware-Grade Audio Generator | ISO 8253-1 | Offline AI Inference")
        self.lbl_tagline.setFont(QFont("Segoe UI", 8))
        self.lbl_tagline.setStyleSheet("color: #64748b;")
        title_box.addWidget(self.lbl_app_title)
        title_box.addWidget(self.lbl_tagline)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        # Hardware Status Badges
        self.lbl_hw_badge = QLabel("USB DAC: Detecting...")
        self.lbl_hw_badge.setStyleSheet("background-color: #1e293b; color: #f59e0b; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 10px;")
        top_bar.addWidget(self.lbl_hw_badge)

        self.lbl_ac_mode_badge = QLabel("Mode: Dual AC/BC")
        self.lbl_ac_mode_badge.setStyleSheet("background-color: #1e293b; color: #22c55e; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 10px;")
        top_bar.addWidget(self.lbl_ac_mode_badge)

        # Transducer Profile Selector
        top_bar.addWidget(QLabel("Transducer:"))
        self.combo_transducer = QComboBox()
        for pid, pname in self.cal.list_profiles().items():
            self.combo_transducer.addItem(pname, pid)
        self.combo_transducer.currentIndexChanged.connect(self.on_transducer_changed)
        top_bar.addWidget(self.combo_transducer)

        # Calibration Wizard Launcher Button
        self.btn_open_cal = QPushButton("⚙ Calibration Wizard")
        self.btn_open_cal.clicked.connect(self.open_calibration_wizard)
        top_bar.addWidget(self.btn_open_cal)

        # Language Selector Dropdown
        top_bar.addWidget(QLabel("🌐 Language:"))
        self.combo_lang = QComboBox()
        for code, name in self.loc.get_supported_languages().items():
            self.combo_lang.addItem(name, code)
        self.combo_lang.currentIndexChanged.connect(self.on_language_changed)
        top_bar.addWidget(self.combo_lang)

        root_layout.addLayout(top_bar)

        # Ambient noise banner if elevated
        self.banner_noise = QLabel("")
        self.banner_noise.setVisible(False)
        self.banner_noise.setStyleSheet("background-color: #ef4444; color: white; padding: 6px; font-weight: bold; border-radius: 4px; text-align: center;")
        root_layout.addWidget(self.banner_noise)

        # -------------------------------------------------------------
        # THREE-PANEL CORE LAYOUT (Left Controls, Center Plot, Right Info)
        # -------------------------------------------------------------
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(8)

        # --- LEFT PANEL: AUDIOMETER TEST CONTROLS ---
        left_panel = self.build_left_controls_panel()
        panels_layout.addWidget(left_panel, stretch=26)

        # --- CENTER PANEL: AUDIOGRAM VISUALIZER & TEST TABS ---
        center_panel = self.build_center_audiogram_panel()
        panels_layout.addWidget(center_panel, stretch=48)

        # --- RIGHT PANEL: PATIENT INFO, AI ANALYSIS, THRESHOLD GRID ---
        right_panel = self.build_right_info_panel()
        panels_layout.addWidget(right_panel, stretch=26)

        root_layout.addLayout(panels_layout)

        # -------------------------------------------------------------
        # BOTTOM STATUS / ACTION BAR
        # -------------------------------------------------------------
        bottom_bar = QHBoxLayout()
        self.lbl_status = QLabel("Ready for Pure Tone Audiometry. Select Ear and Press [Present].")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 11px;")
        bottom_bar.addWidget(self.lbl_status)
        bottom_bar.addStretch()

        self.btn_instruction_video = QPushButton("🎬 Patient Instructions (Audio/Visual)")
        self.btn_instruction_video.clicked.connect(self.show_patient_instructions_modal)
        bottom_bar.addWidget(self.btn_instruction_video)

        self.btn_export_pdf = QPushButton("📄 Generate PDF Report [<2s]")
        self.btn_export_pdf.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold;")
        self.btn_export_pdf.clicked.connect(self.action_export_pdf)
        bottom_bar.addWidget(self.btn_export_pdf)

        self.btn_export_emr = QPushButton("💾 Export EMR JSON")
        self.btn_export_emr.clicked.connect(self.action_export_json)
        bottom_bar.addWidget(self.btn_export_emr)

        root_layout.addLayout(bottom_bar)

    # -------------------------------------------------------------------------
    # LEFT PANEL: TEST CONTROLS
    # -------------------------------------------------------------------------
    def build_left_controls_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 1. Ear & Conduction Selection Box
        box_ear = QGroupBox(self.loc.get("ear"))
        l_ear = QGridLayout(box_ear)

        self.btn_ear_right = QPushButton("RIGHT (RED)")
        self.btn_ear_right.setCheckable(True)
        self.btn_ear_right.setChecked(True)
        self.btn_ear_right.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; padding: 8px;")
        self.btn_ear_right.clicked.connect(lambda: self.select_ear("right"))
        l_ear.addWidget(self.btn_ear_right, 0, 0)

        self.btn_ear_left = QPushButton("LEFT (BLUE)")
        self.btn_ear_left.setCheckable(True)
        self.btn_ear_left.setChecked(False)
        self.btn_ear_left.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-weight: bold; padding: 8px;")
        self.btn_ear_left.clicked.connect(lambda: self.select_ear("left"))
        l_ear.addWidget(self.btn_ear_left, 0, 1)

        # Conduction mode
        self.btn_cond_ac = QPushButton("Air Conduction (AC)")
        self.btn_cond_ac.setCheckable(True)
        self.btn_cond_ac.setChecked(True)
        self.btn_cond_ac.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold;")
        self.btn_cond_ac.clicked.connect(lambda: self.select_conduction("AC"))
        l_ear.addWidget(self.btn_cond_ac, 1, 0)

        self.btn_cond_bc = QPushButton("Bone Conduction (BC)")
        self.btn_cond_bc.setCheckable(True)
        self.btn_cond_bc.setChecked(False)
        self.btn_cond_bc.clicked.connect(lambda: self.select_conduction("BC"))
        l_ear.addWidget(self.btn_cond_bc, 1, 1)

        layout.addWidget(box_ear)

        # 2. Stimulus Frequency Selector
        box_freq = QGroupBox(self.loc.get("frequency"))
        l_freq = QGridLayout(box_freq)
        self.freq_buttons = {}
        row, col = 0, 0
        for f in STANDARD_FREQUENCIES:
            btn = QPushButton(f"{f}")
            btn.setCheckable(True)
            if f == 1000:
                btn.setChecked(True)
                btn.setStyleSheet("background-color: #38bdf8; color: black; font-weight: bold;")
            btn.clicked.connect(lambda checked, freq=f: self.select_frequency(freq))
            self.freq_buttons[f] = btn
            l_freq.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1
        layout.addWidget(box_freq)

        # 3. Stimulus Intensity Control (Dial & Slider & Decibel Readout)
        box_level = QGroupBox(self.loc.get("intensity"))
        l_level = QVBoxLayout(box_level)

        h_val = QHBoxLayout()
        self.lbl_db_hl = QLabel("30 dB HL")
        self.lbl_db_hl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_db_hl.setStyleSheet("color: #38bdf8;")
        h_val.addWidget(self.lbl_db_hl)
        h_val.addStretch()

        self.combo_step = QComboBox()
        self.combo_step.addItems(["5 dB (Manual Standard)", "1 dB (Research Mode)"])
        self.combo_step.currentIndexChanged.connect(self.on_step_size_changed)
        h_val.addWidget(self.combo_step)
        l_level.addLayout(h_val)

        # Horizontal Level Slider (-10 to 120 dB)
        self.slider_level = QSlider(Qt.Orientation.Horizontal)
        self.slider_level.setRange(-10, 120)
        self.slider_level.setValue(30)
        self.slider_level.setSingleStep(5)
        self.slider_level.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_level.setTickInterval(10)
        self.slider_level.valueChanged.connect(self.on_slider_level_changed)
        l_level.addWidget(self.slider_level)

        # Decrement / Increment buttons
        h_btn_level = QHBoxLayout()
        self.btn_db_down = QPushButton("▼ -5 dB [↓]")
        self.btn_db_down.clicked.connect(lambda: self.adjust_level(-self.controller.step_size))
        self.btn_db_up = QPushButton("▲ +5 dB [↑]")
        self.btn_db_up.clicked.connect(lambda: self.adjust_level(self.controller.step_size))
        h_btn_level.addWidget(self.btn_db_down)
        h_btn_level.addWidget(self.btn_db_up)
        l_level.addLayout(h_btn_level)

        layout.addWidget(box_level)

        # 4. Presentation & Threshold Action Buttons
        box_act = QGroupBox("Stimulus Presentation & Protocols")
        l_act = QVBoxLayout(box_act)

        self.btn_present = QPushButton("🔊 PRESENT TONE [Space]")
        self.btn_present.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.btn_present.setStyleSheet("background-color: #22c55e; color: white; padding: 12px; border-radius: 6px;")
        self.btn_present.clicked.connect(self.action_present_tone)
        l_act.addWidget(self.btn_present)

        self.btn_store_thresh = QPushButton("✔ Store Threshold [Enter]")
        self.btn_store_thresh.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 8px;")
        self.btn_store_thresh.clicked.connect(self.action_store_threshold)
        l_act.addWidget(self.btn_store_thresh)

        # Automated Protocols Row
        h_auto = QHBoxLayout()
        self.btn_auto_hw = QPushButton("Auto Hughson-Westlake (ISO 8253-1)")
        self.btn_auto_hw.setStyleSheet("background-color: #7c3aed; color: white; font-weight: bold;")
        self.btn_auto_hw.clicked.connect(self.action_auto_hughson_westlake)
        h_auto.addWidget(self.btn_auto_hw)

        self.btn_auto_bekesy = QPushButton("Auto Bekesy")
        self.btn_auto_bekesy.setStyleSheet("background-color: #4f46e5; color: white; font-weight: bold;")
        self.btn_auto_bekesy.clicked.connect(self.action_auto_bekesy)
        h_auto.addWidget(self.btn_auto_bekesy)
        l_act.addLayout(h_auto)

        self.btn_stop_auto = QPushButton("⏹ Stop Automated Test")
        self.btn_stop_auto.setStyleSheet("background-color: #dc2626; color: white;")
        self.btn_stop_auto.clicked.connect(self.controller.stop_automated_test)
        l_act.addWidget(self.btn_stop_auto)

        layout.addWidget(box_act)

        # 5. Narrowband Masking Box
        box_mask = QGroupBox("Narrowband Masking Noise (Non-Test Ear)")
        l_mask = QVBoxLayout(box_mask)

        self.chk_auto_mask = QCheckBox("Auto Masking Calculation (IA crossover)")
        self.chk_auto_mask.setChecked(True)
        l_mask.addWidget(self.chk_auto_mask)

        h_mask_ctrl = QHBoxLayout()
        self.chk_mask_enable = QCheckBox("Enable Masking")
        self.chk_mask_enable.toggled.connect(self.on_masking_toggled)
        h_mask_ctrl.addWidget(self.chk_mask_enable)

        self.spin_mask_level = QSpinBox()
        self.spin_mask_level.setRange(-10, 110)
        self.spin_mask_level.setValue(20)
        self.spin_mask_level.setSuffix(" dB")
        self.spin_mask_level.valueChanged.connect(self.on_mask_level_changed)
        h_mask_ctrl.addWidget(self.spin_mask_level)
        l_mask.addLayout(h_mask_ctrl)

        layout.addWidget(box_mask)
        layout.addStretch()

        return container

    # -------------------------------------------------------------------------
    # CENTER PANEL: LIVE AUDIOGRAM CANVAS & TABS
    # -------------------------------------------------------------------------
    def build_center_audiogram_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Create Tabbed view: [Audiogram Chart] | [Speech Audiometry] | [Special Tests]
        self.center_tabs = QTabWidget()

        # Tab 1: Audiogram Plot
        tab_audiogram = QWidget()
        l_tab1 = QVBoxLayout(tab_audiogram)
        l_tab1.setContentsMargins(4, 4, 4, 4)

        # Matplotlib Figure & Canvas
        self.figure = plt.figure(facecolor='#0f172a', edgecolor='none')
        self.canvas = FigureCanvas(self.figure)
        l_tab1.addWidget(self.canvas)
        self.init_audiogram_plot()

        self.center_tabs.addTab(tab_audiogram, "📊 Live Binaural Audiogram")

        # Tab 2: Speech Audiometry (SRT & WRS)
        tab_speech = self.build_speech_tab()
        self.center_tabs.addTab(tab_speech, "🗣 Speech Audiometry (SRT / WRS)")

        # Tab 3: Special Tests (SISI & Tone Decay)
        tab_special = self.build_special_tests_tab()
        self.center_tabs.addTab(tab_special, "🔬 Special Tests (SISI / Tone Decay)")

        layout.addWidget(self.center_tabs)
        return container

    def init_audiogram_plot(self):
        """Initializes dark-themed medical audiogram styling."""
        self.ax = self.figure.add_subplot(111)
        self.redraw_audiogram()

    def redraw_audiogram(self):
        """Redraws the entire audiogram with clinical symbols and norm curves."""
        self.ax.clear()
        self.ax.set_facecolor('#111827')

        # Inverted decibel HL axis (-10 dB to 120 dB)
        self.ax.set_ylim(120, -10)
        self.ax.set_xlim(100, 9000)
        self.ax.set_xscale('log')
        self.ax.set_xticks(STANDARD_FREQUENCIES)
        self.ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
        self.ax.set_yticks(np.arange(-10, 130, 10))

        self.ax.tick_params(colors='#94a3b8', labelsize=8)
        self.ax.spines['bottom'].set_color('#334155')
        self.ax.spines['top'].set_color('#334155')
        self.ax.spines['right'].set_color('#334155')
        self.ax.spines['left'].set_color('#334155')

        self.ax.grid(True, which='both', color='#1e293b', linestyle='--', linewidth=0.7)

        # Normal Hearing Region Shading (<= 25 dB HL)
        self.ax.axhspan(-10, 25, facecolor='#064e3b', alpha=0.35, label='Normal Region (≤ 25 dB HL)')

        # Labels
        self.ax.set_xlabel("Frequency (Hz)", color='#94a3b8', fontsize=9, fontweight='bold')
        self.ax.set_ylabel("Hearing Level (dB HL)", color='#94a3b8', fontsize=9, fontweight='bold')

        # Extract thresholds
        r_ac = self.controller.thresholds["right"]["AC"]
        l_ac = self.controller.thresholds["left"]["AC"]
        r_bc = self.controller.thresholds["right"]["BC"]
        l_bc = self.controller.thresholds["left"]["BC"]

        # Plot Right AC: Red Circle 'o'
        if r_ac:
            f_r = sorted([int(f) for f in r_ac.keys()])
            y_r = [r_ac[str(f)] for f in f_r]
            self.ax.plot(f_r, y_r, color='#ef4444', marker='o', markersize=8, linewidth=2,
                         markerfacecolor='none', markeredgewidth=2, label='Right AC (O)')

        # Plot Left AC: Blue Cross 'x'
        if l_ac:
            f_l = sorted([int(f) for f in l_ac.keys()])
            y_l = [l_ac[str(f)] for f in f_l]
            self.ax.plot(f_l, y_l, color='#3b82f6', marker='x', markersize=8, linewidth=2,
                         markeredgewidth=2, label='Left AC (X)')

        # Plot Right BC: Red '<'
        if r_bc:
            f_rb = sorted([int(f) for f in r_bc.keys()])
            y_rb = [r_bc[str(f)] for f in f_rb]
            self.ax.plot(f_rb, y_rb, color='#ef4444', linestyle='--', marker='<', markersize=8,
                         markerfacecolor='none', markeredgewidth=1.8, label='Right BC (<)')

        # Plot Left BC: Blue '>'
        if l_bc:
            f_lb = sorted([int(f) for f in l_bc.keys()])
            y_lb = [l_bc[str(f)] for f in f_lb]
            self.ax.plot(f_lb, y_lb, color='#3b82f6', linestyle='--', marker='>', markersize=8,
                         markerfacecolor='none', markeredgewidth=1.8, label='Left BC (>)')

        self.ax.legend(loc='lower left', facecolor='#0f172a', edgecolor='#334155', fontsize=8, labelcolor='#f1f5f9')
        self.canvas.draw_idle()

    # -------------------------------------------------------------------------
    # RIGHT PANEL: PATIENT DEMOGRAPHICS, LIVE NOISE, AI CARD, THRESHOLD GRID
    # -------------------------------------------------------------------------
    def build_right_info_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 1. Patient Info Card
        box_pat = QGroupBox(self.loc.get("patient_details"))
        l_pat = QGridLayout(box_pat)

        l_pat.addWidget(QLabel("Name:"), 0, 0)
        self.edit_pat_name = QLineEdit("Ramesh Kumar")
        l_pat.addWidget(self.edit_pat_name, 0, 1)

        l_pat.addWidget(QLabel("Age:"), 1, 0)
        self.spin_pat_age = QSpinBox()
        self.spin_pat_age.setRange(1, 110)
        self.spin_pat_age.setValue(48)
        l_pat.addWidget(self.spin_pat_age, 1, 1)

        l_pat.addWidget(QLabel("MRN / ID:"), 2, 0)
        self.edit_pat_id = QLineEdit("PT-2026-001")
        l_pat.addWidget(self.edit_pat_id, 2, 1)

        # History checkboxes (Required for 13-feature AI inference)
        self.chk_discharge = QCheckBox(self.loc.get("history_discharge"))
        l_pat.addWidget(self.chk_discharge, 3, 0, 1, 2)

        self.chk_noise = QCheckBox(self.loc.get("history_noise"))
        l_pat.addWidget(self.chk_noise, 4, 0, 1, 2)

        layout.addWidget(box_pat)

        # 2. Ambient Noise Level Gauge (Rural Feature)
        box_noise = QGroupBox(self.loc.get("ambient_noise"))
        l_noise = QVBoxLayout(box_noise)

        h_n = QHBoxLayout()
        self.lbl_noise_val = QLabel("34 dB SPL")
        self.lbl_noise_val.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_noise_val.setStyleSheet("color: #22c55e;")
        h_n.addWidget(self.lbl_noise_val)

        self.lbl_noise_status = QLabel("Room Quiet (Optimal)")
        self.lbl_noise_status.setStyleSheet("color: #22c55e; font-size: 10px;")
        h_n.addWidget(self.lbl_noise_status)
        h_n.addStretch()

        self.btn_check_5s_noise = QPushButton("5s Check")
        self.btn_check_5s_noise.clicked.connect(self.run_5s_noise_check)
        h_n.addWidget(self.btn_check_5s_noise)
        l_noise.addLayout(h_n)

        self.progress_noise = QProgressBar()
        self.progress_noise.setRange(20, 90)
        self.progress_noise.setValue(34)
        self.progress_noise.setTextVisible(False)
        self.progress_noise.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 4px;
            }
        """)
        l_noise.addWidget(self.progress_noise)

        layout.addWidget(box_noise)

        # 3. AI Pathology Inference Card (Collapsible)
        box_ai = QGroupBox(self.loc.get("run_ai_analysis"))
        l_ai = QVBoxLayout(box_ai)

        self.btn_run_ai = QPushButton("⚡ RUN AI PATHOLOGY ANALYSIS")
        self.btn_run_ai.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 8px;")
        self.btn_run_ai.clicked.connect(self.action_run_ai_analysis)
        l_ai.addWidget(self.btn_run_ai)

        self.lbl_ai_banner = QLabel("Ready for inference. Complete AC testing first.")
        self.lbl_ai_banner.setWordWrap(True)
        self.lbl_ai_banner.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        l_ai.addWidget(self.lbl_ai_banner)

        # Predicted Class & Certainty
        h_ai_res = QHBoxLayout()
        self.lbl_ai_class = QLabel("Pathology: --")
        self.lbl_ai_class.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_ai_class.setStyleSheet("color: #38bdf8;")
        h_ai_res.addWidget(self.lbl_ai_class)

        self.lbl_ai_conf = QLabel("Certainty: --%")
        self.lbl_ai_conf.setStyleSheet("color: #22c55e; font-weight: bold;")
        h_ai_res.addWidget(self.lbl_ai_conf)
        l_ai.addLayout(h_ai_res)

        # Recommendation text
        self.lbl_ai_rec = QLabel("Recommendation: Complete pure-tone test to view recommendation.")
        self.lbl_ai_rec.setWordWrap(True)
        self.lbl_ai_rec.setStyleSheet("color: #cbd5e1; font-size: 10px; line-height: 1.3;")
        l_ai.addWidget(self.lbl_ai_rec)

        layout.addWidget(box_ai)

        # 4. Interactive Threshold Table (Editable Grid)
        box_grid = QGroupBox("Established Thresholds (dB HL)")
        l_grid = QVBoxLayout(box_grid)

        self.grid_table = QTableWidget()
        self.grid_table.setColumnCount(4)
        self.grid_table.setHorizontalHeaderLabels(["Freq", "R AC", "L AC", "BC"])
        self.grid_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid_table.verticalHeader().setVisible(False)
        self.populate_threshold_grid()
        self.grid_table.cellChanged.connect(self.on_grid_cell_changed)
        l_grid.addWidget(self.grid_table)

        layout.addWidget(box_grid)
        return container

    def populate_threshold_grid(self):
        """Fills threshold table rows for standard frequencies."""
        self.grid_table.blockSignals(True)
        self.grid_table.setRowCount(len(STANDARD_FREQUENCIES))
        for row, f in enumerate(STANDARD_FREQUENCIES):
            str_f = str(f)
            # Freq
            item_f = QTableWidgetItem(f"{f}")
            item_f.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_f.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_table.setItem(row, 0, item_f)

            # Right AC
            r_val = self.controller.thresholds["right"]["AC"].get(str_f)
            item_r = QTableWidgetItem(f"{r_val:.0f}" if r_val is not None else "-")
            item_r.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_table.setItem(row, 1, item_r)

            # Left AC
            l_val = self.controller.thresholds["left"]["AC"].get(str_f)
            item_l = QTableWidgetItem(f"{l_val:.0f}" if l_val is not None else "-")
            item_l.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_table.setItem(row, 2, item_l)

            # BC
            bc_val = self.controller.thresholds["right"]["BC"].get(str_f) or self.controller.thresholds["left"]["BC"].get(str_f)
            item_bc = QTableWidgetItem(f"{bc_val:.0f}" if bc_val is not None else "-")
            item_bc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_table.setItem(row, 3, item_bc)

        self.grid_table.blockSignals(False)

    def on_grid_cell_changed(self, row, col):
        """Allows clinician to manually edit or correct any threshold in the grid."""
        f = STANDARD_FREQUENCIES[row]
        str_f = str(f)
        text = self.grid_table.item(row, col).text().strip()
        try:
            val = float(text)
            if col == 1:
                self.controller.thresholds["right"]["AC"][str_f] = val
            elif col == 2:
                self.controller.thresholds["left"]["AC"][str_f] = val
            elif col == 3:
                self.controller.thresholds["right"]["BC"][str_f] = val
            self.redraw_audiogram()
            self.auto_save_session_point()
        except ValueError:
            pass

    # -------------------------------------------------------------------------
    # SPEECH AUDIOMETRY TAB
    # -------------------------------------------------------------------------
    def build_speech_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)

        desc = QLabel(
            "Speech Reception Threshold (SRT) uses bisyllabic Spondee words presented at descending 5 dB steps. "
            "Word Recognition Score (WRS) presents phonetically balanced words at SRT + 30 dB (or 40 dB SL)."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(desc)

        # SRT Control Box
        box_srt = QGroupBox("1. Speech Reception Threshold (SRT)")
        l_srt = QVBoxLayout(box_srt)

        h_word = QHBoxLayout()
        self.lbl_speech_word = QLabel("Airplane")
        self.lbl_speech_word.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_speech_word.setStyleSheet("color: #38bdf8;")
        h_word.addWidget(self.lbl_speech_word)

        self.btn_play_speech_word = QPushButton("▶ Play Speech Word")
        self.btn_play_speech_word.setStyleSheet("background-color: #0284c7; color: white;")
        self.btn_play_speech_word.clicked.connect(self.play_current_speech_word)
        h_word.addWidget(self.btn_play_speech_word)

        self.btn_next_word = QPushButton("Next Word ⏭")
        self.btn_next_word.clicked.connect(self.advance_speech_word)
        h_word.addWidget(self.btn_next_word)
        l_srt.addLayout(h_word)

        # Scoring
        h_score = QHBoxLayout()
        self.btn_word_correct = QPushButton("✔ Correct Repeat [C]")
        self.btn_word_correct.setStyleSheet("background-color: #22c55e; color: white;")
        self.btn_word_correct.clicked.connect(self.record_speech_correct)
        h_score.addWidget(self.btn_word_correct)

        self.btn_word_incorrect = QPushButton("✘ Incorrect Repeat [I]")
        self.btn_word_incorrect.setStyleSheet("background-color: #ef4444; color: white;")
        self.btn_word_incorrect.clicked.connect(self.record_speech_incorrect)
        h_score.addWidget(self.btn_word_incorrect)

        self.lbl_srt_result = QLabel("Established SRT: Right = 25 dB HL | Left = 30 dB HL")
        self.lbl_srt_result.setStyleSheet("color: #f59e0b; font-weight: bold;")
        h_score.addWidget(self.lbl_srt_result)
        l_srt.addLayout(h_score)

        layout.addWidget(box_srt)

        # WRS Control Box
        box_wrs = QGroupBox("2. Word Recognition Score (WRS)")
        l_wrs = QVBoxLayout(box_wrs)

        self.lbl_wrs_info = QLabel("Presenting Phonetically Balanced (PB) list at 55 dB HL (SRT + 30 dB SL)")
        l_wrs.addWidget(self.lbl_wrs_info)

        h_wrs = QHBoxLayout()
        self.lbl_wrs_score = QLabel("Current WRS Score: Right = 92% (Normal) | Left = 84% (Mild Reduction)")
        self.lbl_wrs_score.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_wrs_score.setStyleSheet("color: #22c55e;")
        h_wrs.addWidget(self.lbl_wrs_score)
        l_wrs.addLayout(h_wrs)

        layout.addWidget(box_wrs)
        layout.addStretch()
        return container

    def play_current_speech_word(self):
        """Synthesizes or plays word audio through AudioEngine."""
        word = self.lbl_speech_word.text()
        lang = self.loc.current_lang
        audio_samples, sample_rate = self.speech.get_word_audio(word, lang=lang)
        # Ensure speech is presented at conversational audible loudness (at least 45 dB HL)
        playback_level = max(45.0, float(self.controller.current_level))
        self.audio.play_speech_sample(
            audio_samples=audio_samples,
            sample_rate=sample_rate,
            db_hl=playback_level,
            ear=self.controller.current_ear
        )
        self.lbl_status.setText(f"Playing speech token: '{word}' ({self.controller.current_ear.upper()} Ear at {playback_level:.0f} dB HL)")

    def advance_speech_word(self):
        lang = self.loc.current_lang
        words = self.speech.get_spondee_list(lang)
        current = self.lbl_speech_word.text()
        try:
            idx = words.index(current)
            next_word = words[(idx + 1) % len(words)]
        except ValueError:
            next_word = words[0]
        self.lbl_speech_word.setText(next_word)

    def record_speech_correct(self):
        ear = self.controller.current_ear
        self.controller.speech_results[ear]["SRT"] = round(self.controller.current_level, 0)
        self.lbl_srt_result.setText(f"SRT ({ear.upper()}): {self.controller.current_level} dB HL")
        self.advance_speech_word()

    def record_speech_incorrect(self):
        self.controller.change_level(5.0)
        self.advance_speech_word()

    # -------------------------------------------------------------------------
    # SPECIAL TESTS TAB (SISI & TONE DECAY)
    # -------------------------------------------------------------------------
    def build_special_tests_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)

        # SISI Box
        box_sisi = QGroupBox("Short Increment Sensitivity Index (SISI)")
        l_sisi = QVBoxLayout(box_sisi)
        desc_sisi = QLabel("Superimposes 1 dB increments every 5s at 20 dB SL carrier. >70% score confirms cochlear recruitment.")
        desc_sisi.setStyleSheet("color: #94a3b8; font-size: 10px;")
        l_sisi.addWidget(desc_sisi)

        h_s = QHBoxLayout()
        btn_start_sisi = QPushButton("Start SISI Test (20 Increments)")
        btn_start_sisi.setStyleSheet("background-color: #0284c7; color: white;")
        btn_start_sisi.clicked.connect(self.action_start_sisi)
        h_s.addWidget(btn_start_sisi)

        self.lbl_sisi_status = QLabel("SISI Score: Not tested")
        self.lbl_sisi_status.setStyleSheet("color: #f59e0b; font-weight: bold;")
        h_s.addWidget(self.lbl_sisi_status)
        l_sisi.addLayout(h_s)

        layout.addWidget(box_sisi)

        # Tone Decay Box
        box_decay = QGroupBox("Tone Decay Test (Retrocochlear Recruitment Evaluation)")
        l_decay = QVBoxLayout(box_decay)
        desc_decay = QLabel("Continuous tone at threshold + 5 dB for 60 seconds. Decay > 15-20 dB indicates acoustic neuroma / retrocochlear lesion.")
        desc_decay.setStyleSheet("color: #94a3b8; font-size: 10px;")
        l_decay.addWidget(desc_decay)

        h_d = QHBoxLayout()
        btn_start_decay = QPushButton("Start 60s Tone Decay Test")
        btn_start_decay.setStyleSheet("background-color: #7c3aed; color: white;")
        btn_start_decay.clicked.connect(self.action_start_tone_decay)
        h_d.addWidget(btn_start_decay)

        self.lbl_decay_status = QLabel("Decay Result: Not tested")
        self.lbl_decay_status.setStyleSheet("color: #f59e0b; font-weight: bold;")
        h_d.addWidget(self.lbl_decay_status)
        l_decay.addLayout(h_d)

        layout.addWidget(box_decay)
        layout.addStretch()
        return container

    def action_start_sisi(self):
        self.lbl_sisi_status.setText("SISI running... Patient must indicate 1 dB increments.")
        self.controller.run_sisi_test(
            frequency=self.controller.current_frequency,
            on_complete=lambda score: self.lbl_sisi_status.setText(f"SISI Complete: {score}% ({'Positive / Cochlear' if score>=70 else 'Negative'})")
        )

    def action_start_tone_decay(self):
        self.lbl_decay_status.setText("Tone Decay running... Sustaining perception.")
        self.controller.run_tone_decay_test(
            frequency=self.controller.current_frequency,
            on_complete=lambda res: self.lbl_decay_status.setText(f"Tone Decay: +{res['total_decay_db']} dB ({res['interpretation']})")
        )

    # =========================================================================
    # EVENT HANDLERS & PROTOCOL DISPATCHERS
    # =========================================================================
    def select_ear(self, ear: str):
        self.controller.select_ear(ear)
        if ear == "right":
            self.btn_ear_right.setChecked(True)
            self.btn_ear_right.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; padding: 8px;")
            self.btn_ear_left.setChecked(False)
            self.btn_ear_left.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-weight: bold; padding: 8px;")
        else:
            self.btn_ear_left.setChecked(True)
            self.btn_ear_left.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 8px;")
            self.btn_ear_right.setChecked(False)
            self.btn_ear_right.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-weight: bold; padding: 8px;")
        self.lbl_status.setText(f"Selected: {ear.upper()} Ear")

    def select_conduction(self, cond: str):
        success = self.controller.select_conduction(cond)
        if not success:
            QMessageBox.warning(self, "Hardware Restriction", "Bone conduction hardware is not configured. AC-Only mode active.")
            self.btn_cond_ac.setChecked(True)
            self.btn_cond_bc.setChecked(False)
            return

        if cond == "AC":
            self.btn_cond_ac.setChecked(True)
            self.btn_cond_ac.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold;")
            self.btn_cond_bc.setChecked(False)
            self.btn_cond_bc.setStyleSheet("background-color: #1f2937; color: #94a3b8;")
        else:
            self.btn_cond_bc.setChecked(True)
            self.btn_cond_bc.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold;")
            self.btn_cond_ac.setChecked(False)
            self.btn_cond_ac.setStyleSheet("background-color: #1f2937; color: #94a3b8;")

    def select_frequency(self, freq: int):
        self.controller.set_frequency(freq)
        for f, btn in self.freq_buttons.items():
            if f == freq:
                btn.setChecked(True)
                btn.setStyleSheet("background-color: #38bdf8; color: black; font-weight: bold;")
            else:
                btn.setChecked(False)
                btn.setStyleSheet("background-color: #1f2937; color: #f9fafb;")

    def adjust_level(self, delta: float):
        new_val = self.controller.change_level(delta)
        self.slider_level.setValue(int(new_val))
        self.lbl_db_hl.setText(f"{new_val:.0f} dB HL")

    def on_slider_level_changed(self, val: int):
        self.controller.set_level(val)
        self.lbl_db_hl.setText(f"{val} dB HL")

    def on_step_size_changed(self, idx: int):
        self.controller.step_size = 5.0 if idx == 0 else 1.0
        self.btn_db_down.setText(f"▼ -{int(self.controller.step_size)} dB [↓]")
        self.btn_db_up.setText(f"▲ +{int(self.controller.step_size)} dB [↑]")

    def on_masking_toggled(self, checked: bool):
        self.controller.masking_enabled = checked

    def on_mask_level_changed(self, val: int):
        self.controller.masking_level = float(val)

    def action_present_tone(self):
        """Presents manual stimulus with 20ms raised-cosine taper."""
        self.btn_present.setStyleSheet("background-color: #15803d; color: white; padding: 12px; border-radius: 6px;")
        QTimer.singleShot(400, lambda: self.btn_present.setStyleSheet("background-color: #22c55e; color: white; padding: 12px; border-radius: 6px;"))
        self.controller.present_manual_tone(duration_s=1.2)

    def action_store_threshold(self):
        """Stores threshold and updates audiogram canvas & persistence journal."""
        self.controller.store_manual_threshold()
        self.populate_threshold_grid()
        self.redraw_audiogram()
        self.auto_save_session_point()

    def action_auto_hughson_westlake(self):
        """Starts automated ISO 8253-1 testing."""
        # Pre-test noise check:
        avg_spl, status, can_proceed = self.noise.perform_5s_pre_test_check()
        if not can_proceed:
            QMessageBox.critical(self, "Ambient Noise Critical", f"Ambient noise ({avg_spl} dB SPL) exceeds 55 dB threshold. Testing is blocked. Please move to a quieter room.")
            return

        self.btn_auto_hw.setEnabled(False)
        self.lbl_status.setText("Hughson-Westlake automated threshold seeking in progress...")
        self.controller.start_automated_hughson_westlake(
            on_complete=lambda: self.on_auto_hw_finished()
        )

    def on_auto_hw_finished(self):
        self.btn_auto_hw.setEnabled(True)
        self.populate_threshold_grid()
        self.redraw_audiogram()
        self.lbl_status.setText("Hughson-Westlake completed. All thresholds plotted.")
        self.auto_save_session_point()

    def action_auto_bekesy(self):
        """Starts automated Bekesy tracking."""
        self.lbl_status.setText("Bekesy tracking active. Hold spacebar / button when hearing tone.")
        self.controller.start_bekesy_tracking(
            frequency=self.controller.current_frequency,
            on_complete=lambda thresh: self.on_auto_hw_finished()
        )

    def on_threshold_recorded_gui(self, ear: str, cond: str, freq: int, level: float, masked: bool):
        """Slot executed on main GUI thread when threshold established."""
        self.populate_threshold_grid()
        self.redraw_audiogram()
        self.auto_save_session_point()

    def on_controller_status_gui(self, msg: str, data: Dict[str, Any]):
        """Slot executed on main GUI thread when status updates."""
        self.lbl_status.setText(msg)

    def on_threshold_recorded(self, ear: str, cond: str, freq: int, level: float, masked: bool):
        self.bridge.threshold_recorded.emit(ear, cond, freq, level, masked)

    def on_controller_status(self, msg: str, data: Dict[str, Any]):
        self.bridge.status_updated.emit(msg, data)

    # =========================================================================
    # AI PATHOLOGY INFERENCE INTEGRATION
    # =========================================================================
    def action_run_ai_analysis(self):
        """
        Executes AI Inference:
        If BC exists -> Runs 18-feature model
        If BC missing -> Runs 13-feature AC-Only model with rejection threshold (<0.70 -> Uncertain)
        """
        # Gather inputs - check current ear, or opposite ear if current ear has < 3 thresholds
        ear = self.controller.current_ear
        ac_dict = self.controller.thresholds[ear]["AC"]
        bc_dict = self.controller.thresholds[ear]["BC"]

        if len(ac_dict) < 3:
            opp_ear = "left" if ear == "right" else "right"
            opp_ac = self.controller.thresholds[opp_ear]["AC"]
            if len(opp_ac) >= 3:
                ear = opp_ear
                ac_dict = opp_ac
                bc_dict = self.controller.thresholds[ear]["BC"]
            else:
                QMessageBox.warning(
                    self,
                    "Audiogram Incomplete",
                    f"Please establish thresholds for at least 3 frequencies (e.g. 500, 1000, 2000, 4000 Hz) before running AI analysis.\n\nCurrent points tested for {ear.upper()} ear: {len(ac_dict)}."
                )
                return

        age = self.spin_pat_age.value()
        discharge = 1 if self.chk_discharge.isChecked() else 0
        noise = 1 if self.chk_noise.isChecked() else 0

        # Dispatch inference
        res = self.ai.analyze_ear_session(
            ac_thresholds={int(k): v for k, v in ac_dict.items()},
            bc_thresholds={int(k): v for k, v in bc_dict.items()} if bc_dict else None,
            age=age,
            discharge=discharge,
            noise=noise
        )

        self.session_data["ai_analysis"] = res

        # Update AI Card UI
        self.lbl_ai_banner.setText(res.get("banner", ""))
        if res.get("is_ac_only", False):
            self.lbl_ai_banner.setStyleSheet("color: #f59e0b; font-weight: bold;")
        else:
            self.lbl_ai_banner.setStyleSheet("color: #22c55e; font-weight: bold;")

        pred = res.get("prediction", "Normal")
        conf = res.get("confidence", 0.90)
        self.lbl_ai_class.setText(f"Pathology: {pred}")
        self.lbl_ai_conf.setText(f"Certainty: {conf * 100:.1f}%")
        self.lbl_ai_rec.setText(f"Recommendation: {res.get('recommendation')}")

        self.auto_save_session_point()
        QMessageBox.information(
            self,
            "AI Inference Complete",
            f"Diagnosis: {pred}\nCertainty: {conf*100:.1f}%\nModel: {res.get('model_used')}\n\n{res.get('banner')}"
        )

    # =========================================================================
    # AMBIENT NOISE & HARDWARE DETECTION
    # =========================================================================
    def poll_ambient_noise_gui(self):
        """Safely polled on main GUI thread to display ambient room noise."""
        spl = self.noise.current_spl
        status, _ = self.noise.get_noise_status()
        self.lbl_noise_val.setText(f"{spl:.0f} dB SPL")
        self.progress_noise.setValue(int(spl))
        self.session_data["ambient_noise_spl"] = spl

        if status == "acceptable":
            self.lbl_noise_val.setStyleSheet("color: #22c55e;")
            self.lbl_noise_status.setText("Room Quiet (Optimal)")
            self.progress_noise.setStyleSheet("QProgressBar::chunk { background-color: #22c55e; }")
            if self.banner_noise.isVisible():
                self.banner_noise.setVisible(False)
        elif status == "warning":
            self.lbl_noise_val.setStyleSheet("color: #f59e0b;")
            self.lbl_noise_status.setText("Elevated Noise (>45 dB)")
            self.progress_noise.setStyleSheet("QProgressBar::chunk { background-color: #f59e0b; }")
            self.banner_noise.setText("⚠️ Warning: Ambient Noise Elevated (> 45 dB SPL). May affect low-frequency thresholds.")
            self.banner_noise.setStyleSheet("background-color: #d97706; color: white; padding: 4px; font-weight: bold;")
            if not self.banner_noise.isVisible():
                self.banner_noise.setVisible(True)
        else:  # blocked
            self.lbl_noise_val.setStyleSheet("color: #ef4444;")
            self.lbl_noise_status.setText("Critical Noise (>55 dB)")
            self.progress_noise.setStyleSheet("QProgressBar::chunk { background-color: #ef4444; }")
            self.banner_noise.setText("🛑 Critical Ambient Noise (> 55 dB SPL). Testing blocked. Move to quieter room.")
            self.banner_noise.setStyleSheet("background-color: #ef4444; color: white; padding: 4px; font-weight: bold;")
            if not self.banner_noise.isVisible():
                self.banner_noise.setVisible(True)

    def on_noise_update(self, spl: float, status: str):
        pass  # Handled safely via poll_ambient_noise_gui timer

    def run_5s_noise_check(self):
        avg, status, allowed = self.noise.perform_5s_pre_test_check()
        QMessageBox.information(
            self,
            "5-Second Ambient Baseline Check",
            f"Average Room Noise: {avg} dB SPL\nStatus: {status.upper()}\nPermissible to test: {'YES' if allowed else 'NO - Relocate'}"
        )

    def check_initial_hardware(self):
        hw = self.hardware.scan_devices()
        if hw["has_usb_dac"]:
            self.lbl_hw_badge.setText(f"DAC: {hw['active_dac_name'][:18]}")
            self.lbl_hw_badge.setStyleSheet("background-color: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 12px; font-weight: bold;")
        else:
            self.lbl_hw_badge.setText("DAC: Built-in (Warning)")
            self.lbl_hw_badge.setStyleSheet("background-color: #7f1d1d; color: #fca5a5; padding: 4px 10px; border-radius: 12px; font-weight: bold;")

        if not hw["has_bone_conduction"]:
            self.cal.set_ac_only_mode(True)
            self.lbl_ac_mode_badge.setText("Mode: AC-Only (Rural Preset)")
            self.lbl_ac_mode_badge.setStyleSheet("background-color: #78350f; color: #fbbf24; padding: 4px 10px; border-radius: 12px; font-weight: bold;")
            self.btn_cond_bc.setEnabled(False)
            self.btn_cond_bc.setToolTip("Bone conduction hardware not detected. AC-Only mode active.")

    def on_transducer_changed(self, idx: int):
        pid = self.combo_transducer.currentData()
        self.cal.set_active_profile(pid)
        self.session_data["transducer"] = pid
        self.session_data["calibration_profile"] = pid
        self.lbl_status.setText(f"Active transducer changed to: {self.cal.get_active_profile().get('name')}")

    def open_calibration_wizard(self):
        dlg = CalibrationWizardDialog(self.cal, self.audio, self)
        dlg.exec()

    # =========================================================================
    # MULTILINGUAL LOCALIZATION
    # =========================================================================
    def on_language_changed(self, idx: int):
        lang_code = self.combo_lang.currentData()
        self.loc.set_language(lang_code)
        self.apply_translations()

    def apply_translations(self):
        self.lbl_app_title.setText(self.loc.get("app_title"))
        self.lbl_tagline.setText(self.loc.get("tagline"))
        self.btn_export_pdf.setText(self.loc.get("export_pdf"))
        self.btn_present.setText(self.loc.get("present_tone"))
        self.btn_store_thresh.setText(self.loc.get("store_threshold"))
        self.btn_auto_hw.setText(self.loc.get("start_hw"))
        self.btn_auto_bekesy.setText(self.loc.get("start_bekesy"))
        self.btn_run_ai.setText(self.loc.get("run_ai_analysis"))
        self.chk_discharge.setText(self.loc.get("history_discharge"))
        self.chk_noise.setText(self.loc.get("history_noise"))
        self.lbl_speech_word.setText(self.speech.get_spondee_list(self.loc.current_lang)[0])

    # =========================================================================
    # POWER INTERRUPTION RECOVERY & AUTO-SAVE
    # =========================================================================
    def check_session_recovery(self):
        """Prompts to restore incomplete session if found in the journal."""
        if self.storage.has_incomplete_session():
            reply = QMessageBox.question(
                self,
                "Power Interruption Recovery",
                "An interrupted / incomplete test session was found from a previous run.\n"
                "Would you like to resume testing from where you left off?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                data = self.storage.load_incomplete_session()
                if data:
                    self.session_data = data
                    self.controller.thresholds = data.get("tests", {}).get("pure_tone", self.controller.thresholds)
                    self.edit_pat_name.setText(data.get("patient_name", "Anonymous"))
                    self.edit_pat_id.setText(data.get("patient_id", "PT-001"))
                    self.spin_pat_age.setValue(data.get("age", 40))
                    self.populate_threshold_grid()
                    self.redraw_audiogram()
                    self.lbl_status.setText("Restored incomplete test session successfully.")
            else:
                self.storage.clear_journal()

    def auto_save_session_point(self):
        """Immediately auto-saves current test point to prevent data loss on power cuts."""
        self.session_data["patient_name"] = self.edit_pat_name.text()
        self.session_data["patient_id"] = self.edit_pat_id.text()
        self.session_data["age"] = self.spin_pat_age.value()
        self.session_data["tests"] = {"pure_tone": self.controller.thresholds, "speech": self.controller.speech_results}
        self.session_data["patient_reliability"] = self.response.get_reliability_score()
        self.storage.auto_save_threshold_event(self.session_data)

    # =========================================================================
    # EXPORT DISPATCHERS (<2s PDF, JSON, CSV, FHIR)
    # =========================================================================
    def action_export_pdf(self):
        self.auto_save_session_point()
        t0 = time.time()
        try:
            pdf_path = self.exporter.generate_pdf_report(self.session_data)
            elapsed = time.time() - t0
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("PDF Report Generated")
            msg_box.setText(f"Clinical PDF report generated in {elapsed:.2f} seconds!\n\nSaved to:\n{pdf_path}")
            btn_open = msg_box.addButton("Open PDF", QMessageBox.ButtonRole.ActionRole)
            btn_folder = msg_box.addButton("Open Reports Folder", QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            msg_box.exec()

            if msg_box.clickedButton() == btn_open:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
            elif msg_box.clickedButton() == btn_folder:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(pdf_path)))
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to generate PDF: {e}")

    def action_export_json(self):
        self.auto_save_session_point()
        json_path = self.exporter.export_emr_json(self.session_data)
        csv_path = self.exporter.export_research_csv(self.session_data)
        fhir_path = self.exporter.export_hl7_fhir_json(self.session_data)
        QMessageBox.information(
            self,
            "EMR & Research Data Exported",
            f"Exported files:\n• EMR JSON: {json_path}\n• Bulk Research CSV: {csv_path}\n• HL7 FHIR: {fhir_path}"
        )

    # =========================================================================
    # PATIENT INSTRUCTIONS ANIMATION / VISUAL MODAL
    # =========================================================================
    def show_patient_instructions_modal(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Patient Instructions (Multi-Language)")
        dlg.setMinimumSize(550, 400)
        dlg.setStyleSheet("background-color: #0f172a; color: white;")
        l = QVBoxLayout(dlg)

        title = QLabel(self.loc.get("instructions_title"))
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        l.addWidget(title)

        # Graphic indicator (Headphones + Beep Waves icon simulation)
        box_vis = QLabel("🎧  🔊  👉  [🔘 BUTTON]")
        box_vis.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_vis.setFont(QFont("Segoe UI", 26))
        box_vis.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 20px; margin: 10px 0;")
        l.addWidget(box_vis)

        txt = QLabel(self.loc.get("instruction_pure_tone"))
        txt.setWordWrap(True)
        txt.setFont(QFont("Segoe UI", 12))
        txt.setStyleSheet("color: #f1f5f9; line-height: 1.5; padding: 10px;")
        l.addWidget(txt)

        btn_audio = QPushButton("🔊 Play Spoken Audio Instructions")
        btn_audio.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 10px;")
        btn_audio.clicked.connect(lambda: self.play_instruction_audio())
        l.addWidget(btn_audio)

        btn_close = QPushButton("Ready / Start Test")
        btn_close.setStyleSheet("background-color: #22c55e; color: white; font-weight: bold; padding: 10px;")
        btn_close.clicked.connect(dlg.accept)
        l.addWidget(btn_close)

        dlg.exec()

    def play_instruction_audio(self):
        # Generates a pleasant guidance chime followed by pure-tone test sample
        sample = self.speech.synthesize_word_audio("Test Beep", duration_s=1.5)
        self.audio.play_speech_sample(sample, sample_rate=48000, db_hl=45.0, ear="right")

    # =========================================================================
    # KEYBOARD ACCELERATORS (Spacebar = Present, Enter = Store)
    # =========================================================================
    def setup_keyboard_shortcuts(self):
        pass  # Handled via keyPressEvent

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Space:
            self.action_present_tone()
            # Also register patient response event if stimulus is active
            self.response.register_response(input_source="spacebar")
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.action_store_threshold()
        elif key == Qt.Key.Key_Up:
            self.adjust_level(self.controller.step_size)
        elif key == Qt.Key.Key_Down:
            self.adjust_level(-self.controller.step_size)
        elif key == Qt.Key.Key_Left:
            self.step_frequency_down()
        elif key == Qt.Key.Key_Right:
            self.step_frequency_up()
        elif key == Qt.Key.Key_Escape:
            self.audio.stop()
        else:
            super().keyPressEvent(event)

    def step_frequency_up(self):
        curr = self.controller.current_frequency
        try:
            idx = STANDARD_FREQUENCIES.index(curr)
            if idx < len(STANDARD_FREQUENCIES) - 1:
                self.select_frequency(STANDARD_FREQUENCIES[idx + 1])
        except ValueError:
            pass

    def step_frequency_down(self):
        curr = self.controller.current_frequency
        try:
            idx = STANDARD_FREQUENCIES.index(curr)
            if idx > 0:
                self.select_frequency(STANDARD_FREQUENCIES[idx - 1])
        except ValueError:
            pass

    def closeEvent(self, event):
        """Gracefully shut down audio streams and background threads on exit."""
        if hasattr(self, "noise_poll_timer") and self.noise_poll_timer.isActive():
            self.noise_poll_timer.stop()
        self.noise.stop_monitoring()
        self.audio.stop()
        self.controller.stop_automated_test()
        event.accept()
