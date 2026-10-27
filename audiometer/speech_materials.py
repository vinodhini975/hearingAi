"""
Speech Audiometry Materials and Signal Player.
Contains standardized Spondee and Phonetically Balanced (PB) word lists
for English, Hindi, and Tamil, with offline audio generation and playback.
"""

import os
import math
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)

# Standard clinical Spondee word lists (bisyllabic with equal stress)
SPONDEES = {
    "en": [
        "Airplane", "Baseball", "Cupcake", "Doormat", "Eyeball",
        "Firefly", "Grandslam", "Hotdog", "Iceberg", "Keyboard",
        "Lifeguard", "Mushroom", "Necktie", "Oatmeal", "Pancake",
        "Railroad", "Sailboat", "Toothbrush", "Uptown", "Windmill"
    ],
    "hi": [
        "रेलगाड़ी (Railgadi)", "दरवाज़ा (Darwaza)", "डाकखाना (Dak-khana)", "फूलगोभी (Phoolgobhi)", "बरसात (Barsaat)",
        "किताबघर (Kitabghar)", "दूधवाला (Doodhwala)", "चायपत्ती (Chaypatti)", "घड़ीसाज़ (Ghadisaz)", "दीवार (Deewar)",
        "फलदार (Phaldaar)", "पनघट (Panghat)", "अखबार (Akhbar)", "हवाई (Hawai)", "सड़क (Sadak)"
    ],
    "ta": [
        "தபால்பெட்டி (Thabalpetti)", "பூந்தோட்டம் (Poonthottam)", "கைக்கடிகாரம் (Kaikkudikaram)", "பள்ளிவாசல் (Pallivasal)", "வானூர்தி (Vanoorthi)",
        "மழைக்காலம் (Mazaikalam)", "புத்தகப்பை (Puthagappai)", "கண்ணாடி (Kannadi)", "விளையாட்டு (Vilaiyaattu)", "கடற்கரை (Kadarkarai)"
    ],
    "bn": [
        "রেলগাড়ি (Railgari)", "ফুলদানি (Phuldani)", "ডাকঘর (Dakghar)", "বৃষ্টিপাত (Brishtipat)", "রান্নাঘর (Rannaghar)",
        "খবরেরকাগজ (Khaborerkagoj)", "দরজা (Dorja)", "মাঠঘাট (Mathghat)", "জলখাবার (Jolkhabar)", "পথঘাট (Pothghat)"
    ]
}

# Phonetically Balanced (PB) word lists (monosyllabic / standardized representative frequency distribution)
PB_WORDS = {
    "en": [
        "Bat", "Cap", "Dog", "Fan", "Hat", "Jug", "Kite", "Log", "Map", "Net",
        "Pin", "Rat", "Sun", "Tub", "Van", "Web", "Box", "Cup", "Duck", "Frog",
        "Gold", "Hill", "Jam", "Leaf", "Moon"
    ],
    "hi": [
        "कल (Kal)", "जल (Jal)", "मन (Man)", "फल (Phal)", "घर (Ghar)",
        "नल (Nal)", "धन (Dhan)", "तन (Tan)", "खत (Khat)", "बस (Bas)",
        "सच (Sach)", "रस (Ras)", "हल (Hal)", "पथ (Path)", "डगर (Dagar)"
    ],
    "ta": [
        "கல் (Kal)", "மண் (Man)", "கண் (Kan)", "பால் (Paal)", "பூ (Poo)",
        "தீ (Thee)", "கை (Kai)", "நீர் (Neer)", "பல் (Pal)", "வில் (Vil)",
        "சொல் (Sol)", "நெல் (Nel)", "மீன் (Meen)", "மான் (Maan)", "தேன் (Then)"
    ],
    "bn": [
        "জল (Jol)", "ফল (Phol)", "মন (Mon)", "ঘর (Ghor)", "পাখি (Pakhi)",
        "ফুল (Phul)", "গাছ (Gachh)", "নদী (Nodi)", "চাঁদ (Chand)", "বই (Boi)"
    ]
}


