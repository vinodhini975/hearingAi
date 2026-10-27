"""
Test Controller and Clinical Protocols for Diagnostic Audiometer.
Implements:
1. Pure Tone Audiometry (Manual, ISO 8253-1 Hughson-Westlake, Bekesy tracking)
2. Clinical Masking Rules (Interaural Attenuation, Narrowband Plateau)
3. Speech Audiometry (SRT, WRS)
4. Special Diagnostic Tests (SISI, Tone Decay)
"""

import time
import random
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple, Callable

from audiometer.audio_engine import AudioEngine
from audiometer.patient_response import PatientResponseManager
from audiometer.calibration import CalibrationManager

logger = logging.getLogger(__name__)

STANDARD_AC_FREQS = [250, 500, 1000, 2000, 4000, 8000]
EXTENDED_AC_FREQS = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
STANDARD_BC_FREQS = [250, 500, 750, 1000, 1500, 2000, 3000, 4000]

# Interaural attenuation constants (dB)
IA_CIRCUMAURAL = 40.0
IA_SUPRA_AURAL = 40.0
IA_INSERT = 50.0
IA_BONE = 0.0


class TestController:
    """
    Coordinates stimulus presentation, automated Hughson-Westlake threshold seeking,
    Bekesy tracking, masking decisions, and diagnostic protocols.
    """

    def __init__(
        self,
        audio_engine: AudioEngine,
        response_mgr: PatientResponseManager,
        cal_mgr: CalibrationManager
    ):
        self.audio = audio_engine
        self.response = response_mgr
        self.cal = cal_mgr

        # Current testing state
        self.current_ear: str = "right"  # "right" or "left"
        self.current_conduction: str = "AC"  # "AC" or "BC"
        self.current_frequency: int = 1000
        self.current_level: float = 30.0  # dB HL
        self.step_size: float = 5.0  # 5 dB manual/clinical, 1 dB research

        # Masking state
        self.masking_enabled: bool = False
        self.masking_level: float = -10.0

        # Session Thresholds storage:
        # tests["pure_tone"]["right"]["AC"][freq] = threshold
        self.thresholds: Dict[str, Dict[str, Dict[str, float]]] = {
            "right": {"AC": {}, "BC": {}, "AC_masked": {}, "BC_masked": {}},
            "left": {"AC": {}, "BC": {}, "AC_masked": {}, "BC_masked": {}}
        }

        # Speech audiometry results
        self.speech_results: Dict[str, Dict[str, Any]] = {
            "right": {"SRT": None, "WRS": None},
            "left": {"SRT": None, "WRS": None}
        }

        # Special tests results
        self.sisi_results: Dict[str, Any] = {}
        self.tone_decay_results: Dict[str, Any] = {}

        # Automated testing thread & state
        self._auto_thread: Optional[threading.Thread] = None
        self._stop_auto = threading.Event()
        self.is_auto_running: bool = False

        # Status callbacks for GUI updates
        self._on_status_update: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self._on_threshold_found: Optional[Callable[[str, str, int, float, bool], None]] = None

    def set_callbacks(
        self,
        on_status: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_threshold: Optional[Callable[[str, str, int, float, bool], None]] = None
    ) -> None:
        self._on_status_update = on_status
        self._on_threshold_found = on_threshold

    def _notify_status(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        if self._on_status_update:
            data = {
                "ear": self.current_ear,
                "conduction": self.current_conduction,
                "frequency": self.current_frequency,
                "level": self.current_level,
                "message": message
            }
            if extra:
                data.update(extra)
            self._on_status_update(message, data)

    def select_ear(self, ear: str) -> None:
        """Switches active ear ('right' or 'left')."""
        self.current_ear = ear.lower()
        self._notify_status(f"Ear selected: {self.current_ear.upper()}")

    def select_conduction(self, conduction: str) -> bool:
        """
        Switches between Air Conduction ('AC') and Bone Conduction ('BC').
        Checks AC-only mode constraints.
        """
        cond = conduction.upper()
        if cond == "BC":
            if self.cal.is_ac_only() or not self.cal.is_bone_conduction_available():
                logger.warning("Bone conduction requested but system is in AC-Only mode!")
                self._notify_status("BC Unavailable: In AC-Only Mode")
                return False
        self.current_conduction = cond
        self._notify_status(f"Conduction selected: {self.current_conduction}")
        return True

    def set_frequency(self, frequency: int) -> None:
        """Sets stimulus frequency in Hz."""
        self.current_frequency = int(frequency)
        self._notify_status(f"Frequency: {self.current_frequency} Hz")

    def set_level(self, level_db_hl: float) -> None:
        """Sets stimulus intensity in dB HL."""
        max_output = self.cal.get_max_output(self.current_frequency)
        clamped = max(-10.0, min(float(level_db_hl), max_output))
        self.current_level = clamped
        self._notify_status(f"Intensity: {self.current_level} dB HL")

    def change_level(self, delta: float) -> float:
        """Increments or decrements level by delta dB."""
        self.set_level(self.current_level + delta)
        return self.current_level

    def present_manual_tone(self, duration_s: float = 1.2) -> Tuple[float, float]:
        """Plays manual stimulus at current ear, frequency, and dB HL."""
        masking_db = self.masking_level if self.masking_enabled else None
        self.response.start_stimulus(is_catch_trial=False)
        test_amp, mask_amp = self.audio.present_tone_db_hl(
            frequency=self.current_frequency,
            db_hl=self.current_level,
            ear=self.current_ear,
            duration_s=duration_s,
            masking_db_hl=masking_db,
            blocking=False
        )
        self._notify_status(f"Presenting {self.current_frequency}Hz at {self.current_level} dB HL ({self.current_ear.upper()} {self.current_conduction})")
        return test_amp, mask_amp

    def store_manual_threshold(self, level: Optional[float] = None) -> None:
        """Saves current level as established threshold."""
        thresh = self.current_level if level is None else level
        mode_key = self.current_conduction
        if self.masking_enabled:
            mode_key = f"{self.current_conduction}_masked"

        str_freq = str(self.current_frequency)
        self.thresholds[self.current_ear][mode_key][str_freq] = round(thresh, 1)

        if self._on_threshold_found:
            self._on_threshold_found(
                self.current_ear,
                self.current_conduction,
                self.current_frequency,
                thresh,
                self.masking_enabled
            )
        self._notify_status(f"Stored threshold: {self.current_frequency}Hz = {thresh} dB HL")

    # =========================================================================
    # ISO 8253-1 AUTOMATED HUGHSON-WESTLAKE THRESHOLD SEEKING
    # =========================================================================
    def run_hughson_westlake_single_frequency(
        self,
        frequency: int,
        start_level: float = 30.0,
        max_presentations: int = 12
    ) -> Optional[float]:
        """
        Executes ISO 8253-1 Hughson-Westlake algorithm for one frequency:
        - Descend 10 dB on response
        - Ascend 5 dB on no-response
        - Threshold criterion: 2 of 3 (or 2 of 4) ascending responses at same level,
          provided there was non-response at (level - 5 dB).
        - Random inter-stimulus interval: 1.5 - 3.0 seconds
        - Response window: 2.5 seconds
        - Max presentations <= 12
        """
        level = start_level
        ascending_responses: Dict[float, int] = {}
        ascending_trials: Dict[float, int] = {}
        non_responses: set = set()
        presentation_count = 0
        last_direction = "descending"

        # Check masking need
        masking_db = self.calculate_masking_need(frequency, level)

        while presentation_count < max_presentations and not self._stop_auto.is_set():
            presentation_count += 1

            # Randomized inter-stimulus interval to prevent rhythm anticipation
            isi = random.uniform(1.5, 3.0)
            self._notify_status(
                f"HW {frequency}Hz: Waiting ISI ({isi:.1f}s)...",
                {"phase": "isi", "presentation": presentation_count}
            )
            time.sleep(isi)
            if self._stop_auto.is_set():
                break

            # 10% chance of catch trial (silent presentation to monitor reliability)
            if random.random() < 0.12 and presentation_count > 2:
                self.response.start_stimulus(is_catch_trial=True)
                time.sleep(2.0)
                self.response.end_presentation_window()
                continue

            # Present tone
            self.current_level = level
            self.response.start_stimulus(is_catch_trial=False)
            self._notify_status(
                f"HW {frequency}Hz: Presenting at {level} dB HL (Trial {presentation_count}/{max_presentations})",
                {"phase": last_direction, "level": level, "presentation": presentation_count}
            )

            # 1.2s tone
            self.audio.present_tone_db_hl(
                frequency=frequency,
                db_hl=level,
                ear=self.current_ear,
                duration_s=1.2,
                masking_db_hl=masking_db,
                blocking=False
            )

            # Wait for response window (up to 2.5s)
            start_wait = time.time()
            heard = False
            while time.time() - start_wait < 2.5:
                if self._stop_auto.is_set():
                    break
                time.sleep(0.05)
                # Check if patient registered hit
                if self.response.is_stimulus_active and len(self.response.response_log) > 0:
                    last_event = self.response.response_log[-1]
                    if last_event.get("is_hit", False) and last_event.get("timestamp", 0) >= start_wait:
                        heard = True
                        break

            self.response.end_presentation_window()

            # Rule transition:
            if heard:
                if last_direction == "ascending":
                    ascending_responses[level] = ascending_responses.get(level, 0) + 1
                    ascending_trials[level] = ascending_trials.get(level, 0) + 1

                    # Check ISO 8253-1 criterion: 2/3 responses at same level AND non-response 5dB below
                    if ascending_responses[level] >= 2:
                        below_level = level - 5.0
                        if below_level in non_responses or level <= -10.0 or ascending_responses[level] >= 3:
                            logger.info(f"ISO 8253-1 threshold met at {frequency}Hz = {level} dB HL ({presentation_count} presentations)")
                            return level

                # Descend 10 dB on positive response
                level = max(-10.0, level - 10.0)
                last_direction = "descending"
            else:
                non_responses.add(level)
                if last_direction == "ascending":
                    ascending_trials[level] = ascending_trials.get(level, 0) + 1

                # Ascend 5 dB on no response
                max_out = self.cal.get_max_output(frequency)
                level = min(max_out, level + 5.0)
                last_direction = "ascending"

        # If presentation limit reached, take the level with highest response ratio
        best_level = None
        best_count = 0
        for l_val, c_val in ascending_responses.items():
            if c_val > best_count:
                best_count = c_val
                best_level = l_val

        return best_level

    def start_automated_hughson_westlake(
        self,
        frequencies: Optional[List[int]] = None,
        on_complete: Optional[Callable[[], None]] = None
    ) -> None:
        """Starts background automated Hughson-Westlake test across selected frequencies."""
        if self.is_auto_running:
            return

        freq_list = frequencies or (STANDARD_AC_FREQS if self.current_conduction == "AC" else STANDARD_BC_FREQS)
        self.is_auto_running = True
        self._stop_auto.clear()

        def _worker():
            try:
                # Audiological standard order: start at 1000 Hz, go high, then recheck 1000 Hz, then lows
                ordered = [1000] + [f for f in freq_list if f > 1000] + [f for f in freq_list if f < 1000]
                # Remove duplicates while preserving order
                seen = set()
                run_freqs = [f for f in ordered if not (f in seen or seen.add(f))]

                for f in run_freqs:
                    if self._stop_auto.is_set():
                        break
                    self.current_frequency = f
                    thresh = self.run_hughson_westlake_single_frequency(f)
                    if thresh is not None:
                        str_f = str(f)
                        mode_key = self.current_conduction
                        self.thresholds[self.current_ear][mode_key][str_f] = round(thresh, 1)
                        if self._on_threshold_found:
                            self._on_threshold_found(
                                self.current_ear,
                                self.current_conduction,
                                f,
                                thresh,
                                self.masking_enabled
                            )
                self._notify_status("Automated Hughson-Westlake test complete.")
            except Exception as e:
                logger.error(f"Hughson-Westlake worker error: {e}")
            finally:
                self.is_auto_running = False
                if on_complete:
                    on_complete()

        self._auto_thread = threading.Thread(target=_worker, daemon=True)
        self._auto_thread.start()

    def stop_automated_test(self) -> None:
        """Interrupts automated Hughson-Westlake or Bekesy testing."""
        self._stop_auto.set()
        self.audio.stop()
        self.is_auto_running = False
        self._notify_status("Automated test stopped by operator.")

    # =========================================================================
    # BEKESY AUTOMATED TRACKING AUDIOMETRY
    # =========================================================================
    def start_bekesy_tracking(
        self,
        frequency: int,
        duration_s: float = 30.0,
        rate_db_per_sec: float = 2.5,
        on_complete: Optional[Callable[[float], None]] = None
    ) -> None:
        """
        Implements Bekesy tracking algorithm:
        - Continuous pulsed tone at `frequency`
        - Patient presses button when hearing tone -> level attenuates at rate_db_per_sec
        - Patient releases button when inaudible -> level increases at rate_db_per_sec
        - Tracks directional reversal peaks (midpoints) to calculate true threshold
        """
        if self.is_auto_running:
            return

        self.is_auto_running = True
        self._stop_auto.clear()
        self.current_frequency = frequency

        def _bekesy_worker():
            level = 40.0
            reversals = []
            direction = -1  # -1 = descending (patient hearing), +1 = ascending (patient not hearing)
            start_time = time.time()
            step_interval = 0.4
            delta_step = rate_db_per_sec * step_interval

            last_level = level
            try:
                while time.time() - start_time < duration_s and not self._stop_auto.is_set():
                    # Check button state:
                    is_pressed = self.response.is_stimulus_active
                    new_direction = -1 if is_pressed else 1

                    if new_direction != direction:
                        # Reversal detected!
                        reversals.append(level)
                        direction = new_direction

                    level += direction * delta_step
                    max_out = self.cal.get_max_output(frequency)
                    level = max(-10.0, min(max_out, level))
                    self.current_level = level

                    # Pulse 300ms tone
                    self.audio.present_tone_db_hl(
                        frequency=frequency,
                        db_hl=level,
                        ear=self.current_ear,
                        duration_s=step_interval * 0.8,
                        blocking=False
                    )
                    self._notify_status(
                        f"Bekesy {frequency}Hz: Tracking at {level:.1f} dB HL ({'Hearing' if is_pressed else 'Searching'})",
                        {"phase": "tracking", "level": round(level, 1), "reversals": len(reversals)}
                    )
                    time.sleep(step_interval)

                # Compute threshold as mean of midpoints (discard first 2 reversals for stabilization)
                valid_reversals = reversals[2:] if len(reversals) >= 4 else reversals
                if valid_reversals:
                    thresh = round(float(sum(valid_reversals) / len(valid_reversals)), 1)
                else:
                    thresh = round(level, 1)

                str_f = str(frequency)
                self.thresholds[self.current_ear][self.current_conduction][str_f] = thresh
                if self._on_threshold_found:
                    self._on_threshold_found(
                        self.current_ear,
                        self.current_conduction,
                        frequency,
                        thresh,
                        False
                    )
                self._notify_status(f"Bekesy complete: {frequency}Hz threshold = {thresh} dB HL")
                if on_complete:
                    on_complete(thresh)
            except Exception as e:
                logger.error(f"Bekesy tracking error: {e}")
            finally:
                self.is_auto_running = False

        self._auto_thread = threading.Thread(target=_bekesy_worker, daemon=True)
        self._auto_thread.start()

    # =========================================================================
    # CLINICAL MASKING DECISION ENGINE
    # =========================================================================
    def calculate_masking_need(self, frequency: int, test_level: float) -> Optional[float]:
        """
        Rule per clinical requirement:
        When testing AC in one ear, check if AC threshold minus interaural attenuation
        (40 dB for supra/circumaural, 50 dB for insert, 0 dB for BC) is better than or equal
        to threshold in non-test ear:
            AC_test - IA >= AC_threshold_non_test
        If yes:
            masking_level = AC_threshold_non_test - IA + 10 dB
        """
        non_test_ear = "left" if self.current_ear == "right" else "right"
        str_f = str(frequency)
        non_test_ac = self.thresholds[non_test_ear]["AC"].get(str_f, 10.0)

        # Transducer interaural attenuation
        prof = self.cal.get_active_profile()
        coupling = prof.get("coupling", "circumaural")
        if self.current_conduction == "BC":
            ia = IA_BONE  # 0 dB
        elif coupling == "insert":
            ia = IA_INSERT  # 50 dB
        else:
            ia = IA_CIRCUMAURAL  # 40 dB

        # Crossover rule:
        crossover_level = test_level - ia
        if crossover_level >= non_test_ac:
            needed_mask = round(non_test_ac - ia + 10.0, 1)
            # Minimum effective masking noise floor
            needed_mask = max(15.0, needed_mask)
            self.masking_enabled = True
            self.masking_level = needed_mask
            logger.info(f"Cross-hearing detected at {frequency}Hz! Presenting {needed_mask} dB NBN masking to {non_test_ear.upper()} ear.")
            return needed_mask
        else:
            self.masking_enabled = False
            self.masking_level = -10.0
            return None

    # =========================================================================
    # SPECIAL DIAGNOSTIC TESTS: SISI & TONE DECAY
    # =========================================================================
    def run_sisi_test(
        self,
        frequency: int,
        carrier_sl_db: float = 20.0,
        total_increments: int = 20,
        on_complete: Optional[Callable[[float], None]] = None
    ) -> None:
        """
        SISI (Short Increment Sensitivity Index):
        Carrier tone at (Threshold + 20 dB SL).
        Every 5 seconds, adds a 1 dB increment for 200 ms.
        Score = (increments detected / 20) * 100%.
        """
        if self.is_auto_running:
            return

        str_f = str(frequency)
        thresh = self.thresholds[self.current_ear]["AC"].get(str_f, 20.0)
        carrier_level = thresh + carrier_sl_db

        self.is_auto_running = True
        self._stop_auto.clear()

        def _sisi_worker():
            detected = 0
            try:
                for inc_idx in range(1, total_increments + 1):
                    if self._stop_auto.is_set():
                        break

                    # Carrier tone on
                    self.audio.present_tone_db_hl(
                        frequency=frequency,
                        db_hl=carrier_level,
                        ear=self.current_ear,
                        duration_s=4.0,
                        blocking=False
                    )
                    time.sleep(4.0)

                    # 1 dB increment for 200ms
                    self.response.start_stimulus(is_catch_trial=False)
                    self.audio.present_tone_db_hl(
                        frequency=frequency,
                        db_hl=carrier_level + 1.0,
                        ear=self.current_ear,
                        duration_s=0.2,
                        blocking=True
                    )

                    # Check response
                    time.sleep(1.0)
                    if self.response.end_presentation_window():
                        detected += 1
                        logger.info(f"SISI increment {inc_idx}/{total_increments} detected.")

                    self._notify_status(f"SISI {frequency}Hz: Trial {inc_idx}/{total_increments} (Detected: {detected})")

                sisi_score = round((detected / float(total_increments)) * 100.0, 1)
                self.sisi_results[f"{self.current_ear}_{frequency}"] = {
                    "score": sisi_score,
                    "interpretation": "Positive / Cochlear (Recruitment)" if sisi_score >= 70.0 else "Negative / Normal or Neural"
                }
                self._notify_status(f"SISI Complete: {sisi_score}% ({self.sisi_results[f'{self.current_ear}_{frequency}']['interpretation']})")
                if on_complete:
                    on_complete(sisi_score)
            finally:
                self.is_auto_running = False

        self._auto_thread = threading.Thread(target=_sisi_worker, daemon=True)
        self._auto_thread.start()

    def run_tone_decay_test(
        self,
        frequency: int,
        duration_s: float = 60.0,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """
        Tone Decay Test (Carhart):
        Presents continuous tone at threshold + 5 dB.
        Checks if patient sustains perception for 60 continuous seconds.
        Decay > 15-20 dB indicates retrocochlear lesion.
        """
        if self.is_auto_running:
            return

        str_f = str(frequency)
        base_thresh = self.thresholds[self.current_ear]["AC"].get(str_f, 20.0)
        level = base_thresh + 5.0

        self.is_auto_running = True
        self._stop_auto.clear()

        def _decay_worker():
            total_decay_db = 0.0
            start_t = time.time()
            try:
                self.audio.present_tone_db_hl(
                    frequency=frequency,
                    db_hl=level,
                    ear=self.current_ear,
                    duration_s=duration_s + 5.0,
                    blocking=False
                )

                while time.time() - start_t < duration_s and not self._stop_auto.is_set():
                    time.sleep(0.5)
                    # If patient releases button (auditory fatigue/decay):
                    if not self.response.is_stimulus_active:
                        level += 5.0
                        total_decay_db += 5.0
                        self._notify_status(f"Tone decay noted! Level increased to {level} dB HL (Total decay: +{total_decay_db} dB)")
                        self.audio.present_tone_db_hl(
                            frequency=frequency,
                            db_hl=level,
                            ear=self.current_ear,
                            duration_s=duration_s + 5.0,
                            blocking=False
                        )
                    else:
                        elapsed = int(time.time() - start_t)
                        self._notify_status(f"Tone Decay {frequency}Hz: Perception sustained ({elapsed}/{int(duration_s)}s)")

                self.audio.stop()
                result = {
                    "frequency": frequency,
                    "base_threshold": base_thresh,
                    "total_decay_db": total_decay_db,
                    "interpretation": "Significant Tone Decay / Retrocochlear Warning" if total_decay_db >= 15.0 else "Normal / No Significant Adaptation"
                }
                self.tone_decay_results[f"{self.current_ear}_{frequency}"] = result
                self._notify_status(f"Tone Decay Finished: +{total_decay_db} dB ({result['interpretation']})")
                if on_complete:
                    on_complete(result)
            finally:
                self.is_auto_running = False

        self._auto_thread = threading.Thread(target=_decay_worker, daemon=True)
        self._auto_thread.start()

    # =========================================================================
    # PURE TONE AVERAGE (PTA) CALCULATION
    # =========================================================================
    def calculate_pta(self, ear: str, conduction: str = "AC") -> Optional[float]:
        """
        Auto-calculates standard 4-frequency PTA:
        PTA = (500 + 1000 + 2000 + 4000) / 4 dB HL
        """
        ear_dict = self.thresholds.get(ear.lower(), {}).get(conduction, {})
        freqs = ["500", "1000", "2000", "4000"]
        vals = [ear_dict[f] for f in freqs if f in ear_dict and ear_dict[f] is not None]

        if len(vals) == 4:
            return round(sum(vals) / 4.0, 1)
        elif len(vals) >= 2:
            return round(sum(vals) / float(len(vals)), 1)
        return None
