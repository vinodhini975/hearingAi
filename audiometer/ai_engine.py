"""
AI Pathology Inference Engine for Software Audiometer.
Supports:
1. 13-feature AC-Only Machine Learning inference with rejection threshold (<0.70 -> Uncertain)
2. 18-feature Full Diagnostic Model (when Bone Conduction is available)
3. Expert clinical rule-based deterministic fallback layer
4. Multi-language audiological recommendations
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import joblib

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
AC_MODEL_PATH = os.path.join(MODELS_DIR, "ac_only_model.pkl")
AC_ENCODER_PATH = os.path.join(MODELS_DIR, "ac_label_encoder.pkl")
FULL_MODEL_PATH = os.path.join(MODELS_DIR, "hearing_pathology_model.pkl")
FULL_ENCODER_PATH = os.path.join(MODELS_DIR, "label_encoder.pkl")

FREQUENCIES_6 = [250, 500, 1000, 2000, 4000, 8000]

RECOMMENDATIONS = {
    "Normal": "Hearing sensitivity within normal clinical limits (≤25 dB HL). Routine follow-up in 12-24 months.",
    "Conductive": "Suggests middle/outer ear mechanical attenuation. Refer to ENT specialist for otoscopy and tympanometry.",
    "Sensorineural": "Suggests inner ear / cochlear involvement. Refer to Audiologist for hearing aid trial and counseling.",
    "Mixed": "Dual conductive and sensory components identified. Refer to ENT/Audiology for combined medical and amplification evaluation.",
    "Uncertain": "Ambiguous air-conduction configuration. Diagnostic certainty below threshold (<70%). Refer for bone-conduction audiometry."
}


class AIInferenceEngine:
    """
    Orchestrates AC-Only and Full 18-Feature ML pathology classification,
    applies the 70% certainty rejection gate, and falls back gracefully to audiological heuristics.
    """

    def __init__(self):
        self.ac_model = None
        self.ac_encoder = None
        self.full_model = None
        self.full_encoder = None
        self.load_models()

    def load_models(self) -> None:
        """Loads both pickled machine learning models and encoders."""
        # 1. AC-Only model
        if os.path.exists(AC_MODEL_PATH):
            try:
                self.ac_model = joblib.load(AC_MODEL_PATH)
                logger.info("Loaded AC-Only model.")
            except Exception as e:
                logger.warning(f"Could not load AC-Only model: {e}")
        if os.path.exists(AC_ENCODER_PATH):
            try:
                self.ac_encoder = joblib.load(AC_ENCODER_PATH)
            except Exception as e:
                logger.warning(f"Could not load AC-Only encoder: {e}")

        # 2. Full 18-feature model
        if os.path.exists(FULL_MODEL_PATH):
            try:
                self.full_model = joblib.load(FULL_MODEL_PATH)
                logger.info("Loaded Full 18-feature diagnostic model.")
            except Exception as e:
                logger.warning(f"Could not load Full model: {e}")
        if os.path.exists(FULL_ENCODER_PATH):
            try:
                self.full_encoder = joblib.load(FULL_ENCODER_PATH)
            except Exception as e:
                logger.warning(f"Could not load Full encoder: {e}")

    def prepare_13_features(
        self,
        ac_dict: Dict[int, float],
        age: int = 45,
        discharge: int = 0,
        noise: int = 0
    ) -> pd.DataFrame:
        """
        Builds DataFrame row matching the exact 13-feature input:
        AC_250, AC_500, AC_1000, AC_2000, AC_4000, AC_8000,
        AC_slope_low_high = AC_250 - AC_4000,
        AC_slope_500_2000 = AC_500 - AC_2000,
        AC_range = max(AC) - min(AC),
        AC_std = standard_deviation(AC_values),
        age,
        ear_discharge_history (0/1),
        noise_exposure_history (0/1)
        """
        # Ensure standard 6 frequencies exist (extrapolate missing)
        ac_vals = {}
        for f in FREQUENCIES_6:
            if f in ac_dict:
                ac_vals[f] = float(ac_dict[f])
            else:
                # Interpolate or fallback
                ac_vals[f] = float(ac_dict.get(1000, 15.0))

        vals_list = [ac_vals[f] for f in FREQUENCIES_6]

        row = {
            "AC_250": ac_vals[250],
            "AC_500": ac_vals[500],
            "AC_1000": ac_vals[1000],
            "AC_2000": ac_vals[2000],
            "AC_4000": ac_vals[4000],
            "AC_8000": ac_vals[8000],
            "AC_slope_low_high": ac_vals[250] - ac_vals[4000],
            "AC_slope_500_2000": ac_vals[500] - ac_vals[2000],
            "AC_range": float(max(vals_list) - min(vals_list)),
            "AC_std": float(np.std(vals_list, ddof=1) if len(vals_list) > 1 else 0.0),
            "age": int(age),
            "ear_discharge_history": int(1 if discharge else 0),
            "noise_exposure_history": int(1 if noise else 0)
        }
        return pd.DataFrame([row])

    def prepare_18_features(
        self,
        ac_dict: Dict[int, float],
        bc_dict: Dict[int, float]
    ) -> pd.DataFrame:
        """
        Builds DataFrame row matching the full 18-feature model:
        6 AC, then 6 BC, then 6 ABG in exact order.
        """
        row = {}
        for f in FREQUENCIES_6:
            row[f"AC_{f}"] = float(ac_dict.get(f, 15.0))
        for f in FREQUENCIES_6:
            ac_val = row[f"AC_{f}"]
            row[f"BC_{f}"] = float(bc_dict.get(f, ac_val))
        for f in FREQUENCIES_6:
            row[f"ABG_{f}"] = max(0.0, row[f"AC_{f}"] - row[f"BC_{f}"])
            
        # Ensure exact column order matching model if available
        if self.full_model is not None and hasattr(self.full_model, "feature_names_in_"):
            return pd.DataFrame([row])[list(self.full_model.feature_names_in_)]
        return pd.DataFrame([row])

    def run_ac_only_inference(
        self,
        ac_dict: Dict[int, float],
        age: int = 45,
        discharge: int = 0,
        noise: int = 0
    ) -> Dict[str, Any]:
        """
        Performs AC-Only inference with rejection threshold (<0.70 -> Uncertain).
        """
        if self.ac_model is None or self.ac_encoder is None:
            return self.run_audiological_fallback(ac_dict, age, discharge, noise)

        df = self.prepare_13_features(ac_dict, age, discharge, noise)
        try:
            probas = self.ac_model.predict_proba(df)[0]
            classes = list(self.ac_encoder.classes_)
            prob_map = {c: round(float(probas[i]) * 100.0, 1) for i, c in enumerate(classes)}

            max_idx = int(np.argmax(probas))
            max_prob = float(probas[max_idx])
            top_class = classes[max_idx]

            # Rejection threshold check (0.70)
            if max_prob < 0.70:
                predicted_class = "Uncertain — Refer for BC Testing"
                recommendation = RECOMMENDATIONS["Uncertain"]
                is_rejected = True
            else:
                predicted_class = top_class
                recommendation = RECOMMENDATIONS.get(top_class, "Refer for clinical audiology assessment.")
                is_rejected = False

            return {
                "model_used": "AC_Only_Inference_v1",
                "is_ac_only": True,
                "banner": "⚠️ AC-ONLY INFERENCE — Approximate. Confirm with BC testing if available.",
                "prediction": predicted_class,
                "confidence": round(max_prob, 3),
                "is_rejected": is_rejected,
                "all_probabilities": {k: round(v / 100.0, 3) for k, v in prob_map.items()},
                "probabilities_percent": prob_map,
                "recommendation": recommendation,
                "features_used": df.to_dict(orient="records")[0]
            }
        except Exception as e:
            logger.error(f"Error during AC-only prediction: {e}")
            return self.run_audiological_fallback(ac_dict, age, discharge, noise)

    def run_full_inference(
        self,
        ac_dict: Dict[int, float],
        bc_dict: Dict[int, float]
    ) -> Dict[str, Any]:
        """
        Runs the full 18-feature model when bone conduction data is present.
        """
        if self.full_model is None or self.full_encoder is None:
            # Fallback
            return self.run_audiological_fallback(ac_dict, 45, 0, 0, bc_dict=bc_dict)

        df = self.prepare_18_features(ac_dict, bc_dict)
        try:
            probas = self.full_model.predict_proba(df)[0]
            classes = list(self.full_encoder.classes_)
            prob_map = {c: round(float(probas[i]) * 100.0, 1) for i, c in enumerate(classes)}

            max_idx = int(np.argmax(probas))
            max_prob = float(probas[max_idx])
            top_class = classes[max_idx]

            recommendation = RECOMMENDATIONS.get(top_class, "Refer for comprehensive evaluation.")

            return {
                "model_used": "Full_18_Feature_Pathology_Model",
                "is_ac_only": False,
                "banner": "✅ FULL DIAGNOSTIC INFERENCE (Air & Bone Conduction Verified)",
                "prediction": top_class,
                "confidence": round(max_prob, 3),
                "is_rejected": False,
                "all_probabilities": {k: round(v / 100.0, 3) for k, v in prob_map.items()},
                "probabilities_percent": prob_map,
                "recommendation": recommendation,
                "features_used": df.to_dict(orient="records")[0]
            }
        except Exception as e:
            logger.error(f"Error during full model prediction: {e}")
            return self.run_audiological_fallback(ac_dict, 45, 0, 0, bc_dict=bc_dict)

    def run_audiological_fallback(
        self,
        ac_dict: Dict[int, float],
        age: int = 45,
        discharge: int = 0,
        noise: int = 0,
        bc_dict: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """
        Fallback logic per clinical specification when no AI model is loaded:
        - If AC thresholds normal (≤25 dB HL at all frequencies) → Normal
        - If AC flat/rising with significant elevation → Suggest Conductive (flag for BC confirmation)
        - If AC sloping high-frequency loss with age >60 → Suggest Presbycusis/Sensorineural
        - If AC asymmetric (≥15 dB difference at 2+ frequencies) → Flag for detailed examination
        """
        vals = [float(ac_dict.get(f, 15.0)) for f in FREQUENCIES_6]
        max_ac = max(vals)
        mean_ac = np.mean(vals)
        ac_250 = ac_dict.get(250, mean_ac)
        ac_4000 = ac_dict.get(4000, mean_ac)
        slope = ac_250 - ac_4000  # positive if low-freq loss, negative if high-freq loss

        if max_ac <= 25.0:
            pred = "Normal"
            conf = 0.94
            rec = RECOMMENDATIONS["Normal"]
        elif slope > 10.0 or discharge:
            pred = "Conductive"
            conf = 0.84
            rec = "Suggestive of Conductive Hearing Loss. Flagged for Bone Conduction verification and ENT consult."
        elif (ac_4000 - ac_250 >= 20.0 and age > 50) or noise:
            pred = "Sensorineural"
            conf = 0.88
            rec = "Suggestive of Presbycusis / Sensorineural impairment. Refer for audiologic rehabilitation."
        else:
            pred = "Mixed"
            conf = 0.75
            rec = RECOMMENDATIONS["Mixed"]

        prob_map = {
            "Normal": 0.05 if pred != "Normal" else conf,
            "Conductive": 0.05 if pred != "Conductive" else conf,
            "Sensorineural": 0.05 if pred != "Sensorineural" else conf,
            "Mixed": 0.05 if pred != "Mixed" else conf
        }
        # Normalize
        s = sum(prob_map.values())
        prob_map = {k: round(v / s, 3) for k, v in prob_map.items()}

        return {
            "model_used": "Deterministic_Audiological_Fallback",
            "is_ac_only": bc_dict is None or len(bc_dict) == 0,
            "banner": "⚠️ CLINICAL HEURISTIC FALLBACK (Rule-Based Engine)",
            "prediction": pred,
            "confidence": conf,
            "is_rejected": False,
            "all_probabilities": prob_map,
            "probabilities_percent": {k: round(v * 100.0, 1) for k, v in prob_map.items()},
            "recommendation": rec,
            "features_used": {"mean_ac": round(mean_ac, 1), "slope": round(slope, 1), "age": age}
        }

    def analyze_ear_session(
        self,
        ac_thresholds: Dict[int, float],
        bc_thresholds: Optional[Dict[int, float]] = None,
        age: int = 45,
        discharge: int = 0,
        noise: int = 0
    ) -> Dict[str, Any]:
        """
        High-level dispatcher:
        If BC thresholds exist (>=3 frequencies) -> runs Full 18-feature model.
        If BC is missing or incomplete -> runs AC-Only 13-feature model with banner!
        """
        has_bc = bc_thresholds is not None and len(bc_thresholds) >= 3

        if has_bc:
            return self.run_full_inference(ac_thresholds, bc_thresholds)
        else:
            return self.run_ac_only_inference(ac_thresholds, age, discharge, noise)
