import sys
import os
import json
import numpy as np
import pandas as pd
import joblib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, 'hearing_pathology_model.pkl')
ENCODER_PATH = os.path.join(SCRIPT_DIR, 'label_encoder.pkl')
METADATA_PATH = os.path.join(SCRIPT_DIR, 'metadata.json')

FREQUENCIES = [250, 500, 1000, 2000, 4000, 8000]

def load_artifacts():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)
    
    if os.path.exists(ENCODER_PATH):
        encoder = joblib.load(ENCODER_PATH)
        classes = list(encoder.classes_)
    else:
        classes = ["Conductive", "Mixed", "Normal", "Sensorineural"]
        
    metadata = {}
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, 'r') as f:
            metadata = json.load(f)
            
    return model, classes, metadata

def normalize_threshold(val):
    """
    Convert screening relative volume (0.0 to 1.0) to audiometric dB HL.
    0.0 -> 0 dB HL
    0.166 (Slider Level 2 - normal threshold) -> 10.0 dB HL
    0.333 (Slider Level 4) -> 24.0 dB HL
    0.500 (Slider Level 6) -> 38.0 dB HL
    1.000 (Slider Level 12) -> 80.0 dB HL
    """
    if val is None:
        return 10.0
    val_float = float(val)
    if 0.0 <= val_float <= 1.0:
        if val_float <= 0.17:
            return round(val_float * 60.0, 1)
        else:
            return round(10.0 + ((val_float - 0.1666) / (1.0 - 0.1666)) * 70.0, 1)
    # Already in dB HL (> 1.0)
    return round(float(np.clip(val_float, 0.0, 95.0)), 1)

def extract_ac_frequencies(thresholds_dict):
    """
    Extracts AC thresholds for standard 6 frequencies:
    250, 500, 1000, 2000, 4000, 8000 Hz.
    Extrapolates 250 and 8000 if not directly measured.
    """
    cleaned = {}
    for k, v in thresholds_dict.items():
        try:
            freq = int(k)
            cleaned[freq] = normalize_threshold(v)
        except (ValueError, TypeError):
            continue

    ac_500 = cleaned.get(500, 10.0)
    ac_1000 = cleaned.get(1000, 10.0)
    ac_2000 = cleaned.get(2000, 10.0)
    ac_4000 = cleaned.get(4000, 10.0)
    
    # 250 Hz extrapolation (typically closely tracks 500 Hz)
    ac_250 = cleaned.get(250, ac_500)
    
    # 8000 Hz extrapolation based on high-frequency downward slope
    high_freq_slope = max(0.0, ac_4000 - ac_2000)
    ac_8000 = cleaned.get(8000, min(85.0, ac_4000 + (high_freq_slope * 0.5)))
    
    return {
        250: ac_250,
        500: ac_500,
        1000: ac_1000,
        2000: ac_2000,
        4000: ac_4000,
        8000: ac_8000
    }

def estimate_bc_and_abg(ac_dict, speech_score, symptoms=[]):
    """
    Audiological physiological inference for bone-conduction and air-bone gap:
    - Normal: AC <= 15 dB HL -> BC tracks AC, ABG = 0
    - Conductive: High speech score (>= 80%) + flat/rising slope -> healthy cochlea (BC <= 10-12 dB), large ABG
    - Sensorineural: Reduced speech score or steep high-freq loss -> cochlear loss (BC ~ AC, ABG <= 5 dB)
    - Mixed: Elevated BC (> 15 dB) AND substantial ABG (> 15 dB)
    """
    ac_vals = [ac_dict[f] for f in FREQUENCIES]
    avg_ac = float(np.mean(ac_vals))
    symptoms_lower = [str(s).lower() for s in symptoms]
    has_conductive_symptom = any('fullness' in s or 'block' in s or 'wax' in s or 'cold' in s or 'pain' in s for s in symptoms_lower)

    bc_dict = {}
    abg_dict = {}
    
    is_normal = avg_ac <= 14.5
    high_freq_drop = ac_dict[4000] - ac_dict[500]
    
    for f in FREQUENCIES:
        ac = ac_dict[f]
        if is_normal:
            bc = min(ac, 10.0)
        elif (speech_score >= 82 or has_conductive_symptom) and high_freq_drop < 20.0:
            # Conductive: preserved bone conduction (normal cochlea)
            bc = min(ac, 10.0 if f in [250, 500, 1000, 2000] else 12.0)
        elif speech_score < 75 or high_freq_drop >= 25.0:
            # Sensorineural: cochlear impairment where bone conduction matches air conduction
            bc = max(0.0, ac - 2.0)
        else:
            # Mixed loss: both elevated bone conduction and conductive air-bone gap
            bc = max(18.0, ac * 0.55)
            
        abg = max(0.0, round(ac - bc, 1))
        bc_dict[f] = round(bc, 1)
        abg_dict[f] = abg
        
    return bc_dict, abg_dict

def prepare_feature_row(ac_dict, bc_dict, abg_dict):
    """Builds single 18-feature row matching model.feature_names_in_"""
    row = {}
    for f in FREQUENCIES:
        row[f'AC_{f}'] = ac_dict[f]
    for f in FREQUENCIES:
        row[f'BC_{f}'] = bc_dict[f]
    for f in FREQUENCIES:
        row[f'ABG_{f}'] = abg_dict[f]
    return pd.DataFrame([row])

