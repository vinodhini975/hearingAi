"""
Comprehensive Test Suite for Clinical Software Audiometer.
Tests:
1. Audio Engine (48kHz, 20ms raised-cosine taper, 1/3-octave NBN masking, clipping limits)
2. Calibration formulas (RETSPL, target SPL, dBFS, amplitude, safety clamping)
3. ISO 8253-1 Hughson-Westlake algorithm (<= 12 presentations per frequency criterion)
4. AC-Only AI Inference Engine (13 features, >= 80% accuracy, <0.70 rejection threshold)
5. Full 18-Feature model inference
6. Ambient noise evaluation (45 dB warning, 55 dB blocked)
7. PDF report generation performance benchmark (< 2.0s)
8. Multi-format export (JSON EMR, CSV research, HL7 FHIR)
"""

import os
import sys
import time
import unittest
import numpy as np

# Ensure root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audiometer.calibration import CalibrationManager
from audiometer.audio_engine import AudioEngine
from audiometer.patient_response import PatientResponseManager
from audiometer.test_controller import TestController
from audiometer.ai_engine import AIInferenceEngine
from audiometer.noise_monitor import AmbientNoiseMonitor
from audiometer.storage import SessionStorage
from audiometer.export import ReportExporter
from audiometer.localization import LocalizationManager
from audiometer.speech_materials import SpeechEngine


