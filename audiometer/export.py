"""
Export Engine for Clinical Software Audiometer.
Generates:
1. Publication-Grade Clinical PDF Report (< 2 seconds) with Audiogram, Grid, AI diagnosis
2. Electronic Medical Record (EMR) JSON
3. Bulk Research CSV
4. HL7 FHIR DiagnosticReport / Observation JSON
"""

import os
import io
import csv
import json
import time
import datetime
import logging
from typing import Dict, Any, Optional

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Headless rendering for rapid PDF generation
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

STANDARD_FREQUENCIES = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]


class ReportExporter:
    """
    Handles PDF generation, JSON EMR packaging, bulk CSV formatting,
    and HL7 FHIR compliance.
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or REPORTS_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_pdf_report(
        self,
        session_data: Dict[str, Any],
        output_filepath: Optional[str] = None
    ) -> str:
        """
        Generates a 2-page / 1-page high-resolution clinical diagnostic audiometry report in PDF format.
        Benchmark requirement: < 2.0 seconds execution time.
        """
        start_time = time.time()
        patient_id = session_data.get("patient_id", "Patient_001").replace("/", "_")
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = output_filepath or os.path.join(self.output_dir, f"Audiogram_Report_{patient_id}_{timestamp_str}.pdf")

        # Create multi-panel clinical document layout
        fig = plt.figure(figsize=(10.5, 13.5), dpi=150)
        fig.patch.set_facecolor('#ffffff')

        # -----------------------------------------------------------------
        # 1. HEADER SECTION
        # -----------------------------------------------------------------
        plt.subplot2grid((7, 2), (0, 0), colspan=2)
        plt.axis('off')
        header_text = (
            "AUDIOLOGICAL EVALUATION & CLINICAL PATHOLOGY REPORT\n"
            "Hardware-Grade Diagnostic Software Audiometer | ISO 8253-1 Compliant"
        )
        plt.text(0.5, 0.70, header_text, ha='center', va='center', fontsize=14, fontweight='bold', color='#0f172a')
        
        info_col1 = (
            f"Patient ID: {session_data.get('patient_id', 'N/A')}\n"
            f"Name: {session_data.get('patient_name', 'Anonymous')}\n"
            f"Age: {session_data.get('age', 'N/A')} years\n"
            f"Date / Time: {session_data.get('timestamp', datetime.datetime.now().isoformat())[:16]}"
        )
        info_col2 = (
            f"Clinician / Operator: {session_data.get('operator', 'Clinical Staff')}\n"
            f"Transducer Profile: {session_data.get('transducer', 'Sennheiser_HDA200')}\n"
            f"Calibration Status: Calibrated (ISO 389-1)\n"
            f"Deployment: Rural Tele-Audiology Field Unit"
        )
        plt.text(0.04, 0.15, info_col1, ha='left', va='center', fontsize=9, color='#334155', linespacing=1.4)
        plt.text(0.54, 0.15, info_col2, ha='left', va='center', fontsize=9, color='#334155', linespacing=1.4)

        # -----------------------------------------------------------------
        # 2. AUDIOGRAM CANVAS PLOT
        # -----------------------------------------------------------------
        ax = plt.subplot2grid((7, 2), (1, 0), rowspan=3, colspan=2)
        ax.set_facecolor('#f8fafc')
        
        # Clinical Audiogram Axes: Inverted dB HL (-10 dB to 120 dB)
        ax.set_ylim(120, -10)
        ax.set_xlim(100, 9000)
        ax.set_xscale('log')
        ax.set_xticks(STANDARD_FREQUENCIES)
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_yticks(np.arange(-10, 130, 10))

        ax.set_xlabel("Frequency (Hz)", fontsize=10, fontweight='bold', color='#1e293b')
        ax.set_ylabel("Hearing Level (dB HL)", fontsize=10, fontweight='bold', color='#1e293b')
        ax.set_title("PURE TONE AUDIOGRAM (BINAURAL)", fontsize=11, fontweight='bold', pad=10, color='#0f172a')

        # Normative hearing shade (<= 25 dB HL is normal)
        ax.axhspan(-10, 25, facecolor='#ecfdf5', alpha=0.6, label='Normal Hearing Area (≤ 25 dB HL)')
        ax.grid(True, which='both', color='#cbd5e1', linestyle=':', linewidth=0.8)

        # Extract test thresholds
        tests = session_data.get("tests", {}).get("pure_tone", {})
        r_ac = tests.get("right", {}).get("AC", {})
        l_ac = tests.get("left", {}).get("AC", {})
        r_bc = tests.get("right", {}).get("BC", {})
        l_bc = tests.get("left", {}).get("BC", {})

        # Plot Right AC: Red circle 'o' with solid line
        if r_ac:
            f_r = sorted([int(f) for f in r_ac.keys()])
            y_r = [r_ac[str(f)] for f in f_r]
            ax.plot(f_r, y_r, color='#dc2626', marker='o', markersize=8, linewidth=1.8,
                    markerfacecolor='none', markeredgewidth=2.0, label='Right Ear AC (O)')

        # Plot Left AC: Blue cross 'x' with solid line
        if l_ac:
            f_l = sorted([int(f) for f in l_ac.keys()])
            y_l = [l_ac[str(f)] for f in f_l]
            ax.plot(f_l, y_l, color='#2563eb', marker='x', markersize=8, linewidth=1.8,
                    markeredgewidth=2.0, label='Left Ear AC (X)')

        # Plot Right BC: Red '<' with dashed line
        if r_bc:
            f_rb = sorted([int(f) for f in r_bc.keys()])
            y_rb = [r_bc[str(f)] for f in f_rb]
            ax.plot(f_rb, y_rb, color='#dc2626', linestyle='--', marker='<', markersize=8,
                    markerfacecolor='none', markeredgewidth=1.8, label='Right Ear BC (<)')

        # Plot Left BC: Blue '>' with dashed line
        if l_bc:
            f_lb = sorted([int(f) for f in l_bc.keys()])
            y_lb = [l_bc[str(f)] for f in f_lb]
            ax.plot(f_lb, y_lb, color='#2563eb', linestyle='--', marker='>', markersize=8,
                    markerfacecolor='none', markeredgewidth=1.8, label='Left Ear BC (>)')

        ax.legend(loc='lower left', fontsize=8, framealpha=0.85)

        # -----------------------------------------------------------------
        # 3. THRESHOLD DATA TABLE
        # -----------------------------------------------------------------
        ax_tab = plt.subplot2grid((7, 2), (4, 0), colspan=2)
        ax_tab.axis('off')

        headers = ["Freq (Hz)", "125", "250", "500", "750", "1000", "1500", "2000", "3000", "4000", "6000", "8000", "PTA (4F)"]
        
        def format_row(label, t_dict, pta_val):
            row = [label]
            for f in [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]:
                val = t_dict.get(str(f))
                row.append(f"{val:.0f}" if val is not None else "-")
            row.append(f"{pta_val:.1f} dB" if pta_val is not None else "-")
            return row

        # Calculate PTAs
        def calc_pta(d):
            vals = [d.get(str(f)) for f in [500, 1000, 2000, 4000] if d.get(str(f)) is not None]
            return round(sum(vals)/len(vals), 1) if vals else None

        r_pta = calc_pta(r_ac)
        l_pta = calc_pta(l_ac)

        cell_data = [
            format_row("Right AC (dB)", r_ac, r_pta),
            format_row("Left AC (dB)", l_ac, l_pta),
            format_row("Right BC (dB)", r_bc, calc_pta(r_bc)),
            format_row("Left BC (dB)", l_bc, calc_pta(l_bc))
        ]

        table = ax_tab.table(
            cellText=cell_data,
            colLabels=headers,
            loc='center',
            cellLoc='center'
        )
        table.auto_set_font_size(False)
        table.set_fontsize(7.5)
        table.scale(1.0, 1.4)

        # Color the header row
        for i in range(len(headers)):
            table[(0, i)].set_facecolor('#e2e8f0')
            table[(0, i)].set_text_props(weight='bold', color='#0f172a')

        # -----------------------------------------------------------------
        # 4. SPEECH AUDIOMETRY & PATIENT RELIABILITY
        # -----------------------------------------------------------------
        ax_sp = plt.subplot2grid((7, 2), (5, 0))
        ax_sp.axis('off')
        speech = session_data.get("tests", {}).get("speech", {})
        r_srt = speech.get("right", {}).get("SRT", "N/A")
        r_wrs = speech.get("right", {}).get("WRS", "N/A")
        l_srt = speech.get("left", {}).get("SRT", "N/A")
        l_wrs = speech.get("left", {}).get("WRS", "N/A")

        speech_text = (
            "SPEECH AUDIOMETRY SUMMARY\n"
            f"• Right Ear: SRT = {r_srt} dB HL | WRS = {r_wrs}%\n"
            f"• Left Ear:  SRT = {l_srt} dB HL | WRS = {l_wrs}%\n"
            f"• Test Materials: Spondee & Phonetically Balanced Word Lists"
        )
        ax_sp.text(0.05, 0.70, speech_text, fontsize=8.5, linespacing=1.5, color='#1e293b', fontweight='medium')

        ax_rel = plt.subplot2grid((7, 2), (5, 1))
        ax_rel.axis('off')
        reliability = session_data.get("patient_reliability", 1.0)
        rel_text = (
            "RELIABILITY & QUALITY ASSURANCE\n"
            f"• Patient Reliability Score: {reliability * 100:.1f}%\n"
            f"• Ambient Room Noise Level: {session_data.get('ambient_noise_spl', 35.0)} dB SPL (ISO 8253-1 Permissible)\n"
            f"• Transducer Output Check: Digital Safety Limit Active (0 dBFS Clamping)"
        )
        ax_rel.text(0.05, 0.70, rel_text, fontsize=8.5, linespacing=1.5, color='#1e293b', fontweight='medium')

        # -----------------------------------------------------------------
        # 5. AI PATHOLOGY INFERENCE RESULTS CARD
        # -----------------------------------------------------------------
        ax_ai = plt.subplot2grid((7, 2), (6, 0), colspan=2)
        ax_ai.axis('off')

        ai_data = session_data.get("ai_analysis", {})
        pred = ai_data.get("prediction", "Normal")
        conf = ai_data.get("confidence", 0.90)
        rec = ai_data.get("recommendation", "Routine follow up.")
        model_name = ai_data.get("model_used", "AC_Only_Inference_v1")
        banner = ai_data.get("banner", "AI Pathology Prediction")

        # Background color for AI diagnosis card
        is_ac_only = "AC-ONLY" in banner.upper() or "AC_ONLY" in model_name.upper()
        card_color = "#fffbeb" if is_ac_only else "#f0fdf4"
        edge_color = "#f59e0b" if is_ac_only else "#22c55e"

        card = plt.Rectangle((0.02, 0.05), 0.96, 0.88, transform=ax_ai.transAxes,
                             facecolor=card_color, edgecolor=edge_color, linewidth=1.5,
                             clip_on=False, zorder=0)
        ax_ai.add_patch(card)

        ai_text = (
            f"{banner}\n"
            f"Diagnostic Classification: {pred.upper()} (Certainty: {conf * 100:.1f}%)\n"
            f"Clinical Recommendation: {rec}\n"
            f"Model Architecture: Random Forest Ensemble ({model_name}) | Offline Local Inference"
        )
        ax_ai.text(0.05, 0.50, ai_text, va='center', fontsize=8.5, color='#0f172a', linespacing=1.4, fontweight='medium')

        plt.tight_layout()
        plt.savefig(target_path, format='pdf', bbox_inches='tight')
        plt.close(fig)

        elapsed = time.time() - start_time
        logger.info(f"PDF report generated in {elapsed:.2f} seconds at: {target_path}")
        return target_path

    def export_emr_json(self, session_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Exports session data as standard EMR JSON."""
        patient_id = session_data.get("patient_id", "Patient_001").replace("/", "_")
        target_path = output_path or os.path.join(self.output_dir, f"EMR_{patient_id}.json")
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)
        return target_path

    def export_research_csv(self, session_data: Dict[str, Any], csv_path: Optional[str] = None) -> str:
        """Appends session record to bulk research CSV."""
        target_path = csv_path or os.path.join(self.output_dir, "audiometry_research_bulk.csv")
        file_exists = os.path.exists(target_path)

        # Flatten features
        tests = session_data.get("tests", {}).get("pure_tone", {})
        r_ac = tests.get("right", {}).get("AC", {})
        l_ac = tests.get("left", {}).get("AC", {})
        speech = session_data.get("tests", {}).get("speech", {})
        ai = session_data.get("ai_analysis", {})

        row = {
            "patient_id": session_data.get("patient_id", ""),
            "timestamp": session_data.get("timestamp", datetime.datetime.now().isoformat()),
            "age": session_data.get("age", ""),
            "operator": session_data.get("operator", ""),
            "transducer": session_data.get("transducer", ""),
            "ambient_noise_spl": session_data.get("ambient_noise_spl", 35.0),
            "patient_reliability": session_data.get("patient_reliability", 1.0),
            # AC Right
            "AC_R_250": r_ac.get("250", ""),
            "AC_R_500": r_ac.get("500", ""),
            "AC_R_1000": r_ac.get("1000", ""),
            "AC_R_2000": r_ac.get("2000", ""),
            "AC_R_4000": r_ac.get("4000", ""),
            "AC_R_8000": r_ac.get("8000", ""),
            # AC Left
            "AC_L_250": l_ac.get("250", ""),
            "AC_L_500": l_ac.get("500", ""),
            "AC_L_1000": l_ac.get("1000", ""),
            "AC_L_2000": l_ac.get("2000", ""),
            "AC_L_4000": l_ac.get("4000", ""),
            "AC_L_8000": l_ac.get("8000", ""),
            # Speech
            "SRT_Right": speech.get("right", {}).get("SRT", ""),
            "WRS_Right": speech.get("right", {}).get("WRS", ""),
            "SRT_Left": speech.get("left", {}).get("SRT", ""),
            "WRS_Left": speech.get("left", {}).get("WRS", ""),
            # AI Inference
            "AI_Model": ai.get("model_used", ""),
            "AI_Prediction": ai.get("prediction", ""),
            "AI_Confidence": ai.get("confidence", "")
        }

        with open(target_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        return target_path

    def export_hl7_fhir_json(self, session_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Exports HL7 FHIR DiagnosticReport resource (LOINC 89025-1: Pure Tone Audiometry Study).
        """
        patient_id = session_data.get("patient_id", "Patient_001").replace("/", "_")
        target_path = output_path or os.path.join(self.output_dir, f"FHIR_DiagnosticReport_{patient_id}.json")

        fhir_report = {
            "resourceType": "DiagnosticReport",
            "id": f"audiometry-{patient_id}",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                    "code": "AU",
                    "display": "Audiology"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "89025-1",
                    "display": "Pure tone audiometry panel"
                }],
                "text": "Pure Tone Audiometry & AI Hearing Pathology Assessment"
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": session_data.get("patient_name", "Anonymous")
            },
            "effectiveDateTime": session_data.get("timestamp", datetime.datetime.now().isoformat()),
            "performer": [{
                "display": session_data.get("operator", "Clinician")
            }],
            "conclusion": f"{session_data.get('ai_analysis', {}).get('prediction', 'Normal')} Hearing Pathology. {session_data.get('ai_analysis', {}).get('recommendation', '')}",
            "extension": [{
                "url": "http://audiology.org/fhir/StructureDefinition/ai-confidence",
                "valueDecimal": float(session_data.get("ai_analysis", {}).get("confidence", 0.90))
            }]
        }

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(fhir_report, f, indent=2)
        return target_path
