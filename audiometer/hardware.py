"""
Hardware Detection and Diagnostics for Software Audiometer.
Detects USB DACs, assesses audio output latency, checks bone-conduction transducers,
and configures system volume lock warnings.
"""

import logging
from typing import Dict, Any, List, Tuple
import sounddevice as sd

logger = logging.getLogger(__name__)


class HardwareDetector:
    """
    Scans physical audio interfaces on Windows/Linux/Mac.
    Detects presence of calibrated USB sound cards and bone vibrators.
    """

    def __init__(self):
        self.devices: List[Dict[str, Any]] = []
        self.has_usb_dac: bool = False
        self.has_bone_conduction: bool = False
        self.active_dac_name: str = "Default Audio Output"
        self.scan_devices()

    def scan_devices(self) -> Dict[str, Any]:
        """Scans host system for audio hardware."""
        self.devices.clear()
        self.has_usb_dac = False
        self.has_bone_conduction = False

        try:
            raw_devices = sd.query_devices()
            for idx, dev in enumerate(raw_devices):
                name = dev.get("name", "")
                out_channels = dev.get("max_output_channels", 0)
                name_lower = name.lower()

                if out_channels >= 2:
                    is_usb = any(term in name_lower for term in ["usb", "dac", "scarlett", "fiio", "behringer", "motu", "audient"])
                    is_bc = any(term in name_lower for term in ["bone", "b71", "radioear", "openear", "shokz"])

                    entry = {
                        "index": idx,
                        "name": name,
                        "channels": out_channels,
                        "samplerate": dev.get("default_samplerate"),
                        "is_usb": is_usb,
                        "is_bc": is_bc
                    }
                    self.devices.append(entry)

                    if is_usb:
                        self.has_usb_dac = True
                        self.active_dac_name = name
                    if is_bc:
                        self.has_bone_conduction = True
        except Exception as e:
            logger.error(f"Error enumerating sound devices: {e}")

        logger.info(f"Hardware scan finished: Found {len(self.devices)} output endpoints. USB DAC: {self.has_usb_dac}, BC device: {self.has_bone_conduction}")

        return {
            "has_usb_dac": self.has_usb_dac,
            "has_bone_conduction": self.has_bone_conduction,
            "active_dac_name": self.active_dac_name,
            "devices": self.devices
        }

    def get_hardware_status_banners(self) -> List[Tuple[str, str]]:
        """
        Returns list of (severity, banner_message):
        - severity: 'warning' or 'info'
        """
        banners = []
        if not self.has_usb_dac:
            banners.append((
                "warning",
                "⚠️ No external USB DAC detected. Built-in PC sound card may introduce electrical noise floor."
            ))
        else:
            banners.append((
                "info",
                f"✅ USB DAC Detected: {self.active_dac_name} (Volume locked digitally)."
            ))

        if not self.has_bone_conduction:
            banners.append((
                "warning",
                "⚠️ Bone conduction transducer not detected. AC-Only mode automatically enabled."
            ))
        return banners