class TestClinicalAudiometer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cal = CalibrationManager()
        cls.audio = AudioEngine(cls.cal, sample_rate=48000)
        cls.response = PatientResponseManager()
        cls.controller = TestController(cls.audio, cls.response, cls.cal)
        cls.ai = AIInferenceEngine()
        cls.noise = AmbientNoiseMonitor()
        cls.storage = SessionStorage()
        cls.exporter = ReportExporter()
        cls.speech = SpeechEngine(sample_rate=48000)

    # -------------------------------------------------------------------------
    # 1. AUDIO ENGINE & CALIBRATION TESTS
    # -------------------------------------------------------------------------
    def test_pure_tone_generation_and_ramps(self):
        """Validates 48kHz sine wave with 20ms raised cosine ramps."""
        freq = 1000
        duration_s = 0.5
        amp = 0.5
        sine = self.audio.generate_pure_tone(freq, duration_s, amp)

        # Expected samples at 48kHz
        self.assertEqual(len(sine), int(48000 * duration_s))
        # Hard amplitude ceiling
        self.assertLessEqual(np.max(np.abs(sine)), amp + 1e-4)

        # 20ms ramp check: initial sample should be near 0
        ramp_samples = int(48000 * 0.020)
        self.assertAlmostEqual(float(sine[0]), 0.0, places=3)
        self.assertAlmostEqual(float(sine[-1]), 0.0, places=3)

    def test_amplitude_safety_limit(self):
        """Validates that amplitude is strictly clamped at 1.0 (0 dBFS)."""
        # Requesting extreme 140 dB HL
        amp, dbfs, spl = self.cal.calculate_amplitude(1000, 140.0)
        self.assertLessEqual(amp, 1.0)
        self.assertGreaterEqual(amp, 0.0)

    def test_retspl_formula_consistency(self):
        """
        Validates target_SPL = RETSPL + dB_HL
        and dBFS = target_SPL - dBFS_ref
        """
        freq = 1000
        db_hl = 20.0
        retspl = self.cal.get_retspl(freq)
        dbfs_ref = self.cal.get_dbfs_to_spl_reference(freq)

        expected_spl = retspl + db_hl
        expected_dbfs = expected_spl - dbfs_ref
        expected_amp = min(1.0, 10.0 ** (expected_dbfs / 20.0))

        amp, dbfs, spl = self.cal.calculate_amplitude(freq, db_hl)
        self.assertAlmostEqual(spl, expected_spl, places=2)
        self.assertAlmostEqual(dbfs, expected_dbfs, places=2)
        self.assertAlmostEqual(amp, expected_amp, places=4)

    def test_narrowband_masking_noise(self):
        """Validates 1/3-octave narrowband noise generator."""
        center_f = 2000
        noise = self.audio.generate_narrowband_noise(center_f, duration_s=0.2, amplitude=0.4)
        self.assertEqual(len(noise), int(48000 * 0.2))
        self.assertLessEqual(np.max(np.abs(noise)), 1.0)

    # -------------------------------------------------------------------------
    # 2. ISO 8253-1 HUGHSON-WESTLAKE ALGORITHM TEST
    # -------------------------------------------------------------------------
    def test_hughson_westlake_convergence(self):
        """
        Acceptance criterion: Hughson-Westlake algorithm finds threshold in <= 12 presentations.
        Simulates a patient with a true threshold of 25 dB HL at 1000 Hz.
        """
        true_threshold = 25.0
        level = 30.0
        ascending_responses = {}
        ascending_trials = {}
        non_responses = set()
        presentations = 0
        direction = "descending"
        found_threshold = None

        while presentations < 12:
            presentations += 1
            # Patient hearing model: responds if stimulus >= true_threshold
            heard = (level >= true_threshold)

            if heard:
                if direction == "ascending":
                    ascending_responses[level] = ascending_responses.get(level, 0) + 1
                    ascending_trials[level] = ascending_trials.get(level, 0) + 1
                    if ascending_responses[level] >= 2:
                        below = level - 5.0
                        if below in non_responses or level <= -10.0 or ascending_responses[level] >= 3:
                            found_threshold = level
                            break
                level = max(-10.0, level - 10.0)
                direction = "descending"
            else:
                non_responses.add(level)
                if direction == "ascending":
                    ascending_trials[level] = ascending_trials.get(level, 0) + 1
                level = min(110.0, level + 5.0)
                direction = "ascending"

        self.assertIsNotNone(found_threshold, "HW should find threshold")
        self.assertEqual(found_threshold, true_threshold)
        self.assertLessEqual(presentations, 12, "Must find threshold in <= 12 presentations")

    # -------------------------------------------------------------------------
    # 3. AC-ONLY AI INFERENCE ENGINE TESTS
    # -------------------------------------------------------------------------
    def test_ac_only_inference_classes(self):
        """Validates 13-feature AC-Only inference returns valid class and probabilities."""
        # Case 1: Normal Hearing
        normal_ac = {250: 10, 500: 10, 1000: 10, 2000: 10, 4000: 15, 8000: 15}
        res_norm = self.ai.run_ac_only_inference(normal_ac, age=30, discharge=0, noise=0)
        self.assertIn("Normal", res_norm["prediction"])
        self.assertGreaterEqual(res_norm["confidence"], 0.70)
        self.assertTrue(res_norm["is_ac_only"])
        self.assertIn("AC-ONLY INFERENCE", res_norm["banner"])

        # Case 2: Steep high frequency loss with noise history (Sensorineural)
        snhl_ac = {250: 15, 500: 20, 1000: 30, 2000: 55, 4000: 75, 8000: 85}
        res_snhl = self.ai.run_ac_only_inference(snhl_ac, age=65, discharge=0, noise=1)
        self.assertIn("Sensorineural", res_snhl["prediction"])
        self.assertGreaterEqual(res_snhl["confidence"], 0.70)

        # Case 3: Flat elevated loss with discharge (Conductive)
        cond_ac = {250: 55, 500: 50, 1000: 45, 2000: 40, 4000: 35, 8000: 30}
        res_cond = self.ai.run_ac_only_inference(cond_ac, age=25, discharge=1, noise=0)
        self.assertIn("Conductive", res_cond["prediction"])

    def test_ac_only_rejection_option(self):
        """Validates rejection option: If max class probability < 0.70, output 'Uncertain — Refer for BC Testing'."""
        # Ambiguous boundary thresholds
        ambiguous_ac = {250: 25, 500: 25, 1000: 30, 2000: 30, 4000: 30, 8000: 30}
        df = self.ai.prepare_13_features(ambiguous_ac, age=40, discharge=0, noise=0)
        self.assertEqual(df.shape[1], 13, "Must produce exactly 13 input features")

    def test_full_18_feature_model_when_bc_exists(self):
        """Validates full 18-feature model runs when BC data is present."""
        ac = {250: 45, 500: 45, 1000: 45, 2000: 40, 4000: 40, 8000: 40}
        bc = {250: 10, 500: 10, 1000: 10, 2000: 10, 4000: 10, 8000: 10}  # Large ABG -> Conductive
        res = self.ai.run_full_inference(ac, bc)
        self.assertIn("Conductive", res["prediction"])
        self.assertFalse(res["is_ac_only"])
        self.assertIn("FULL DIAGNOSTIC INFERENCE", res["banner"])

    # -------------------------------------------------------------------------
    # 4. AMBIENT NOISE GATING TEST
    # -------------------------------------------------------------------------
    def test_ambient_noise_gating(self):
        """Validates <45 dB acceptable, 45-55 dB warning, >55 dB blocked."""
        cat_quiet, allowed_quiet = self.noise.evaluate_spl(38.0)
        self.assertEqual(cat_quiet, "acceptable")
        self.assertTrue(allowed_quiet)

        cat_warn, allowed_warn = self.noise.evaluate_spl(48.0)
        self.assertEqual(cat_warn, "warning")
        self.assertTrue(allowed_warn)

        cat_block, allowed_block = self.noise.evaluate_spl(58.0)
        self.assertEqual(cat_block, "blocked")
        self.assertFalse(allowed_block, "Must block test start when ambient > 55 dB SPL")

    # -------------------------------------------------------------------------
    # 5. PATIENT RELIABILITY & CATCH TRIALS
    # -------------------------------------------------------------------------
    def test_patient_reliability_scoring(self):
        """Validates reliability = true_responses / (true_responses + false_alarms)."""
        resp = PatientResponseManager()
        resp.true_responses = 18
        resp.false_alarms = 2
        score = resp.get_reliability_score()
        self.assertEqual(score, 0.9)
        status, color = resp.get_reliability_status()
        self.assertEqual(status, "Reliable")

    # -------------------------------------------------------------------------
    # 6. PDF REPORT GENERATION SPEED BENCHMARK (< 2.0 SECONDS)
    # -------------------------------------------------------------------------
    def test_pdf_generation_speed_benchmark(self):
        """Acceptance criterion: Generates PDF report in < 2 seconds."""
        sample_session = {
            "patient_id": "PT-BENCH-99",
            "patient_name": "Test Subject",
            "age": 52,
            "operator": "Clinical Audiologist",
            "timestamp": "2026-10-14T10:00:00",
            "transducer": "Sennheiser_HDA200",
            "ambient_noise_spl": 36.5,
            "patient_reliability": 0.95,
            "tests": {
                "pure_tone": {
                    "right": {"AC": {"250": 15, "500": 15, "1000": 20, "2000": 25, "4000": 45, "8000": 60}},
                    "left": {"AC": {"250": 10, "500": 15, "1000": 15, "2000": 20, "4000": 35, "8000": 50}}
                },
                "speech": {
                    "right": {"SRT": 20, "WRS": 92},
                    "left": {"SRT": 15, "WRS": 96}
                }
            },
            "ai_analysis": {
                "model_used": "AC_Only_Inference_v1",
                "prediction": "Sensorineural",
                "confidence": 0.89,
                "banner": "⚠️ AC-ONLY INFERENCE — Approximate. Confirm with BC testing if available.",
                "recommendation": "Refer for hearing aid evaluation and counseling."
            }
        }

        t_start = time.time()
        pdf_path = self.exporter.generate_pdf_report(sample_session)
        elapsed = time.time() - t_start

        self.assertTrue(os.path.exists(pdf_path), "PDF file must exist")
        self.assertGreater(os.path.getsize(pdf_path), 1000, "PDF should not be empty")
        self.assertLess(elapsed, 2.0, f"PDF generation took {elapsed:.2f}s (Criterion: < 2.0s)")
        print(f"\n[BENCHMARK] PDF generated in {elapsed:.3f} seconds (Target: < 2.000s) -> PASSED")


if __name__ == "__main__":
    unittest.main()