class SpeechEngine:
    """
    Manages speech word lists, synthetic acoustic modeling for offline presentation,
    and conducts SRT (Speech Reception Threshold) and WRS (Word Recognition Score).
    """

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.materials_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "speech_materials"
        )

    def get_word_audio(self, word: str, lang: str = "en") -> Tuple[np.ndarray, int]:
        """
        Attempts to load recorded 48 kHz speech WAV sample from speech_materials.
        If file not found, uses formant-synthesized vocal token.
        Returns: (audio_samples, sample_rate)
        """
        import wave
        clean_name = word.split("(")[-1].replace(")", "").strip().lower()
        clean_name = clean_name.replace(" ", "_").replace("-", "_")
        lang_dir = os.path.join(self.materials_dir, lang.lower())
        
        # Check standard filenames
        possible_files = [
            os.path.join(lang_dir, f"spondee_{clean_name}.wav"),
            os.path.join(lang_dir, f"pb_{clean_name}.wav"),
            os.path.join(lang_dir, f"{clean_name}.wav")
        ]
        
        for p in possible_files:
            if os.path.exists(p):
                try:
                    with wave.open(p, "rb") as wf:
                        sr = wf.getframerate()
                        n_frames = wf.getnframes()
                        raw = wf.readframes(n_frames)
                        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                        return audio, sr
                except Exception as e:
                    logger.warning(f"Failed to read WAV {p}: {e}")

        return self.synthesize_word_audio(word, duration_s=1.2), self.sample_rate

    def get_spondee_list(self, lang: str = "en") -> List[str]:
        """Returns localized spondee word list."""
        return SPONDEES.get(lang.lower(), SPONDEES["en"])

    def get_pb_list(self, lang: str = "en") -> List[str]:
        """Returns localized phonetically balanced word list."""
        return PB_WORDS.get(lang.lower(), PB_WORDS["en"])

    def synthesize_word_audio(self, word: str, duration_s: float = 1.0) -> np.ndarray:
        """
        Generates calibrated formant-synthesized vocalic speech token waveform
        for offline testing without external internet or missing WAV files.
        Models typical speech envelope and formants (F0=130Hz, F1=700Hz, F2=1220Hz, F3=2600Hz).
        """
        num_samples = int(self.sample_rate * duration_s)
        t = np.arange(num_samples) / self.sample_rate

        # Fundamental pitch glottal pulse train simulation
        f0 = 135.0 + 10.0 * np.sin(2.0 * np.pi * 1.5 * t)
        phase = np.cumsum(2.0 * np.pi * f0 / self.sample_rate)
        glottal = signal.sawtooth(phase, width=0.1)

        # Formant frequencies based on hash of word to provide distinct acoustic signatures
        word_hash = sum(ord(c) for c in word) % 5
        f1_presets = [500.0, 700.0, 350.0, 600.0, 400.0]
        f2_presets = [1500.0, 1200.0, 2000.0, 1800.0, 1100.0]
        f3 = 2600.0

        f1 = f1_presets[word_hash]
        f2 = f2_presets[word_hash]

        # Simple resonance filtering via additive harmonics
        h1 = np.sin(phase) * 1.0
        h2 = np.sin(phase * (f1 / 135.0)) * 0.7
        h3 = np.sin(phase * (f2 / 135.0)) * 0.4
        h4 = np.sin(phase * (f3 / 135.0)) * 0.15

        voice = h1 + h2 + h3 + h4

        # Speech amplitude envelope (attack, vowel steady, decay)
        envelope = np.ones(num_samples, dtype=np.float32)
        attack = int(0.12 * self.sample_rate)
        decay = int(0.25 * self.sample_rate)
        envelope[:attack] = np.linspace(0.0, 1.0, attack)
        envelope[-decay:] = np.linspace(1.0, 0.0, decay)

        synthetic_speech = (voice * envelope).astype(np.float32)

        # Normalization
        max_val = np.max(np.abs(synthetic_speech))
        if max_val > 1e-4:
            synthetic_speech = synthetic_speech / max_val * 0.7

        return synthetic_speech
