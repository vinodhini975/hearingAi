"""
Storage & Power-Resilience Engine for Clinical Audiometer.
Persists every threshold point immediately to disk to prevent data loss from power cuts.
Detects incomplete sessions on startup and allows seamless test resumption.
"""

import os
import json
import sqlite3
import datetime
import logging
from typing import Dict, Any, Optional, List
import numpy as np

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "session_data")
JOURNAL_FILE = os.path.join(DATA_DIR, "active_session_journal.json")
ARCHIVE_DIR = os.path.join(DATA_DIR, "completed_sessions")


class SessionStorage:
    """
    Manages atomic per-threshold writes, power interruption recovery,
    and finalized session JSON archival.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or DATA_DIR
        self.journal_path = os.path.join(self.data_dir, "active_session_journal.json")
        self.archive_dir = os.path.join(self.data_dir, "completed_sessions")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)

    def has_incomplete_session(self) -> bool:
        """Returns True if an unsaved / interrupted session journal exists."""
        if os.path.exists(self.journal_path):
            try:
                with open(self.journal_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Check if session has any thresholds stored
                    tests = data.get("tests", {}).get("pure_tone", {})
                    r_ac = tests.get("right", {}).get("AC", {})
                    l_ac = tests.get("left", {}).get("AC", {})
                    return len(r_ac) > 0 or len(l_ac) > 0
            except Exception:
                return False
        return False

    def load_incomplete_session(self) -> Optional[Dict[str, Any]]:
        """Restores state from the journal file after an unexpected reboot."""
        if not self.has_incomplete_session():
            return None
        try:
            with open(self.journal_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Restored incomplete test session for patient ID: {data.get('patient_id')}")
                return data
        except Exception as e:
            logger.error(f"Failed to read incomplete session journal: {e}")
            return None

    def auto_save_threshold_event(
        self,
        session_data: Dict[str, Any]
    ) -> bool:
        """
        Immediately saves full test state to the journal file.
        Invoked after EVERY individual threshold is established.
        """
        session_data["last_auto_save"] = datetime.datetime.now().isoformat()
        def _json_default(obj):
            if isinstance(obj, (np.floating, np.float32, np.float64)):
                return float(obj)
            if isinstance(obj, (np.integer, np.int32, np.int64)):
                return int(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return str(obj)

        temp_path = self.journal_path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, default=_json_default)
            # Atomic rename on Windows/POSIX
            os.replace(temp_path, self.journal_path)
            logger.debug(f"Auto-saved threshold checkpoint for patient {session_data.get('patient_id')}")
            return True
        except Exception as e:
            logger.error(f"Error auto-saving session journal: {e}")
            return False

    def finalize_and_archive(self, session_data: Dict[str, Any]) -> str:
        """
        Moves completed session into the archive directory and clears the active journal.
        Returns the finalized file path.
        """
        patient_id = session_data.get("patient_id", "anonymous").replace("/", "_").replace("\\", "_")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audiometry_{patient_id}_{timestamp}.json"
        target_path = os.path.join(self.archive_dir, filename)

        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, default=lambda obj: float(obj) if isinstance(obj, (np.floating, np.float32, np.float64)) else int(obj) if isinstance(obj, (np.integer, np.int32, np.int64)) else obj.tolist() if isinstance(obj, np.ndarray) else str(obj))
            logger.info(f"Finalized session archived to: {target_path}")

            # Clear journal
            if os.path.exists(self.journal_path):
                os.remove(self.journal_path)
            return target_path
        except Exception as e:
            logger.error(f"Error archiving completed session: {e}")
            return ""

    def clear_journal(self) -> None:
        """Deletes active journal if operator discards incomplete session."""
        if os.path.exists(self.journal_path):
            try:
                os.remove(self.journal_path)
            except Exception:
                pass
