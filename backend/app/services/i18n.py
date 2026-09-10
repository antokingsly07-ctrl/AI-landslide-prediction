"""Multilingual alert template library.

Uses predefined, verified message templates (NOT uncontrolled AI text) translated
into supported languages by key. This is a safety requirement for emergency messages.
"""
SUPPORTED_LANGUAGES = ["en", "hi", "as", "bn", "ta"]

RISK_LEVEL_LABELS = {
    "VERY_LOW": {"en": "Very Low", "hi": "अत्यंत कम", "as": "অতি কম", "bn": "খুব কম", "ta": "மிக குறைவு"},
    "LOW": {"en": "Low", "hi": "कम", "as": "কম", "bn": "কম", "ta": "குறைவு"},
    "MODERATE": {"en": "Moderate", "hi": "मध्यम", "as": "মধ্যম", "bn": "মাঝারি", "ta": "மிதமான"},
    "HIGH": {"en": "High", "hi": "उच्च", "as": "উচ্চ", "bn": "উচ্চ", "ta": "அதிகம்"},
    "CRITICAL": {"en": "Critical", "hi": "गंभीर", "as": "গুৰুত্বপূৰ্ণ", "bn": "গুরুতর", "ta": "முக்கியமான"},
}

SEVERITY_LABELS = {
    "advisory": {"en": "Advisory", "hi": "सलाह", "as": "পৰামৰ্শ", "bn": "পরামর্শ", "ta": "ஆலோசனை"},
    "watch": {"en": "Watch", "hi": "निगरानी", "as": "নিৰীক্ষণ", "bn": "নজরদারি", "ta": "கண்காணிப்பு"},
    "warning": {"en": "Warning", "hi": "चेतावनी", "as": "সতৰ্কবাণী", "bn": "সতর্কতা", "ta": "எச்சரிக்கை"},
    "critical": {"en": "Critical", "hi": "गंभीर", "as": "গুৰুত্বপূৰ্ণ", "bn": "গুরুতর", "ta": "முக்கியமான"},
}

