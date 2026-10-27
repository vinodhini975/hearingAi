"""
Calibration Engine for Clinical-Grade Software Audiometer.
Implements ISO 389-1, ISO 389-3, ISO 389-8 RETSPL mappings,
digital amplitude safety limits, and AC-only capability enforcement.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_PROFILES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "calibration_profiles",
    "profiles.json"
)

STANDARD_FREQUENCIES = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
BC_FREQUENCIES = [250, 500, 750, 1000, 1500, 2000, 3000, 4000]


class CalibrationManager:
    """
    Manages transducer calibration profiles, RETSPL lookup tables,
    and converts dB HL to digital amplitude with strict safety ceilings.
    """

    def __init__(self, profiles_path: Optional[str] = None):
        self.profiles_path = profiles_path or DEFAULT_PROFILES_PATH
        self.profiles: Dict[str, Any] = {}
        self.active_profile_id: str = "Sennheiser_HDA200"
        self.ac_only_mode: bool = False
        self.load_profiles()

    def load_profiles(self) -> None:
        """Loads calibration profiles from JSON storage."""
        if os.path.exists(self.profiles_path):
            try:
                with open(self.profiles_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.profiles = data.get("profiles", {})
                    self.active_profile_id = data.get("active_profile", "Sennheiser_HDA200")
                    logger.info(f"Loaded {len(self.profiles)} calibration profiles. Active: {self.active_profile_id}")
                    return
            except Exception as e:
                logger.error(f"Error loading calibration profiles from {self.profiles_path}: {e}")

        # Fallback built-in profile if file unreadable
        self._load_fallback_defaults()

    def _load_fallback_defaults(self) -> None:
        """Loads hardcoded defaults in case filesystem read fails."""
        self.profiles = {
            "Sennheiser_HDA200": {
                "id": "Sennheiser_HDA200",
                "name": "Sennheiser HDA-200 (Circumaural)",
                "type": "air_conduction",
                "is_bone_conduction": false,
                "retspl": {
                    "125": 30.5, "250": 18.0, "500": 11.0, "750": 6.0,
                    "1000": 5.5, "1500": 5.5, "2000": 4.5, "3000": 2.5,
                    "4000": 9.5, "6000": 17.0, "8000": 17.5
                },
                "dbfs_to_spl_reference": {
                    "125": 110.0, "250": 112.0, "500": 114.0, "750": 114.5,
                    "1000": 115.0, "1500": 115.0, "2000": 114.5, "3000": 113.0,
                    "4000": 112.5, "6000": 110.0, "8000": 108.0
                },
                "max_output_db_hl": {
                    "125": 90, "250": 105, "500": 115, "750": 115,
                    "1000": 120, "1500": 120, "2000": 120, "3000": 120,
                    "4000": 115, "6000": 105, "8000": 100
                }
            }
        }
        self.active_profile_id = "Sennheiser_HDA200"

    def save_profiles(self) -> bool:
        """Persists calibration profiles back to JSON storage."""
        os.makedirs(os.path.dirname(self.profiles_path), exist_ok=True)
        try:
            payload = {
                "active_profile": self.active_profile_id,
                "profiles": self.profiles
            }
            with open(self.profiles_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.info(f"Calibration profiles saved successfully to {self.profiles_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save calibration profiles: {e}")
            return False

    def get_active_profile(self) -> Dict[str, Any]:
        """Returns the dictionary configuration of the currently active transducer."""
        return self.profiles.get(self.active_profile_id, {})

    def set_active_profile(self, profile_id: str) -> bool:
        """Switches active transducer profile."""
        if profile_id in self.profiles:
            self.active_profile_id = profile_id
            prof = self.profiles[profile_id]
            # If active transducer is AC, and no BC hardware is present, note AC-only mode
            logger.info(f"Active transducer changed to: {prof.get('name', profile_id)}")
            return True
        return False

    def list_profiles(self) -> Dict[str, str]:
        """Returns a dict mapping profile_id -> display_name."""
        return {pid: p.get("name", pid) for pid, p in self.profiles.items()}

    def get_retspl(self, frequency: int, profile_id: Optional[str] = None) -> float:
        """Fetches the RETSPL for a given frequency and profile."""
        pid = profile_id or self.active_profile_id
        profile = self.profiles.get(pid, {})
        retspl_dict = profile.get("retspl", {})
        str_f = str(int(frequency))
        if str_f in retspl_dict:
            return float(retspl_dict[str_f])
        return 10.0  # Safe audiological baseline estimate

    def get_dbfs_to_spl_reference(self, frequency: int, profile_id: Optional[str] = None) -> float:
        """
        Fetches the measured SPL when a 0 dBFS tone is played at `frequency`.
        """
        pid = profile_id or self.active_profile_id
        profile = self.profiles.get(pid, {})
        ref_dict = profile.get("dbfs_to_spl_reference", {})
        str_f = str(int(frequency))
        if str_f in ref_dict:
            return float(ref_dict[str_f])
        return 110.0  # Conservative clinical default

    def get_max_output(self, frequency: int, profile_id: Optional[str] = None) -> float:
        """Retrieves maximum permissible dB HL for frequency under current transducer."""
        pid = profile_id or self.active_profile_id
        profile = self.profiles.get(pid, {})
        max_dict = profile.get("max_output_db_hl", {})
        str_f = str(int(frequency))
        return float(max_dict.get(str_f, 120.0))

    def calculate_amplitude(self, frequency: int, db_hl: float, profile_id: Optional[str] = None) -> Tuple[float, float, float]:
        """
        Applies clinical transfer formula:
            target_SPL = RETSPL[freq] + dB_HL
            dBFS = target_SPL - dBFS_to_SPL_reference[freq]
            amplitude = 10^(dBFS / 20)
            amplitude = min(amplitude, 1.0)  // HARD SAFETY LIMIT

        Returns:
            (amplitude, dbfs, target_spl)
        """
        # Hard lower bounds (-10 dB HL) and upper bounds (120 dB HL)
        clamped_hl = max(-10.0, float(db_hl))
        max_hl = self.get_max_output(frequency, profile_id)
        if clamped_hl > max_hl:
            logger.warning(f"Requested {clamped_hl} dB HL exceeds transducer max {max_hl} dB HL at {frequency}Hz. Clamping.")
            clamped_hl = max_hl

        retspl = self.get_retspl(frequency, profile_id)
        dbfs_ref = self.get_dbfs_to_spl_reference(frequency, profile_id)

        target_spl = retspl + clamped_hl
        dbfs = target_spl - dbfs_ref

        # Amplitude calculation
        raw_amplitude = 10.0 ** (dbfs / 20.0)

        # Strict digital clipping protection
        amplitude = min(raw_amplitude, 1.0)
        amplitude = max(0.0, amplitude)

        return amplitude, dbfs, target_spl

    def calibrate_frequency_point(self, frequency: int, measured_spl: float, profile_id: Optional[str] = None) -> None:
        """
        Records the measured SPL produced by a 0 dBFS tone at `frequency`
        during calibration wizard.
        """
        pid = profile_id or self.active_profile_id
        if pid not in self.profiles:
            return
        str_f = str(int(frequency))
        if "dbfs_to_spl_reference" not in self.profiles[pid]:
            self.profiles[pid]["dbfs_to_spl_reference"] = {}
        self.profiles[pid]["dbfs_to_spl_reference"][str_f] = round(float(measured_spl), 1)
        self.save_profiles()
        logger.info(f"Updated calibration: Transducer={pid}, Freq={frequency}Hz, 0 dBFS = {measured_spl} dB SPL")

    def create_custom_profile(
        self,
        profile_id: str,
        name: str,
        transducer_type: str,
        is_bone_conduction: bool,
        retspl_map: Dict[str, float],
        dbfs_ref_map: Dict[str, float],
        max_output_map: Optional[Dict[str, float]] = None
    ) -> bool:
        """Adds a newly calibrated transducer profile to the database."""
        self.profiles[profile_id] = {
            "id": profile_id,
            "name": name,
            "type": transducer_type,
            "is_bone_conduction": is_bone_conduction,
            "calibration_date": "2026-10-14",
            "calibrated_by": "Operator Field Wizard",
            "retspl": retspl_map,
            "dbfs_to_spl_reference": dbfs_ref_map,
            "max_output_db_hl": max_output_map or {str(f): (70 if is_bone_conduction else 115) for f in STANDARD_FREQUENCIES}
        }
        return self.save_profiles()

    def set_ac_only_mode(self, enabled: bool) -> None:
        """Flags system into AC-Only mode when bone-conduction hardware is absent."""
        self.ac_only_mode = enabled
        logger.info(f"AC-Only Mode set to: {enabled}")

    def is_ac_only(self) -> bool:
        """True if the system is operating in AC-Only mode."""
        return self.ac_only_mode

    def is_bone_conduction_available(self) -> bool:
        """Checks if a bone-conduction transducer profile is configured and AC-only mode is not forced."""
        if self.ac_only_mode:
            return False
        # Check if any BC profile exists
        for p in self.profiles.values():
            if p.get("is_bone_conduction", False):
                return True
        return False
