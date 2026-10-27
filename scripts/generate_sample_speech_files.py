"""
Generates reference 48kHz WAV speech audio files for Hindi and English Spondees and PB words.
"""

import os
import sys
import wave
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from audiometer.speech_materials import SpeechEngine, SPONDEES, PB_WORDS

SAMPLE_RATE = 48000
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "speech_materials")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def write_wav(filepath: str, samples: np.ndarray, sample_rate: int = 48000):
    int16_samples = np.int16(np.clip(samples, -1.0, 1.0) * 32767)
    with wave.open(filepath, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(int16_samples.tobytes())

def main():
    engine = SpeechEngine(sample_rate=SAMPLE_RATE)
    print(f"Generating speech WAV files into: {OUTPUT_DIR}")
    
    # English Spondees
    en_dir = os.path.join(OUTPUT_DIR, "en")
    os.makedirs(en_dir, exist_ok=True)
    for word in SPONDEES["en"][:10]:
        filename = f"spondee_{word.lower()}.wav"
        path = os.path.join(en_dir, filename)
        audio = engine.synthesize_word_audio(word, duration_s=1.2)
        write_wav(path, audio, SAMPLE_RATE)
        print(f"Created {path}")

    # Hindi Spondees (romanized file keys)
    hi_dir = os.path.join(OUTPUT_DIR, "hi")
    os.makedirs(hi_dir, exist_ok=True)
    hi_words = [
        ("railgadi", "रेलगाड़ी"),
        ("darwaza", "दरवाज़ा"),
        ("dak_khana", "डाकखाना"),
        ("phoolgobhi", "फूलगोभी"),
        ("barsaat", "बरसात"),
        ("kitabghar", "किताबघर"),
        ("doodhwala", "दूधवाला"),
        ("chaypatti", "चायपत्ती"),
        ("ghadisaz", "घड़ीसाज़"),
        ("deewar", "दीवार")
    ]
    for rom, dev in hi_words:
        filename = f"spondee_{rom}.wav"
        path = os.path.join(hi_dir, filename)
        audio = engine.synthesize_word_audio(dev, duration_s=1.2)
        write_wav(path, audio, SAMPLE_RATE)
        print(f"Created Hindi spondee: {filename}")

    # Tamil Spondees (romanized file keys)
    ta_dir = os.path.join(OUTPUT_DIR, "ta")
    os.makedirs(ta_dir, exist_ok=True)
    ta_words = [
        ("thabalpetti", "தபால்பெட்டி"),
        ("poonthottam", "பூந்தோட்டம்"),
        ("kaikkudikaram", "கைக்கடிகாரம்"),
        ("pallivasal", "பள்ளிவாசல்"),
        ("vanoorthi", "வானூர்தி"),
        ("mazaikalam", "மழைக்காலம்"),
        ("puthagappai", "புத்தகப்பை"),
        ("kannadi", "கண்ணாடி")
    ]
    for rom, tam in ta_words:
        filename = f"spondee_{rom}.wav"
        path = os.path.join(ta_dir, filename)
        audio = engine.synthesize_word_audio(tam, duration_s=1.2)
        write_wav(path, audio, SAMPLE_RATE)
        print(f"Created Tamil spondee: {filename}")

    print("All sample speech test audio files successfully generated.")

if __name__ == "__main__":
    main()