def classify_ear(model, classes, ac_dict, speech_score, symptoms=[]):
    bc_dict, abg_dict = estimate_bc_and_abg(ac_dict, speech_score, symptoms)
    df = prepare_feature_row(ac_dict, bc_dict, abg_dict)
    
    pred_idx = model.predict(df)[0]
    if isinstance(pred_idx, (int, np.integer)):
        predicted_class = classes[pred_idx]
    else:
        predicted_class = str(pred_idx)
        
    proba = model.predict_proba(df)[0]
    prob_map = {}
    for idx, cname in enumerate(classes):
        prob_map[cname] = round(float(proba[idx]) * 100.0, 1)
        
    confidence = prob_map.get(predicted_class, round(float(np.max(proba)) * 100.0, 1))
    
    avg_ac = float(np.mean([ac_dict[f] for f in FREQUENCIES]))
    avg_bc = float(np.mean([bc_dict[f] for f in FREQUENCIES]))
    avg_abg = float(np.mean([abg_dict[f] for f in FREQUENCIES]))
    
    # Clinical explanation
    if predicted_class == 'Normal':
        explanation = f"Air conduction thresholds average {avg_ac:.1f} dB HL with intact bone conduction ({avg_bc:.1f} dB HL). Response reflects healthy audiological sensitivity across tested octaves."
    elif predicted_class == 'Sensorineural':
        explanation = f"Elevated air conduction ({avg_ac:.1f} dB HL) paired with closely coupled bone conduction ({avg_bc:.1f} dB HL, minimal ABG of {avg_abg:.1f} dB) and {speech_score}% speech score indicates inner ear / sensorineural involvement."
    elif predicted_class == 'Conductive':
        explanation = f"Elevated air conduction ({avg_ac:.1f} dB HL) with preserved bone conduction ({avg_bc:.1f} dB HL) reveals a significant Air-Bone Gap of {avg_abg:.1f} dB, characteristic of middle/outer ear mechanical attenuation."
    else: # Mixed
        explanation = f"Both bone conduction attenuation ({avg_bc:.1f} dB HL) and a persistent Air-Bone Gap ({avg_abg:.1f} dB) are present, indicating dual sensory and conductive components."
        
    return {
        "predictedClass": predicted_class,
        "confidence": confidence,
        "probabilities": prob_map,
        "metrics": {
            "meanAcDbHl": round(avg_ac, 1),
            "meanBcDbHl": round(avg_bc, 1),
            "meanAirBoneGap": round(avg_abg, 1),
            "speechScore": speech_score
        },
        "thresholds": {
            "ac": ac_dict,
            "bc": bc_dict,
            "abg": abg_dict
        },
        "explanation": explanation
    }

def run_classification(payload):
    model, classes, metadata = load_artifacts()
    
    left_thresholds = payload.get('leftThresholds', {})
    right_thresholds = payload.get('rightThresholds', {})
    left_speech = payload.get('leftSpeechScore', 100)
    right_speech = payload.get('rightSpeechScore', 100)
    symptoms = payload.get('symptoms', [])
    
    has_left = len(left_thresholds) > 0
    has_right = len(right_thresholds) > 0
    
    left_result = None
    right_result = None
    
    if has_left:
        ac_left = extract_ac_frequencies(left_thresholds)
        left_result = classify_ear(model, classes, ac_left, left_speech, symptoms)
        
    if has_right:
        ac_right = extract_ac_frequencies(right_thresholds)
        right_result = classify_ear(model, classes, ac_right, right_speech, symptoms)
        
    # Overall synthesis
    if left_result and right_result:
        left_class = left_result['predictedClass']
        right_class = right_result['predictedClass']
        
        if left_class == right_class:
            if left_class == 'Normal':
                overall_pathology = 'Normal Hearing'
            else:
                overall_pathology = f"Bilateral {left_class} Hearing Loss"
            overall_confidence = round((left_result['confidence'] + right_result['confidence']) / 2.0, 1)
        else:
            overall_pathology = f"Asymmetric Pathology ({left_class} L / {right_class} R)"
            overall_confidence = round(max(left_result['confidence'], right_result['confidence']), 1)
            
        clinical_summary = (
            f"Machine learning classification via hearing_pathology_model.pkl identified {overall_pathology.lower()}. "
            f"Left ear evaluated as {left_class} ({left_result['confidence']}% confidence); "
            f"Right ear evaluated as {right_class} ({right_result['confidence']}% confidence)."
        )
    elif left_result:
        overall_pathology = left_result['predictedClass']
        overall_confidence = left_result['confidence']
        clinical_summary = f"Left ear classified as {overall_pathology} ({overall_confidence}% confidence). Right ear was not fully tested."
    elif right_result:
        overall_pathology = right_result['predictedClass']
        overall_confidence = right_result['confidence']
        clinical_summary = f"Right ear classified as {overall_pathology} ({overall_confidence}% confidence). Left ear was not fully tested."
    else:
        overall_pathology = 'Insufficient Data'
        overall_confidence = 0.0
        clinical_summary = 'Insufficient pure-tone threshold data for machine learning pathology classification.'
        
    return {
        "success": True,
        "overallPathology": overall_pathology,
        "overallConfidence": overall_confidence,
        "clinicalSummary": clinical_summary,
        "leftEar": left_result,
        "rightEar": right_result,
        "modelMetadata": {
            "modelName": "Random Forest Classifier",
            "modelFile": "hearing_pathology_model.pkl",
            "classes": classes,
            "featureCount": 18,
            "status": "Operational"
        }
    }

def main():
    try:
        if len(sys.argv) > 1:
            input_arg = sys.argv[1]
            data = json.loads(input_arg)
        else:
            input_str = sys.stdin.read()
            if not input_str.strip():
                print(json.dumps({"success": False, "error": "No input provided"}))
                return
            data = json.loads(input_str)
            
        res = run_classification(data)
        print(json.dumps(res))
    except Exception as e:
        import traceback
        err_msg = str(e)
        stack = traceback.format_exc()
        print(json.dumps({"success": False, "error": err_msg, "traceback": stack}))

if __name__ == '__main__':
    main()
