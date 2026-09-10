"""
Multilingual Language Router and Dialect Normalization Bridge.
Handles core languages (Odia, English)
plus native Odia tribal and regional varieties (Sambalpuri/Kosli, Santali, Desia, Kui).
"""

import re
import logging
from enum import Enum
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SupportedLanguage(str, Enum):
    ODIA = "or-IN"
    ENGLISH = "en-IN"
    SAMBALPURI = "sp-IN"
    SANTALI = "sat-IN"
    DESIA = "des-IN"
    KUI = "kui-IN"
    UNKNOWN = "unknown"


class DialectBridge:
    """
    Normalizes tribal and regional dialect expressions into standard base language
    to ensure high-precision NLU and verified legal RAG retrieval.
    """

    # Sambalpuri (Kosli) -> Standard Odia lexical mappings
    SAMBALPURI_TO_ODIA = {
        r"\bkanje\b": "kahinki",
        r"\bkana\b": "kana",
        r"\btor\b": "tora",
        r"\bmor\b": "mora",
        r"\bmor pache\b": "mo pache",
        r"\bgodauchhan\b": "godauchhanti",
        r"\bgodauchhe\b": "godauchhi",
        r"\bhanta\b": "seti",
        r"\benta\b": "eithi",
        r"\bkahe\b": "kahuchhi",
        r"\bdeuchhe\b": "deuchhi",
        r"\bkarchhe\b": "karuchhi",
        r"\bmarba\b": "marideba",
        r"\bkhaye\b": "khauchi",
        r"\bpile\b": "pila",
        r"\bdada\b": "bhai",
        r"\bhuchhe\b": "heuchhi",
        r"\bbana\b": "jangala",
        r"\bdongar\b": "pahar",
        r"\bnuchi achhe\b": "nuchiki achhi",
        r"\bkhedi dele\b": "bahiskara kale",
        r"\bpani mana\b": "pani nebaku mana",
        r"\bgaon ru\b": "gan ru",
        r"\bdada banchao\b": "bhai banchantu",
        r"\bghare dhuki\b": "ghara bhitaraku pasi",
        r"\bpila ke\b": "shishu ku"
    }

    # Santali (Tribal indigenous language in Odisha) -> Standard Odia mappings
    SANTALI_TO_ODIA = {
        r"\bbir re ukanakana\b": "jangala re nuchiki achhi",
        r"\bpanjayedina\b": "godauchhanti",
        r"\bgojing lagid\b": "mariba pain",
        r"\bdalan kanako\b": "maruchhanti",
        r"\bbotor ge aikawkana\b": "bahut bhaya laguchhi",
        r"\bbanchaoing pe\b": "mote banchantu",
        r"\bdak nu mana\b": "pani peeba mana",
        r"\bato khon ko orok\b": "gan ru bahiskara",
        r"\bpolice hohoako\b": "police ku dakantu",
        r"\bkapi\b": "talwar",
        r"\bhasiyara\b": "churi",
        r"\bthonga\b": "lathi",
        r"\bgidra\b": "pila",
        r"\borak\b": "ghara",
        r"\bdahar\b": "rasta"
    }

    # Desia (Southern Odisha tribal dialect - Koraput, Malkangiri, Nabarangpur) -> Odia
    DESIA_TO_ODIA = {
        r"\bmor pache padila\b": "mo pache padichhi",
        r"\bmor pache\b": "mo pache",
        r"\bgodauche\b": "godauchhi",
        r"\bgodauchhan\b": "godauchhanti",
        r"\bbhay laguche\b": "bhaya laguchhi",
        r"\bpani mana\b": "pani nebaku mana",
        r"\bkhedi delu\b": "bahiskara kale",
        r"\bkhedi dele\b": "bahiskara kale",
        r"\bmarba\b": "marideba",
        r"\bmarbar\b": "marideba",
        r"\bmui\b": "mu",
        r"\bmuke\b": "mate",
        r"\bkoruche\b": "karuchi",
        r"\bkoruchhan\b": "karuchhanti",
        r"\bhoiche\b": "heichi",
        r"\bdelan\b": "dele",
        r"\bbhatar\b": "swami",
        r"\blagin\b": "pain",
        r"\bjhoruche\b": "bohuchi",
        r"\bthakibake\b": "rahibaku",
        r"\bbanchaa\b": "banchantu",
        r"\bpathaa\b": "pathantu",
        r"\bmor banchao\b": "mote banchantu",
        r"\bdada banchao\b": "bhai banchantu",
        r"\bdada\b": "bhai",
        r"\bghare dhukila\b": "ghara bhitaraku pasi",
        r"\bkaha sunba nahi\b": "kehi sununahanti",
        r"\bpadili\b": "padichi",
        r"\bjaiba\b": "jiba",
        r"\bkarba\b": "kariba",
        r"\bkhaye\b": "khauchi",
        r"\bdongar\b": "pahar",
        r"\bdongor\b": "pahar",
        r"\bbana\b": "jangala",
        r"\bmora ke\b": "mote",
        r"\btora ke\b": "tote",
        r"\bchua ke\b": "pila ku",
        r"\bpila ke\b": "pila ku"
    }

    # Kui (Kandha indigenous tribal language) -> Odia
    KUI_TO_ODIA = {
        r"\baanu\b": "mu",
        r"\baane\b": "mate",
        r"\baanki\b": "mate",
        r"\baahe\b": "nahi",
        r"\bgida\b": "pila",
        r"\bmira\b": "pila",
        r"\bmera\b": "ghara",
        r"\biddu\b": "ghara",
        r"\bhaji\b": "rasta",
        r"\bgahi\b": "bhaya",
        r"\bbiiti\b": "bhaya",
        r"\bvespa\b": "kahiba",
        r"\bnaju\b": "gan",
        r"\bdaha\b": "pani",
        r"\bbana\b": "jangala",
        r"\bmara\b": "jangala",
        r"\bdohpa\b": "mariba",
        r"\bhavba\b": "mariba",
        r"\bpidisenji\b": "maruchanti",
        r"\bpitisenji\b": "maruchanti",
        r"\bsaaha\b": "sahajya",
        r"\bkidu\b": "karantu",
        r"\blohe\b": "darkar",
        r"\bpacha\b": "pache",
        r"\bpoyatu\b": "pathantu"
    }

    # Broken and colloquial Odia telegraphic phrasing
    COLLOQUIAL_BROKEN_ODIA_PATTERNS = {
        r"\bmo jana\b": "mu jane",
        r"\bmate dar\b": "mate bhaya laguchi",
        r"\bchua mari\b": "pila ku maruchanti",
        r"\bpani nai\b": "pani miluni",
        r"\bbata nai\b": "rasta nahi",
        r"\bghara bhanga\b": "ghara bhangi dele",
        r"\bse marba\b": "se marideba",
        r"\bmada khauchu\b": "maru pita karuchanti",
        r"\bbachao dada\b": "bhai banchantu",
        r"\bpolice dak\b": "police ku dakantu",
        r"\blathi mada\b": "lathi re maruchanti",
        r"\bjati gali\b": "jati nei gali deuchhanti",
        r"\bgharu kadhi\b": "gharu bahari dele",
        r"\bpani band\b": "pani band karidele",
        r"\bdana band\b": "khadya band karidele",
        r"\bgrama bahara\b": "gan ru bahiskara"
    }

    @classmethod
    def normalize_dialect(cls, text: str, source_dialect: str) -> str:
        """Normalize regional dialect terms and broken colloquial terms into standard form for semantic processing."""
        if not text:
            return ""
        normalized = text
        if source_dialect in [SupportedLanguage.SAMBALPURI, "sp-IN", "sambalpuri"]:
            for pattern, replacement in cls.SAMBALPURI_TO_ODIA.items():
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        elif source_dialect in [SupportedLanguage.SANTALI, "sat-IN", "santali"]:
            for pattern, replacement in cls.SANTALI_TO_ODIA.items():
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        elif source_dialect in [SupportedLanguage.DESIA, "des-IN", "desia"]:
            for pattern, replacement in cls.DESIA_TO_ODIA.items():
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        elif source_dialect in [SupportedLanguage.KUI, "kui-IN", "kui"]:
            for pattern, replacement in cls.KUI_TO_ODIA.items():
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # Apply broken colloquial Odia normalization across Odia & regional tribal dialects
        for pattern, replacement in cls.COLLOQUIAL_BROKEN_ODIA_PATTERNS.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        return normalized


