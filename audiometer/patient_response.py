"""
Patient Response System for Clinical Audiometry.
Tracks response latency, catch trials, false alarms, and patient reliability index.
"""

import time
import logging
from typing import List, Dict, Optional, Callable, Any, Tuple

logger = logging.getLogger(__name__)


class PatientResponseManager:
    """
    Handles patient interaction events across keyboard spacebar, mouse click,
    touchscreen taps, and external USB/Bluetooth response pedals.
    Computes reaction times, monitors catch trials, and derives reliability scores.
    """

    def __init__(self, response_window_s: float = 2.5):
        self.response_window_s = response_window_s
        self.tone_start_time: Optional[float] = None
        self.is_stimulus_active: bool = False
        self.is_catch_trial: bool = False  # True during silent catch intervals

        self.true_responses: int = 0
        self.false_alarms: int = 0
        self.catch_trial_total: int = 0
        self.catch_trial_passed: int = 0

        self.response_log: List[Dict[str, Any]] = []
        self._on_valid_response_cb: Optional[Callable[[float], None]] = None
        self._on_false_alarm_cb: Optional[Callable[[], None]] = None

    def start_stimulus(self, is_catch_trial: bool = False) -> None:
        """Called immediately upon tone onset."""
        self.tone_start_time = time.time()
        self.is_stimulus_active = True
        self.is_catch_trial = is_catch_trial
        if is_catch_trial:
            self.catch_trial_total += 1

    def stop_stimulus(self) -> None:
        """Called when tone presentation completes."""
        self.is_stimulus_active = False

    def register_response(self, input_source: str = "spacebar") -> Dict[str, Any]:
        """
        Processes a button press / tap / spacebar press from the patient.
        Determines whether the response was a true hit, response in window, or false alarm.
        """
        now = time.time()
        latency_ms = None
        is_hit = False
        is_false_alarm = False

        if self.tone_start_time is not None:
            elapsed = now - self.tone_start_time
            if 0.1 <= elapsed <= self.response_window_s:
                if self.is_catch_trial:
                    # Patient responded during a silent catch trial!
                    is_false_alarm = True
                    self.false_alarms += 1
                    logger.warning(f"Patient false alarm during catch trial! (Source: {input_source})")
                else:
                    # Valid auditory threshold response
                    is_hit = True
                    latency_ms = round(elapsed * 1000.0, 1)
                    self.true_responses += 1
                    logger.info(f"Valid patient response: latency={latency_ms}ms (Source: {input_source})")
            else:
                # Outside valid response window
                is_false_alarm = True
                self.false_alarms += 1
                logger.warning(f"Patient response outside window ({elapsed:.2f}s). Counted as false alarm.")
        else:
            # Responded during silence
            is_false_alarm = True
            self.false_alarms += 1
            logger.warning("Spontaneous response during silent baseline.")

        event = {
            "timestamp": now,
            "source": input_source,
            "latency_ms": latency_ms,
            "is_hit": is_hit,
            "is_false_alarm": is_false_alarm,
            "is_catch_trial": self.is_catch_trial
        }
        self.response_log.append(event)

        if is_hit and self._on_valid_response_cb and latency_ms is not None:
            self._on_valid_response_cb(latency_ms)
        elif is_false_alarm and self._on_false_alarm_cb:
            self._on_false_alarm_cb()

        return event

    def end_presentation_window(self) -> bool:
        """
        Called when response window has lapsed.
        Returns True if a valid hit occurred in this window.
        """
        self.is_stimulus_active = False
        if self.is_catch_trial and self.response_log:
            last = self.response_log[-1]
            if not last.get("is_false_alarm", False):
                self.catch_trial_passed += 1

        self.tone_start_time = None
        self.is_catch_trial = False

        # Check if last event was a hit
        if self.response_log:
            return self.response_log[-1].get("is_hit", False)
        return False

    def get_reliability_score(self) -> float:
        """
        Calculates patient reliability index:
        reliability = true_responses / (true_responses + false_alarms)
        Returns float between 0.0 and 1.0 (defaults to 1.0 if no responses yet).
        """
        total = self.true_responses + self.false_alarms
        if total == 0:
            return 1.0
        return round(float(self.true_responses) / float(total), 3)

    def get_reliability_status(self) -> Tuple[str, str]:
        """
        Returns (status_label, color_code):
        - >= 0.85: ("Reliable", "#22c55e") [Green]
        - 0.70 - 0.84: ("Questionable", "#eab308") [Amber]
        - < 0.70: ("Unreliable", "#ef4444") [Red]
        """
        score = self.get_reliability_score()
        if score >= 0.85:
            return "Reliable", "#22c55e"
        elif score >= 0.70:
            return "Questionable", "#eab308"
        else:
            return "Unreliable", "#ef4444"

    def reset_session(self) -> None:
        """Resets all metrics for a new patient test."""
        self.tone_start_time = None
        self.is_stimulus_active = False
        self.is_catch_trial = False
        self.true_responses = 0
        self.false_alarms = 0
        self.catch_trial_total = 0
        self.catch_trial_passed = 0
        self.response_log.clear()

    def set_callbacks(
        self,
        on_valid: Optional[Callable[[float], None]] = None,
        on_false_alarm: Optional[Callable[[], None]] = None
    ) -> None:
        self._on_valid_response_cb = on_valid
        self._on_false_alarm_cb = on_false_alarm