# Generic templates used for all alerts; values interpolated from structured data.
TEMPLATES = {
    "risk_title": {
        "en": "Landslide Risk {severity}: {level}",
        "hi": "भूस्खलन जोखिम {severity}: {level}",
        "as": "ভূমিক্ষয়ৰ বিপদ {severity}: {level}",
        "bn": "ভূমিধস ঝুঁকি {severity}: {level}",
        "ta": "நிலச்சரிவு ஆபத்து {severity}: {level}",
    },
    "risk_message": {
        "en": "A {level} landslide risk has been detected near {location} ({risk_score}/100). {action}",
        "hi": "{location} के पास {level} भूस्खलन जोखिम पाया गया है ({risk_score}/100)। {action}",
        "as": "{location} কাষত {level} ভূমিক্ষয়ৰ বিপদ ধৰা পৰিছে ({risk_score}/100)। {action}",
        "bn": "{location} এর কাছে {level} ভূমিধস ঝুঁকি সনাক্ত হয়েছে ({risk_score}/100)। {action}",
        "ta": "{location} அருகே {level} நிலச்சரிவு ஆபத்து கண்டறியப்பட்டது ({risk_score}/100). {action}",
    },
    "rainfall_title": {
        "en": "Heavy Rainfall Alert",
        "hi": "भारी बारिश अलर्ट",
        "as": "প্ৰবল বৰষুণৰ সতৰ্কবাণী",
        "bn": "প্রবল বৃষ্টিপাত সতর্কতা",
        "ta": "கனமழை எச்சரிக்கை",
    },
    "rainfall_message": {
        "en": "Heavy rainfall ({rain} mm/24h) recorded at {location}. Risk of flooding and slope failure.",
        "hi": "{location} पर भारी बारिश ({rain} मिमी/24घंटे) दर्ज की गई। बाढ़ और ढलान विफलता का जोखिम।",
        "as": "{location} ত প্ৰবল বৰষুণ ({rain} মিমি/২৪ঘণ্টা) ৰেকৰ্ড হৈছে।",
        "bn": "{location} এ ভারী বৃষ্টিপাত ({rain} মিমি/২৪ঘণ্টা) রেকর্ড হয়েছে।",
        "ta": "{location} இல் கனமழை ({rain} மிமீ/24மணி) பதிவானது.",
    },
    "sensor_anomaly_title": {
        "en": "Sensor Anomaly Detected",
        "hi": "सेंसर विसंगति का पता चला",
        "as": "চেন্সৰ অসমতা ধৰা পৰিল",
        "bn": "সেন্সর অসঙ্গতি সনাক্ত",
        "ta": "சென்சார் முரண்பாடு கண்டறியப்பட்டது",
    },
    "sensor_anomaly_message": {
        "en": "Anomalous reading from sensor {sensor} ({type}): {value} {unit}. Possible ground movement.",
        "hi": "सेंसर {sensor} से असामान्य रीडिंग ({type}): {value} {unit}। संभावित जमीनी हलचल।",
        "as": "চেন্সৰ {sensor} ৰ পৰা অস্বাভাৱিক পঠন ({type}): {value} {unit}।",
        "bn": "সেন্সর {sensor} থেকে অস্বাভাবিক রিডিং ({type}): {value} {unit}।",
        "ta": "சென்சார் {sensor} இலிருந்து அசாதாரண அளவீடு ({type}): {value} {unit}.",
    },
    "report_title": {
        "en": "Confirmed Field Report: {type}",
        "hi": "पुष्टि की गई फील्ड रिपोर्ट: {type}",
        "as": "নিশ্চিত ফিল্ড ৰিপৰ্ট: {type}",
        "bn": "নিশ্চিত ফিল্ড রিপোর্ট: {type}",
        "ta": "உறுதிப்படுத்தப்பட்ட கள அறிக்கை: {type}",
    },
    "report_message": {
        "en": "A {severity} severity {type} event has been reported at {location}.",
        "hi": "{location} पर {severity} गंभीरता का {type} प्रकरण रिपोर्ट किया गया।",
        "as": "{location} ত {severity} গুৰুত্বৰ {type} পৰিঘটনা ৰিপৰ্ট হৈছে।",
        "bn": "{location} এ {severity} তীব্রতার {type} ঘটনা রিপোর্ট করা হয়েছে।",
        "ta": "{location} இல் {severity} தீவிர {type} நிகழ்வு பதிவு செய்யப்பட்டது.",
    },
    "road_title": {
        "en": "Road Status Changed: {road}",
        "hi": "सड़क स्थिति बदली: {road}",
        "as": "পথৰ অৱস্থা সলনি: {road}",
        "bn": "রাস্তার অবস্থা পরিবর্তন: {road}",
        "ta": "சாலை நிலை மாற்றம்: {road}",
    },
    "road_message": {
        "en": "Road {road} is now {status}.",
        "hi": "सड़क {road} अब {status} है।",
        "as": "পথ {road} এতিয়া {status}।",
        "bn": "রাস্তা {road} এখন {status}।",
        "ta": "சாலை {road} இப்போது {status}.",
    },
}

ROAD_STATUS_LABELS = {
    "open": {"en": "Open", "hi": "खुला", "as": "খোলা", "bn": "খোলা", "ta": "திறந்தது"},
    "restricted": {"en": "Restricted", "hi": "प्रतिबंधित", "as": "নিষিদ্ধ", "bn": "সীমাবদ্ধ", "ta": "கட்டுப்படுத்தப்பட்டது"},
    "blocked": {"en": "Blocked", "hi": "अवरुद्ध", "as": "অবৰুদ্ধ", "bn": "অবরুদ্ধ", "ta": "மூடப்பட்டது"},
    "severely_blocked": {"en": "Severely Blocked", "hi": "गंभीर रूप से अवरुद्ध", "as": "গুৰুত্বপূৰ্ণভাৱে অবৰুদ্ধ", "bn": "গুরুতরভাবে অবরুদ্ধ", "ta": "கடுமையாக மூடப்பட்டது"},
    "unknown": {"en": "Unknown", "hi": "अज्ञात", "as": "অজ্ঞাত", "bn": "অজানা", "ta": "தெரியவில்லை"},
}


def translate(key: str, lang: str = "en", **kwargs) -> str:
    """Render a predefined template for a language, filling structured values."""
    lang = lang if lang in SUPPORTED_LANGUAGES else "en"
    template_map = TEMPLATES.get(key, {})
    template = template_map.get(lang) or template_map.get("en", "")
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def supported_languages() -> list[str]:
    return SUPPORTED_LANGUAGES