class LanguageRouter:
    """
    Dynamic Language Identification, Routing, and Session Continuity Manager.
    """

    # Unicode script ranges
    ODIA_SCRIPT_RANGE = re.compile(r"[\u0b00-\u0b7f]")
    HINDI_SCRIPT_RANGE = re.compile(r"[\u0900-\u097f]")
    OL_CHIKI_SCRIPT_RANGE = re.compile(r"[\u1c50-\u1c7f]")

    # Phonetic transliterated keywords for romanized input
    ODIA_PHONETIC_MARKERS = {
        "mu", "mate", "mora", "mor", "tume", "apan", "apananka", "achhi", "achhanti",
        "nahi", "katha", "darichhi", "dhamaka", "sahajya", "marideba", "bhanguchhanti",
        "ghara", "lathi", "police", "thana", "gali", "atiyachara", "marpit", "jangala", "godauchanti"
    }

    HINDI_PHONETIC_MARKERS = {
        "main", "mujhe", "mera", "meri", "mere", "aap", "aapka", "hai", "hain", "nahi",
        "madad", "bachao", "police", "kripya", "thana", "shikayat", "darj", "surakshit",
        "chinta", "rahein", "bolo", "bataiye", "namaste", "dhanyawad"
    }

    SAMBALPURI_PHONETIC_MARKERS = {
        "kanje", "godauchhan", "godauchhe", "marba", "deuchhe", "karchhe", "mor", "tor",
        "hanta", "enta", "dongar", "bana", "nuchi", "khedi", "pita", "khata", "aichhe", "aichhan"
    }

    DESIA_PHONETIC_MARKERS = {
        "godauche", "laguche", "sunba", "dhukila", "padila", "mor", "banchao", "khedi", "delu",
        "dada", "ghare", "dongar", "dongor", "marba", "marbar", "mui", "muke", "koruche", "koruchhan",
        "hoiche", "delan", "bhatar", "jhoruche", "thakibake", "padili", "jaiba", "karba"
    }

    KUI_PHONETIC_MARKERS = {
        "aanu", "aane", "aanki", "gida", "mera", "haji", "gahi", "biiti", "vespa", "naju", "iddu", "daha",
        "mira", "dohpa", "havba", "pidisenji", "pitisenji", "saaha", "kidu", "lohe", "pacha", "poyatu"
    }

    SANTALI_PHONETIC_MARKERS = {
        "ukanakana", "panjayedina", "gojing", "dalan", "botor", "aikawkana", "banchaoing",
        "hohoako", "orok", "menakana", "gidra", "orak", "dahar", "kapi", "hasiyara"
    }

    def __init__(self, default_language: SupportedLanguage = SupportedLanguage.ODIA):
        self.default_language = default_language
        self.session_languages: Dict[str, Tuple[SupportedLanguage, float]] = {}

    def detect_language_from_text(self, text: str) -> Tuple[SupportedLanguage, float]:
        """
        Detects primary language from raw text using native script ranges
        and phonetic markers for romanized Indian English/code-switching.
        """
        if not text or not text.strip():
            return self.default_language, 0.50

        # 1. Native script detection (Highest confidence)
        odia_chars = len(self.ODIA_SCRIPT_RANGE.findall(text))
        ol_chiki_chars = len(self.OL_CHIKI_SCRIPT_RANGE.findall(text))

        # Check Ol Chiki first for Santali
        if ol_chiki_chars > 0:
            return SupportedLanguage.SANTALI, 0.99

        if odia_chars > 0:
            # If Odia script, check if specific Kosli/Sambalpuri keywords are present
            text_lower = text.lower()
            if any(w in text_lower for w in ["ଗୋଡ଼ାଉଛନ", "ମାର୍ବା", "ନୁଚି", "ଖେଡି", "ଦଙ୍ଗର", "କନ୍ଜେ"]):
                return SupportedLanguage.SAMBALPURI, 0.95
            return SupportedLanguage.ODIA, 0.98


        # 2. Phonetic romanized lexical detection (Code-mixed / Romanized transcripts)
        words = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        if not words:
            return self.default_language, 0.50

        # Check tribal and regional dialect phonetic markers
        santali_matches = len(words.intersection(self.SANTALI_PHONETIC_MARKERS))
        kui_matches = len(words.intersection(self.KUI_PHONETIC_MARKERS))
        desia_matches = len(words.intersection(self.DESIA_PHONETIC_MARKERS))
        sambalpuri_matches = len(words.intersection(self.SAMBALPURI_PHONETIC_MARKERS))
        odia_matches = len(words.intersection(self.ODIA_PHONETIC_MARKERS))
        hindi_matches = len(words.intersection(self.HINDI_PHONETIC_MARKERS))

        if santali_matches > 0 and santali_matches >= max(sambalpuri_matches, desia_matches, kui_matches, odia_matches, hindi_matches):
            conf = min(0.70 + (santali_matches * 0.10), 0.98)
            return SupportedLanguage.SANTALI, conf

        if kui_matches > 0 and kui_matches >= max(sambalpuri_matches, desia_matches, odia_matches, hindi_matches):
            conf = min(0.70 + (kui_matches * 0.10), 0.98)
            return SupportedLanguage.KUI, conf

        if desia_matches > 0 and desia_matches >= max(sambalpuri_matches, odia_matches):
            conf = min(0.70 + (desia_matches * 0.10), 0.98)
            return SupportedLanguage.DESIA, conf

        if sambalpuri_matches > 0 and sambalpuri_matches >= odia_matches:
            conf = min(0.70 + (sambalpuri_matches * 0.10), 0.98)
            return SupportedLanguage.SAMBALPURI, conf

        if odia_matches > 0:
            conf = min(0.60 + (odia_matches * 0.10), 0.95)
            return SupportedLanguage.ODIA, conf

        # 3. Default to English if predominantly Latin alphabet without Indic phonetic markers
        return SupportedLanguage.ENGLISH, 0.70

    def update_session_language(
        self,
        call_id: str,
        detected_lang: str,
        confidence: float
    ) -> SupportedLanguage:
        """
        Updates the session's active language with hysteresis to prevent rapid flickering.
        """
        normalized_lang = self.normalize_language_code(detected_lang)
        current_lang, current_conf = self.session_languages.get(
            call_id, (self.default_language, 0.50)
        )

        # Allow immediate switch if current is UNKNOWN or initial confidence is solid
        if confidence >= 0.75 or current_lang == SupportedLanguage.UNKNOWN:
            self.session_languages[call_id] = (normalized_lang, confidence)
            return normalized_lang

        return current_lang

    def set_session_language(self, call_id: str, lang: str) -> SupportedLanguage:
        """Manually override or lock session language."""
        normalized = self.normalize_language_code(lang)
        self.session_languages[call_id] = (normalized, 1.0)
        return normalized

    def get_session_language(self, call_id: str) -> SupportedLanguage:
        """Retrieve current established session language."""
        return self.session_languages.get(call_id, (self.default_language, 0.50))[0]

    def resolve_language(
        self,
        call_id: str,
        transcript: str,
        stt_detected_lang: Optional[str] = None,
        language_hint: Optional[str] = None
    ) -> SupportedLanguage:
        """
        Resolves the caller language by prioritizing manual hints,
        analyzing text transcript, evaluating STT confidence, and applying session hysteresis.
        """
        if language_hint and language_hint.lower() not in ["auto", "unknown"]:
            return self.set_session_language(call_id, language_hint)

        detected_lang, text_conf = self.detect_language_from_text(transcript)

        if text_conf >= 0.80:
            return self.update_session_language(call_id, detected_lang.value, text_conf)

        if stt_detected_lang and stt_detected_lang.lower() not in ["auto", "unknown", "und"]:
            return self.update_session_language(call_id, stt_detected_lang, 0.70)

        return self.update_session_language(call_id, detected_lang.value, text_conf)

    @staticmethod
    def normalize_language_code(code: str) -> SupportedLanguage:
        """Maps diverse provider language codes to standard enum."""
        if not code:
            return SupportedLanguage.ODIA
        c = code.lower().strip()
        if "sp" in c or "sambalpur" in c or "kosli" in c:
            return SupportedLanguage.SAMBALPURI
        if "sat" in c or "santali" in c:
            return SupportedLanguage.SANTALI
        if "des" in c or "desia" in c or "koraput" in c:
            return SupportedLanguage.DESIA
        if "kui" in c or "kandha" in c:
            return SupportedLanguage.KUI
        if "or" in c or "odi" in c or "od-" in c:
            return SupportedLanguage.ODIA
        if "en" in c or "eng" in c:
            return SupportedLanguage.ENGLISH
        if "unknown" in c or "und" in c:
            return SupportedLanguage.UNKNOWN
        return SupportedLanguage.ODIA

