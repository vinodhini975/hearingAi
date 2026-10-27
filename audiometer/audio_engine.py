"""
Clinical Audio Engine for Hardware-Grade Software Audiometer.
Implements 48kHz audio generation, 20ms raised-cosine ramps,
independent binaural routing, 1/3-octave narrowband masking,
speech playback, and digital amplitude control.
"""

import os
import math
import time
import logging
import threading
from typing import Optional, Tuple, List, Dict, Callable, Any

import numpy as np
from scipy import signal
import sounddevice as sd

from audiometer.calibration import CalibrationManager

logger = logging.getLogger(__name__)

STANDARD_FREQUENCIES = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]


class AudioEngine:
    """
    High-fidelity signal generator and audio playback engine.
    Controls amplitude strictly in the digital domain with selectable USB DAC output.
    """

    def __init__(self, calibration_mgr: CalibrationManager, sample_rate: int = 48000):
        self.cal = calibration_mgr
        self.sample_rate = sample_rate
        self.selected_device_index: Optional[int] = None
        self.stream: Optional[sd.OutputStream] = None
        self.is_playing: bool = False
        self._stop_event = threading.Event()
        self._current_thread: Optional[threading.Thread] = None
        self.ramp_ms: float = 20.0  # 20ms raised-cosine onset/offset ramp

        # Audio device discovery
        self.devices = self.get_output_devices()
        self._select_default_dac()

    def get_output_devices(self) -> List[Dict[str, Any]]:
        """Queries available audio output devices."""
        device_list = []
        try:
            raw_devices = sd.query_devices()
            for idx, dev in enumerate(raw_devices):
                if dev.get("max_output_channels", 0) >= 2:
                    is_usb = "usb" in dev.get("name", "").lower() or "dac" in dev.get("name", "").lower()
                    device_list.append({
                        "index": idx,
                        "name": dev.get("name"),
                        "channels": dev.get("max_output_channels"),
                        "default_samplerate": dev.get("default_samplerate"),
                        "is_usb": is_usb
                    })
        except Exception as e:
            logger.error(f"Error querying audio devices: {e}")
        return device_list

    def _select_default_dac(self) -> None:
        """Selects USB DAC if detected, otherwise system default."""
        for dev in self.devices:
            if dev["is_usb"]:
                self.selected_device_index = dev["index"]
                logger.info(f"Selected USB DAC audio output: {dev['name']} (index {dev['index']})")
                return
        try:
            default_out = sd.default.device[1]
            self.selected_device_index = default_out
            logger.info(f"Selected default audio output index: {default_out}")
        except Exception:
            self.selected_device_index = None

    def set_output_device(self, device_index: int) -> bool:
        """Configures the active audio device."""
        for dev in self.devices:
            if dev["index"] == device_index:
                self.selected_device_index = device_index
                logger.info(f"Output device changed to: {dev['name']}")
                return True
        return False

    def generate_pure_tone(
        self,
        frequency: int,
        duration_s: float,
        amplitude: float
    ) -> np.ndarray:
        """
        Generates pure sine wave with 20ms raised-cosine onset/offset ramps.
        Amplitude must be between 0.0 and 1.0 (strict digital scale).
        """
        amp = min(1.0, max(0.0, float(amplitude)))
        num_samples = int(self.sample_rate * duration_s)
        t = np.arange(num_samples) / self.sample_rate

        # Pure sine generation
        sine_wave = np.sin(2.0 * np.pi * frequency * t) * amp

        # 20ms raised-cosine taper
        ramp_samples = int(self.sample_rate * (self.ramp_ms / 1000.0))
        ramp_samples = min(ramp_samples, num_samples // 2)

        if ramp_samples > 0:
            # Raised cosine: 0.5 * (1 - cos(pi * n / N))
            ramp_up = 0.5 * (1.0 - np.cos(np.pi * np.arange(ramp_samples) / ramp_samples))
            ramp_down = 0.5 * (1.0 + np.cos(np.pi * np.arange(ramp_samples) / ramp_samples))

            sine_wave[:ramp_samples] *= ramp_up
            sine_wave[-ramp_samples:] *= ramp_down

        return sine_wave.astype(np.float32)

    def generate_narrowband_noise(
        self,
        center_frequency: int,
        duration_s: float,
        amplitude: float
    ) -> np.ndarray:
        """
        Generates 1/3-octave narrowband masking noise centered at `center_frequency`.
        Band limits: f_lower = f_c * 2^(-1/6), f_upper = f_c * 2^(1/6).
        """
        amp = min(1.0, max(0.0, float(amplitude)))
        num_samples = int(self.sample_rate * duration_s)

        f_c = float(center_frequency)
        f_lower = f_c * (2.0 ** (-1.0 / 6.0))
        f_upper = f_c * (2.0 ** (1.0 / 6.0))

        # Nyquist frequency bound
        nyq = self.sample_rate / 2.0
        f_lower = max(20.0, min(f_lower, nyq - 100.0))
        f_upper = max(f_lower + 10.0, min(f_upper, nyq - 50.0))

        # Generate Gaussian white noise
        white_noise = np.random.normal(0.0, 1.0, num_samples)

        # 4th-order Butterworth bandpass filter
        b, a = signal.butter(2, [f_lower / nyq, f_upper / nyq], btype="bandpass")
        filtered = signal.lfilter(b, a, white_noise)

        # Normalize RMS power to 1.0, then scale by target amplitude
        rms = np.sqrt(np.mean(filtered ** 2))
        if rms > 1e-6:
            filtered = (filtered / rms) * (amp / np.sqrt(2.0))
        else:
            filtered = filtered * amp

        # Apply 20ms raised-cosine ramps
        ramp_samples = int(self.sample_rate * (self.ramp_ms / 1000.0))
        ramp_samples = min(ramp_samples, num_samples // 2)
        if ramp_samples > 0:
            ramp_up = 0.5 * (1.0 - np.cos(np.pi * np.arange(ramp_samples) / ramp_samples))
            ramp_down = 0.5 * (1.0 + np.cos(np.pi * np.arange(ramp_samples) / ramp_samples))
            filtered[:ramp_samples] *= ramp_up
            filtered[-ramp_samples:] *= ramp_down

        # Hard safety ceiling
        filtered = np.clip(filtered, -1.0, 1.0)
        return filtered.astype(np.float32)

    def prepare_stereo_presentation(
        self,
        frequency: int,
        duration_s: float,
        test_ear: str,  # "right" or "left"
        test_amplitude: float,
        masking_ear: Optional[str] = None,  # "left", "right", or None
        masking_amplitude: float = 0.0
    ) -> np.ndarray:
        """
        Creates a 2-channel stereo buffer (Left = col 0, Right = col 1)
        routing test tone to test ear and masking noise to non-test ear.
        """
        tone = self.generate_pure_tone(frequency, duration_s, test_amplitude)
        num_samples = len(tone)
        stereo_buffer = np.zeros((num_samples, 2), dtype=np.float32)

        # Route pure tone
        if test_ear.lower() == "right":
            stereo_buffer[:, 1] = tone
        else:
            stereo_buffer[:, 0] = tone

        # Route masking noise if active
        if masking_ear and masking_amplitude > 0.0:
            noise = self.generate_narrowband_noise(frequency, duration_s, masking_amplitude)
            min_len = min(num_samples, len(noise))
            if masking_ear.lower() == "right":
                stereo_buffer[:min_len, 1] += noise[:min_len]
            else:
                stereo_buffer[:min_len, 0] += noise[:min_len]

        # Final hard clip protection across both channels
        stereo_buffer = np.clip(stereo_buffer, -1.0, 1.0)
        return stereo_buffer

    def play_buffer(self, stereo_buffer: np.ndarray, blocking: bool = False) -> None:
        """Plays stereo buffer through the selected output device."""
        self.stop()
        self._stop_event.clear()
        self.is_playing = True

        def _play_worker():
            try:
                sd.play(
                    stereo_buffer,
                    samplerate=self.sample_rate,
                    device=self.selected_device_index,
                    blocking=True
                )
            except Exception as e:
                logger.error(f"Playback error: {e}")
            finally:
                self.is_playing = False

        self._current_thread = threading.Thread(target=_play_worker, daemon=True)
        self._current_thread.start()

        if blocking:
            self._current_thread.join()

    def present_tone_db_hl(
        self,
        frequency: int,
        db_hl: float,
        ear: str,
        duration_s: float = 1.5,
        transducer_id: Optional[str] = None,
        masking_db_hl: Optional[float] = None,
        blocking: bool = False
    ) -> Tuple[float, float]:
        """
        High-level presentation helper:
        Computes calibrated digital amplitude for frequency & dB HL,
        and optionally routes masking noise to opposite ear.
        Returns: (test_amplitude, masking_amplitude)
        """
        test_amp, _, _ = self.cal.calculate_amplitude(frequency, db_hl, transducer_id)

        masking_amp = 0.0
        masking_ear = None
        if masking_db_hl is not None and masking_db_hl > -10.0:
            # Masking goes to the opposite ear
            masking_ear = "left" if ear.lower() == "right" else "right"
            # Masking uses circumaural/supra-aural AC calibration for noise reference
            masking_amp, _, _ = self.cal.calculate_amplitude(frequency, masking_db_hl, transducer_id)

        buffer = self.prepare_stereo_presentation(
            frequency=frequency,
            duration_s=duration_s,
            test_ear=ear,
            test_amplitude=test_amp,
            masking_ear=masking_ear,
            masking_amplitude=masking_amp
        )

        self.play_buffer(buffer, blocking=blocking)
        return test_amp, masking_amp

    def stop(self) -> None:
        """Immediately stops any ongoing sound playback."""
        self._stop_event.set()
        try:
            sd.stop()
        except Exception:
            pass
        self.is_playing = False


    def play_speech_sample(
        self,
        audio_samples: np.ndarray,
        sample_rate: int,
        db_hl: float,
        ear: str,
        transducer_id: Optional[str] = None,
        blocking: bool = False
    ) -> float:
        """
        Plays speech audio waveform calibrated to target dB HL at 1000 Hz reference.
        """
        # Speech calibration is referenced to 1000 Hz RETSPL
        speech_amp, _, _ = self.cal.calculate_amplitude(1000, db_hl, transducer_id)

        # Normalize input audio samples to standard speech RMS level, then scale by speech_amp
        samples = audio_samples.astype(np.float32)
        rms = np.sqrt(np.mean(samples ** 2))
        if rms > 1e-5:
            # Scaled to maintain clear audibility and calibrated speech level
            samples = (samples / rms) * (speech_amp * 0.70)
        else:
            samples = samples * speech_amp

        # Prepare stereo
        stereo_buffer = np.zeros((len(samples), 2), dtype=np.float32)
        if ear.lower() == "right":
            stereo_buffer[:, 1] = samples
        else:
            stereo_buffer[:, 0] = samples

        stereo_buffer = np.clip(stereo_buffer, -1.0, 1.0)

        # Resample if sample_rate != self.sample_rate
        if sample_rate != self.sample_rate and len(stereo_buffer) > 0:
            target_len = int(len(stereo_buffer) * (self.sample_rate / sample_rate))
            resampled_l = signal.resample(stereo_buffer[:, 0], target_len)
            resampled_r = signal.resample(stereo_buffer[:, 1], target_len)
            stereo_buffer = np.column_stack([resampled_l, resampled_r]).astype(np.float32)

        self.play_buffer(stereo_buffer, blocking=blocking)
        return speech_amp
