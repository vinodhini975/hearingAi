"""
Comprehensive Localization Engine for Software Audiometer.
Supports English, Hindi (हिन्दी), Tamil (தமிழ்), and Bengali (বাংলা).
"""
from typing import Optional, Dict

TRANSLATIONS = {
    "en": {
        "app_title": "Clinical Diagnostic Audiometer & AI Pathology Analyzer",
        "tagline": "Hardware-Grade Audiometry for Clinical & Field Deployments",
        "lang_name": "English",
        
        # Navigation / Panels
        "nav_pure_tone": "Pure Tone Audiometry",
        "nav_speech": "Speech Audiometry",
        "nav_special": "Special Tests",
        "nav_calibration": "Calibration Wizard",
        "nav_ai_analysis": "AI Pathology Analysis",
        "nav_reports": "Patient Reports & Export",
        
        # Test Controls
        "frequency": "Frequency (Hz)",
        "intensity": "Intensity (dB HL)",
        "ear": "Test Ear",
        "right_ear": "Right (Red)",
        "left_ear": "Left (Blue)",
        "conduction": "Conduction Type",
        "air_conduction": "Air Conduction (AC)",
        "bone_conduction": "Bone Conduction (BC)",
        "present_tone": "Present Tone [Space]",
        "store_threshold": "Store Threshold [Enter]",
        "start_hw": "Auto Hughson-Westlake",
        "start_bekesy": "Auto Bekesy Tracking",
        "stop_test": "Stop Stimulus",
        "step_size": "Step Size (5 dB Manual / 1 dB Research)",
        "masking": "Narrowband Masking",
        "masking_level": "Masking Level (dB HL)",
        "masking_auto": "Auto Masking Calculation",
        
        # Patient Info
        "patient_details": "Patient Demographics & Medical History",
        "patient_name": "Full Name",
        "patient_id": "Patient ID / MRN",
        "patient_age": "Age (Years)",
        "operator": "Operator / Clinician",
        "history_discharge": "History of Ear Discharge (CSOM)",
        "history_noise": "Occupational / Severe Noise Exposure",
        "history_pain": "Ear Pain / Otalgia",
        "history_meds": "Ototoxic Medications / Chemotherapy",
        
        # Ambient Noise Monitoring
        "ambient_noise": "Ambient Room Noise",
        "noise_measuring": "Measuring ambient noise (5s calibration)...",
        "noise_acceptable": "Ambient Noise Optimal (< 45 dB SPL)",
        "noise_warning": "Warning: Ambient Noise Elevated (> 45 dB SPL)",
        "noise_blocked": "BLOCKED: Ambient Noise Critical (> 55 dB SPL). Relocate to a quieter room.",
        
        # Status & Reliability
        "patient_reliability": "Patient Reliability Index",
        "status_reliable": "Reliable",
        "status_questionable": "Questionable",
        "status_unreliable": "Unreliable / High False Alarms",
        "pta_calculated": "Pure Tone Average (PTA 500-4000 Hz)",
        
        # AI Engine
        "run_ai_analysis": "Run Machine Learning Pathology Analysis",
        "ac_only_banner": "⚠️ AC-ONLY INFERENCE — Approximate. Confirm with BC testing if available.",
        "full_model_banner": "✅ FULL DIAGNOSTIC INFERENCE (Air & Bone Conduction Verified)",
        "predicted_pathology": "Predicted Pathology",
        "confidence": "Certainty / Confidence",
        "recommendation": "Clinical Recommendation",
        "class_normal": "Normal Hearing",
        "class_conductive": "Conductive Hearing Loss",
        "class_sensorineural": "Sensorineural Hearing Loss",
        "class_mixed": "Mixed Hearing Loss",
        "class_uncertain": "Uncertain — Refer for Bone Conduction Testing",
        
        # Patient Instructions
        "instructions_title": "Patient Audiometry Instructions",
        "instruction_pure_tone": "You will hear brief tones of varying loudness in one ear. Press the button or spacebar as soon as you detect even the faintest beep, and release it immediately.",
        "instruction_speech": "You will hear words spoken through the headphones. Repeat each word aloud as clearly as possible, even if it is very soft.",
        
        # Speech Audiometry
        "srt_label": "Speech Reception Threshold (SRT)",
        "wrs_label": "Word Recognition Score (WRS)",
        "word_correct": "Correct Repeat",
        "word_incorrect": "Incorrect Repeat",
        
        # Hardware & Export
        "usb_dac_warning": "⚠️ Warning: No external USB DAC detected. Built-in sound card may introduce noise floor.",
        "bc_unavailable_warning": "⚠️ Bone conduction hardware not detected. AC-Only mode active.",
        "export_pdf": "Generate PDF Clinical Report",
        "export_json": "Export JSON (EMR)",
        "export_csv": "Export CSV (Research)",
        "export_fhir": "Export HL7 FHIR Observation"
    },
    
    "hi": {
        "app_title": "क्लिनिकल ऑडियोमीटर और एआई पैथोलॉजी विश्लेषक",
        "tagline": "अस्पतालों और ग्रामीण स्वास्थ्य केंद्रों के लिए उन्नत हियरिंग टेस्टर",
        "lang_name": "हिन्दी (Hindi)",
        
        # Navigation / Panels
        "nav_pure_tone": "प्योर टोन ऑडियोमेट्री (PTA)",
        "nav_speech": "स्पीच ऑडियोमेट्री",
        "nav_special": "विशेष परीक्षण",
        "nav_calibration": "कैलिब्रेशन विज़ार्ड",
        "nav_ai_analysis": "एआई पैथोलॉजी विश्लेषण",
        "nav_reports": "रोगी रिपोर्ट और निर्यात",
        
        # Test Controls
        "frequency": "आवृत्ति / फ्रीक्वेंसी (Hz)",
        "intensity": "तीव्रता (dB HL)",
        "ear": "परीक्षण कान",
        "right_ear": "दायां कान (लाल)",
        "left_ear": "बायां कान (नीला)",
        "conduction": "कंडक्शन का प्रकार",
        "air_conduction": "एयर कंडक्शन (AC)",
        "bone_conduction": "बोन कंडक्शन (BC)",
        "present_tone": "ध्वनि सुनाएं [Space]",
        "store_threshold": "थ्रेशोल्ड सहेजें [Enter]",
        "start_hw": "स्वचालित ह्यूगसन-वेस्टलेक",
        "start_bekesy": "ऑटो बेकेसी ट्रैकिंग",
        "stop_test": "ध्वनि रोकें",
        "step_size": "कदम का आकार (5 dB मैनुअल / 1 dB शोध)",
        "masking": "मास्किंग शोर",
        "masking_level": "मास्किंग स्तर (dB HL)",
        "masking_auto": "स्वचालित मास्किंग गणना",
        
        # Patient Info
        "patient_details": "मरीज का विवरण और मेडिकल इतिहास",
        "patient_name": "पूरा नाम",
        "patient_id": "मरीज आईडी / पंजीकरण संख्या",
        "patient_age": "उम्र (वर्ष)",
        "operator": "जांचकर्ता / ऑडियोलॉजिस्ट",
        "history_discharge": "कान से मवाद / पानी आने का इतिहास",
        "history_noise": "तेज़ आवाज़ / शोर में काम का इतिहास",
        "history_pain": "कान में दर्द का इतिहास",
        "history_meds": "कान को नुकसान पहुंचाने वाली दवाएं",
        
        # Ambient Noise Monitoring
        "ambient_noise": "कमरे का शोर स्तर",
        "noise_measuring": "कमरे के शोर की 5 सेकंड जांच हो रही है...",
        "noise_acceptable": "कमरे का शोर सही है (< 45 dB SPL)",
        "noise_warning": "चेतावनी: कमरे में शोर अधिक है (> 45 dB SPL)",
        "noise_blocked": "रोक दिया गया: शोर बहुत अधिक है (> 55 dB SPL)। शांत कमरे में जाएं।",
        
        # Status & Reliability
        "patient_reliability": "मरीज की प्रतिक्रिया विश्वसनीयता",
        "status_reliable": "विश्वसनीय",
        "status_questionable": "संदेहास्पद",
        "status_unreliable": "अविश्वसनीय (गलत बटन दबाना)",
        "pta_calculated": "औसत श्रवण स्तर (PTA)",
        
        # AI Engine
        "run_ai_analysis": "एआई पैथोलॉजी जांच शुरू करें",
        "ac_only_banner": "⚠️ केवल एयर कंडक्शन (AC-Only) विश्लेषण — अनुमानित। यदि उपलब्ध हो तो बोन कंडक्शन से पुष्टि करें।",
        "full_model_banner": "✅ पूर्ण नैदानिक विश्लेषण (एयर व बोन कंडक्शन दोनों सत्यापित)",
        "predicted_pathology": "अनुमानित बीमारी / विकार",
        "confidence": "सटीकता / विश्वास स्तर",
        "recommendation": "चिकित्सीय सलाह",
        "class_normal": "सामान्य श्रवण शक्ति (Normal)",
        "class_conductive": "कंडक्टिव हियरिंग लॉस (मध्य कान विकार)",
        "class_sensorineural": "सेंसोरीन्यूरल हियरिंग लॉस (अंदरूनी कान विकार)",
        "class_mixed": "मिक्स्ड हियरिंग लॉस (संयुक्त विकार)",
        "class_uncertain": "अनिश्चित — बोन कंडक्शन जांच की सिफारिश करें",
        
        # Patient Instructions
        "instructions_title": "मरीज के लिए निर्देश",
        "instruction_pure_tone": "आपको हेडफोन में अलग-अलग बीप की आवाज सुनाई देगी। जैसे ही हल्की सी भी बीप सुनाई दे, तुरंत बटन या स्पेसबार दबाएं और छोड़ दें।",
        "instruction_speech": "आपको हेडफोन में शब्द सुनाई देंगे। प्रत्येक शब्द को सुनकर जोर से दोहराएं, चाहे वह कितना भी धीमा हो।",
        
        # Speech Audiometry
        "srt_label": "स्पीच रिसेप्शन थ्रेशोल्ड (SRT)",
        "wrs_label": "शब्द पहचान प्रतिशत (WRS)",
        "word_correct": "सही दोहराया",
        "word_incorrect": "गलत दोहराया",
        
        # Hardware & Export
        "usb_dac_warning": "⚠️ चेतावनी: यूएसबी डीएसी नहीं मिला। बिल्ट-इन कार्ड में शोर हो सकता है।",
        "bc_unavailable_warning": "⚠️ बोन कंडक्शन हार्डवेयर उपलब्ध नहीं है। AC-Only मोड सक्रिय।",
        "export_pdf": "पीडीएफ क्लिनिकल रिपोर्ट बनाएं",
        "export_json": "ईएमआर जेएसओएन निर्यात",
        "export_csv": "सीएसवी डेटा निर्यात",
        "export_fhir": "एचएल7 एफएचआईआर निर्यात"
    },
    
    "ta": {
        "app_title": "மருத்துவ காதுகேட்பு பரிசோதனை மற்றும் AI பகுப்பாய்வி",
        "tagline": "கிராமப்புற மற்றும் மருத்துவ பயன்பாட்டிற்கான நவீன பரிசோதனைக் கருவி",
        "lang_name": "தமிழ் (Tamil)",
        
        # Navigation / Panels
        "nav_pure_tone": "தூய ஒலி பரிசோதனை (PTA)",
        "nav_speech": "பேச்சு ஒலி பரிசோதனை",
        "nav_special": "சிறப்பு பரிசோதனைகள்",
        "nav_calibration": "அளவீட்டு வழிகாட்டி (Calibration)",
        "nav_ai_analysis": "AI நோயியல் பகுப்பாய்வு",
        "nav_reports": "நோயாளி அறிக்கை மற்றும் பதிவிறக்கம்",
        
        # Test Controls
        "frequency": "அதிர்வெண் / Frequency (Hz)",
        "intensity": "ஒலி அளவு (dB HL)",
        "ear": "சோதனை காது",
        "right_ear": "வலது காது (சிவப்பு)",
        "left_ear": "இடது காது (நீலம்)",
        "conduction": "கடத்தல் வகை",
        "air_conduction": "காற்று வழி கடத்தல் (AC)",
        "bone_conduction": "எலும்பு வழி கடத்தல் (BC)",
        "present_tone": "ஒலி எழுப்பு [Space]",
        "store_threshold": "கேட்பு எல்லையை சேமி [Enter]",
        "start_hw": "தானியங்கி ஹக்ள்சன்-வெஸ்ட்லேக்",
        "start_bekesy": "பெகேசி தானியங்கி கண்காணிப்பு",
        "stop_test": "ஒலியை நிறுத்து",
        "step_size": "அளவு மாற்றம் (5 dB / 1 dB)",
        "masking": "மறைப்பு இரைச்சல் (Masking)",
        "masking_level": "மறைப்பு அளவு (dB HL)",
        "masking_auto": "தானியங்கி மறைப்பு கணக்கீடு",
        
        # Patient Info
        "patient_details": "நோயாளி விவரம் மற்றும் மருத்துவ வரலாறு",
        "patient_name": "முழு பெயர்",
        "patient_id": "நோயாளி எண் (MRN)",
        "patient_age": "வயது",
        "operator": "பரிசோதகர்",
        "history_discharge": "காதில் சீழ் அல்லது நீர் வடிதல்",
        "history_noise": "அதிக இரைச்சல் சூழலில் வேலை",
        "history_pain": "காது வலி",
        "history_meds": "காது பாதிக்கும் மருந்துகள்",
        
        # Ambient Noise Monitoring
        "ambient_noise": "அறை இரைச்சல் அளவு",
        "noise_measuring": "அறை இரைச்சல் 5 வினாடிகள் அளவிடப்படுகிறது...",
        "noise_acceptable": "அறை இரைச்சல் சரியான அளவில் உள்ளது (< 45 dB SPL)",
        "noise_warning": "எச்சரிக்கை: அறையில் இரைச்சல் அதிகம் (> 45 dB SPL)",
        "noise_blocked": "தடைசெய்யப்பட்டது: மிக அதிக இரைச்சல் (> 55 dB SPL). அமைதியான அறைக்கு மாறவும்.",
        
        # Status & Reliability
        "patient_reliability": "நோயாளி நம்பகத்தன்மை குறியீடு",
        "status_reliable": "நம்பகமானது",
        "status_questionable": "சந்தேகத்திற்குரியது",
        "status_unreliable": "நம்பகமற்றது",
        "pta_calculated": "சராசரி கேட்பு திறன் (PTA)",
        
        # AI Engine
        "run_ai_analysis": "AI நோயியல் பகுப்பாய்வு செய்க",
        "ac_only_banner": "⚠️ காற்று வழி (AC-Only) AI முடிவு — உத்தேசமானது. எலும்பு வழி பரிசோதனை மூலம் உறுதிப்படுத்தவும்.",
        "full_model_banner": "✅ முழுமையான மருத்துவ அறிக்கை (காற்று மற்றும் எலும்பு வழி சரிபார்க்கப்பட்டது)",
        "predicted_pathology": "கண்டறியப்பட்ட குறைபாடு",
        "confidence": "துல்லியம் / நம்பிக்கை அளவு",
        "recommendation": "மருத்துவ பரிந்துரை",
        "class_normal": "இயல்பான கேட்கும் திறன் (Normal)",
        "class_conductive": "கடத்தல் வகை காது கேளாமை (Conductive)",
        "class_sensorineural": "நரம்பு வழி காது கேளாமை (Sensorineural)",
        "class_mixed": "கலப்பு வகை காது கேளாமை (Mixed)",
        "class_uncertain": "தெளிவற்ற நிலை — எலும்பு வழி பரிசோதனை தேவை",
        
        # Patient Instructions
        "instructions_title": "நோயாளிக்கான அறிவுரைகள்",
        "instruction_pure_tone": "உங்கள் காதில் மெல்லிய பீப் ஒலிகள் கேட்கும். மிக மெல்லிய ஒலியாக இருந்தாலும் கேட்டவுடன் பொத்தானை உடனே அழுத்தவும்.",
        "instruction_speech": "ஹெட்போனில் கூறப்படும் சொற்களை கேட்டு தெளிவாக உரக்கக் கூறவும்.",
        
        # Speech Audiometry
        "srt_label": "பேச்சு ஏற்பு வரம்பு (SRT)",
        "wrs_label": "சொல் அறிதல் விகிதம் (WRS)",
        "word_correct": "சரியானது",
        "word_incorrect": "தவறானது",
        
        # Hardware & Export
        "usb_dac_warning": "⚠️ வெளிப்புற USB DAC இணைக்கப்படவில்லை.",
        "bc_unavailable_warning": "⚠️ எலும்பு வழி சாதனம் இல்லை. AC-Only முறை இயக்கப்பட்டது.",
        "export_pdf": "PDF மருத்துவ அறிக்கை தயார் செய்க",
        "export_json": "JSON தரவு சேமிப்பு",
        "export_csv": "CSV ஆராய்ச்சி தரவு",
        "export_fhir": "HL7 FHIR அறிக்கை"
    },
    
    "bn": {
        "app_title": "ক্লিনিক্যাল অডিওমিটার ও এআই প্যাথলজি অ্যানালাইজার",
        "tagline": "হাসপাতাল ও গ্রামীণ স্বাস্থ্যসেবার জন্য উন্নত হিয়ারিং পরীক্ষক",
        "lang_name": "বাংলা (Bengali)",
        
        # Navigation / Panels
        "nav_pure_tone": "পিওর টোন অডিওমেট্রি (PTA)",
        "nav_speech": "স্পিচ অডিওমেট্রি",
        "nav_special": "বিশেষ পরীক্ষা",
        "nav_calibration": "ক্যালিব্রেশন উইজার্ড",
        "nav_ai_analysis": "এআই প্যাথলজি বিশ্লেষণ",
        "nav_reports": "রোগীর রিপোর্ট ও রপ্তানি",
        
        # Test Controls
        "frequency": "কম্পাঙ্ক / ফ্রিকোয়েন্সি (Hz)",
        "intensity": "তীব্রতা (dB HL)",
        "ear": "পরীক্ষার কান",
        "right_ear": "ডান কান (লাল)",
        "left_ear": "বাম কান (নীল)",
        "conduction": "কন্ডাকশনের ধরন",
        "air_conduction": "এয়ার কন্ডাকশন (AC)",
        "bone_conduction": "বোন কন্ডাকশন (BC)",
        "present_tone": "শব্দ শোনান [Space]",
        "store_threshold": "শ্রবণসীমা সংরক্ষণ [Enter]",
        "start_hw": "স্বয়ংক্রিয় হিউগসন-ওয়েস্টলেক",
        "start_bekesy": "অটো বেকেসি ট্র্যাকিং",
        "stop_test": "শব্দ থামান",
        "step_size": "ধাপের পরিমাণ (5 dB / 1 dB)",
        "masking": "মাস্কিং নয়েজ",
        "masking_level": "মাস্কিং মাত্রা (dB HL)",
        "masking_auto": "স্বয়ংক্রিয় মাস্কিং গণনা",
        
        # Patient Info
        "patient_details": "রোগীর তথ্য ও পূর্ববর্তী ইতিহাস",
        "patient_name": "পুরো নাম",
        "patient_id": "রোগী আইডি (MRN)",
        "patient_age": "বয়স",
        "operator": "পরীক্ষক",
        "history_discharge": "কান দিয়ে পুঁজ বা জল পড়ার ইতিহাস",
        "history_noise": "উচ্চ শব্দে কাজ করার ইতিহাস",
        "history_pain": "কানের ব্যথার ইতিহাস",
        "history_meds": "কানের ক্ষতিকারক ওষুধের ইতিহাস",
        
        # Ambient Noise Monitoring
        "ambient_noise": "ঘরের শব্দের মাত্রা",
        "noise_measuring": "ঘরের শব্দ ৫ সেকেন্ড মাপা হচ্ছে...",
        "noise_acceptable": "ঘরের শব্দ স্বাভাবিক (< 45 dB SPL)",
        "noise_warning": "সতর্কতা: ঘরের শব্দ বেশি (> 45 dB SPL)",
        "noise_blocked": "পরীক্ষা বন্ধ: অতিরিক্ত শব্দ (> 55 dB SPL)। শান্ত ঘরে যান।",
        
        # Status & Reliability
        "patient_reliability": "রোগীর সাড়া প্রদানের নির্ভরযোগ্যতা",
        "status_reliable": "নির্ভরযোগ্য",
        "status_questionable": "সন্দেহজনক",
        "status_unreliable": "অনির্ভরযোগ্য",
        "pta_calculated": "গড় শ্রবণ ক্ষমতা (PTA)",
        
        # AI Engine
        "run_ai_analysis": "এআই প্যাথলজি বিশ্লেষণ চালান",
        "ac_only_banner": "⚠️ শুধুমাত্র এয়ার কন্ডাকশন (AC-Only) অনুমান — বোন কন্ডাকশন দিয়ে নিশ্চিত করুন।",
        "full_model_banner": "✅ সম্পূর্ণ ক্লিনিক্যাল বিশ্লেষণ (এয়ার ও বোন উভয়ই যাচাইকৃত)",
        "predicted_pathology": "সম্ভাব্য সমস্যা",
        "confidence": "নির্ভুলতা / আত্মবিশ্বাস",
        "recommendation": "চিকিৎসকের পরামর্শ",
        "class_normal": "স্বাভাবিক শ্রবণ ক্ষমতা (Normal)",
        "class_conductive": "কন্ডাক্টিভ হিয়ারিং লস (Conductive)",
        "class_sensorineural": "সেন্সরিন্যুরাল হিয়ারিং লস (Sensorineural)",
        "class_mixed": "মিক্সড হিয়ারিং লস (Mixed)",
        "class_uncertain": "অনিশ্চিত — বোন কন্ডাকশন পরীক্ষা প্রয়োজন",
        
        # Patient Instructions
        "instructions_title": "রোগীর জন্য নির্দেশাবলী",
        "instruction_pure_tone": "আপনি হেডফোনে হালকা বীপ শব্দ শুনতে পাবেন। খুব মৃদু শব্দ হলেও শোনার সাথে সাথে বোতামটি চাপুন ও ছেড়ে দিন।",
        "instruction_speech": "হেডফোনে বলা শব্দগুলি শুনে স্পষ্ট করে মুখে বলুন।",
        
        # Speech Audiometry
        "srt_label": "স্পিচ রিসেপশন থ্রেশহোল্ড (SRT)",
        "wrs_label": "শব্দ শনাক্তকরণ স্কোর (WRS)",
        "word_correct": "সঠিক",
        "word_incorrect": "ভুল",
        
        # Hardware & Export
        "usb_dac_warning": "⚠️ সতর্কতা: ইউএসবি ডিএসি পাওয়া যায়নি।",
        "bc_unavailable_warning": "⚠️ বোন কন্ডাকশন হার্ডওয়্যার অনুপস্থিত। AC-Only মোড সক্রিয়।",
        "export_pdf": "পিডিএফ ক্লিনিক্যাল রিপোর্ট তৈরি",
        "export_json": "ইএমআর জেএসওএন রপ্তানি",
        "export_csv": "গবেষণা সিএসভি ডেটা",
        "export_fhir": "HL7 FHIR রিপোর্ট"
    }
}


class LocalizationManager:
    """Manages active language selection and translation lookups."""

    def __init__(self, default_lang: str = "en"):
        self.current_lang = default_lang if default_lang in TRANSLATIONS else "en"

    def set_language(self, lang_code: str) -> bool:
        if lang_code in TRANSLATIONS:
            self.current_lang = lang_code
            return True
        return False

    def get(self, key: str, default: Optional[str] = None) -> str:
        lang_dict = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])
        if key in lang_dict:
            return lang_dict[key]
        # Fallback to English
        return TRANSLATIONS["en"].get(key, default or key)

    def get_supported_languages(self) -> Dict[str, str]:
        return {code: trans["lang_name"] for code, trans in TRANSLATIONS.items()}
