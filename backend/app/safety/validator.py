import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class SafetyValidator:
    """
    Post-generation guardrail ensuring LLM responses are safe, factual, and legally defensible.
    Blocks hallucinated numbers, clinical diagnoses, false promises, and victim blaming.
    """

    # Approved official helplines (never blocked or sanitized)
    APPROVED_NUMBERS = {"14566", "112", "108", "14416", "1098", "1930", "181", "100", "101", "102"}

    # Whitelisted statutory years and legal act dates
    WHITELISTED_YEARS = {str(y) for y in range(1947, 2035)}

    # Map Indic native digits (Odia and Devanagari) to ASCII 0-9
    INDIC_DIGIT_MAP = str.maketrans("୦୧୨୩୪୫୬୭୮୯०१२३४५६७८९", "01234567890123456789")

    PROHIBITED_DIAGNOSES = [
        "you have ptsd", "diagnose you with", "clinical depression",
        "psychiatric illness", "you have trauma disorder", "you are suffering from mental illness"
    ]

    VICTIM_BLAMING = [
        "your fault", "why did you go there", "why didn't you avoid",
        "you should have obeyed", "you caused this"
    ]

    FALSE_PROMISES = [
        "i guarantee the police will arrest", "i promise you will get compensation",
        "i promise everything will be fixed today"
    ]

    OUT_OF_SCOPE_PATTERNS = [
        # Coding & Software Engineering
        r"\b(?:python|javascript|typescript|java|c\+\+|html|css|react|angular|vue|django|flask|spring boot)\b",
        r"\b(?:write\s+(?:a\s+)?code|coding|function|variable|algorithm|debugging|compiler|sql\s+query|database\s+schema)\b",
        r"\b(?:write\s+(?:a\s+)?script|programming|binary\s+search|data\s+structure)\b",
        r"(?:କୋଡିଂ|କୋଡ୍|ପ୍ରୋଗ୍ରାମିଂ|ସଫ୍ଟୱେର୍|ଡିବଗ୍|ପାଇଥନ୍)",
        # Sports, Gaming, Cinema & Entertainment
        r"\b(?:cricket|ipl|football|fifa|messi|ronaldo|virat\s+kohli|world\s+cup|match\s+score)\b",
        r"\b(?:cinema|movie|actor|actress|bollywood|hollywood|box\s+office|song\s+lyrics)\b",
        r"(?:କ୍ରିକେଟ|ଫୁଟବଲ|ମ୍ୟାଚ୍|ସିନେମା|ଗୀତ|ଚଳଚ୍ଚିତ୍ର)",
        # Trivia, Weather, Stock market, Crypto, Recipes
        r"\b(?:bitcoin|cryptocurrency|stock\s+market|share\s+price|trading\s+tips)\b",
        r"\b(?:weather\s+forecast|temperature\s+today|rain\s+forecast|panipaga)\b",
        r"(?:ପାଣିପାଗ|ତାପମାତ୍ରା|ବିଟକଏନ|ଶେୟାର\s+ବଜାର)",
        r"\b(?:recipe\s+for|how\s+to\s+cook|biryani\s+recipe|joke|funny\s+story|riddle)\b",
        r"(?:ରୋଷେଇ|ରେସିପି|ଚୁଟକୁଲା|ମଜାଳିଆ\s+ଗପ|କୌତୁକ)",
        r"\b(?:solve\s+this\s+math|homework|write\s+(?:an?\s+)?essay|who\s+is\s+the\s+president\s+of)\b"
    ]

    OUT_OF_SCOPE_RESPONSES = {
        "or": "ଏହା ଜାତୀୟ ହେଲ୍ପଲାଇନ୍ ୧୪୫୬୬ (14566 - National Helpline Against Atrocities) ଅଟେ। ଆମେ କେବଳ ଅତ୍ୟାଚାର, ଭେଦଭାବ, ଜରୁରୀକାଳୀନ ସୁରକ୍ଷା ଓ ଆଇନଗତ ସହାୟତା ପାଇଁ କାର୍ଯ୍ୟ କରୁଛୁ। ଏହି ପ୍ରଶ୍ନ ଆମ କାର୍ଯ୍ୟ ପରିସର ବାହାରେ ଅଟେ।",
        "en": "This is the National Helpline Against Atrocities (14566). We provide assistance strictly for atrocities, caste discrimination, emergency safety, and statutory victim rights. We cannot answer out-of-scope inquiries."
    }

    SAFE_FALLBACKS = {
        "or": "Namaskar. Apan ebe surakshita achhanti ki? Apananka surakhya amara prathama kartavya. Daya kari kuhan tu ame kemiti sahajya kariparibu.",
        "en": "Hello. Are you currently in a safe place? Your immediate safety is our priority. Please let us know how we can support you."
    }

    @classmethod
    def is_out_of_scope(cls, text: str) -> bool:
        """Determines if a caller message or query is completely unrelated to helpline scope."""
        if not text or not text.strip():
            return False
        
        lower = text.lower()
        
        # Check if text contains genuine emergency/grievance/helpline keywords
        in_scope_override_keywords = [
            "help", "sahayata", "sahajya", "madad", "police", "fir", "atrocity", "dhamki",
            "threat", "marba", "marideba", "dar", "bhaya", "banchao", "bachao", "boycott",
            "bahiskara", "panchayat", "hospital", "doctor", "attack", "lathi", "churi",
            "14566", "112", "sc/st", "caste", "discrimination", "shikayat", "complaint",
            "ଗୋଡ଼ାଉଛନ୍ତି", "ମାରିବା", "ପୋଲିସ", "ସାହାଯ୍ୟ", "ବାସନ୍ଦ", "ଜଙ୍ଗଲ", "ଅତ୍ୟାଚାର"
        ]
        if any(kw in lower for kw in in_scope_override_keywords):
            is_overt_coding = any(p in lower for p in ["write code", "write a python", "write python", "coding", "debug this function"])
            if not is_overt_coding:
                return False

        for pattern in cls.OUT_OF_SCOPE_PATTERNS:
            if re.search(pattern, lower, re.IGNORECASE):
                return True
        return False

    @classmethod
    def validate(cls, text: str, language_code: str = "or", caller_transcript: str = "") -> Tuple[str, bool]:
        """
        Validate generated text.
        Returns: (safe_text, is_clean)
        """
        lower = text.lower()
        validated_text = text

        # 0. Check if caller query was out of scope
        if caller_transcript and cls.is_out_of_scope(caller_transcript):
            lang_key = "en" if "en" in language_code.lower() else "or"
            logger.warning(f"[SafetyValidator] Out-of-scope query blocked from caller transcript: {caller_transcript[:50]}")
            return cls.OUT_OF_SCOPE_RESPONSES.get(lang_key, cls.OUT_OF_SCOPE_RESPONSES["en"]), False

        # Check if generated response is answering out of scope topics
        if cls.is_out_of_scope(text):
            lang_key = "en" if "en" in language_code.lower() else "or"
            logger.warning(f"[SafetyValidator] Out-of-scope response generation intercepted: {text[:50]}")
            return cls.OUT_OF_SCOPE_RESPONSES.get(lang_key, cls.OUT_OF_SCOPE_RESPONSES["en"]), False

        # 1. Check for prohibited medical/clinical diagnosis
        for diag in cls.PROHIBITED_DIAGNOSES:
            if diag in lower:
                logger.warning(f"[SafetyValidator] Inappropriate clinical diagnosis blocked: {diag}")
                fallback = cls.SAFE_FALLBACKS.get(language_code, cls.SAFE_FALLBACKS["en"])
                return fallback, False

        # 2. Check for victim blaming phrases
        for blame in cls.VICTIM_BLAMING:
            if blame in lower:
                logger.warning(f"[SafetyValidator] Victim blaming language blocked: {blame}")
                fallback = cls.SAFE_FALLBACKS.get(language_code, cls.SAFE_FALLBACKS["en"])
                return fallback, False

        # 3. Check for false guarantees/promises
        for promise in cls.FALSE_PROMISES:
            if promise in lower:
                logger.warning(f"[SafetyValidator] False legal/police promise blocked: {promise}")
                fallback = cls.SAFE_FALLBACKS.get(language_code, cls.SAFE_FALLBACKS["en"])
                return fallback, False

        # 4. Check for outdoor / wilderness spatial hallucination
        ct_lower = (caller_transcript or "").lower()
        is_wilderness_call = any(w in ct_lower for w in [
            "jangala", "bana", "bir", "dongar", "pahar", "nadi", "khet", "jungle", "forest",
            "godauchanti", "godauchhan", "panjayedina", "ଜଙ୍ଗଲ", "ବଣ", "ଗୋଡ଼ାଉଛନ୍ତି"
        ])
        if is_wilderness_call:
            for indoor_term in ["kabata band", "darwaza band", "ghara bhitare", "kamre", "lock the door", "lock door", "କବାଟ ବନ୍ଦ", "ଦରୱାଜା ବନ୍ଦ", "ଘର ଭିତରେ"]:
                if indoor_term in lower:
                    logger.warning(f"[SafetyValidator] Spatial hallucination blocked: indoor term '{indoor_term}' during wilderness scenario.")
                    if "en" in language_code.lower():
                        return "Please stay calm, silence your phone, and remain hidden in the trees. Emergency police are being alerted.", False
                    else:
                        return "Apan shanta ruhantu, phone silent karantu o jangala re nuchiki ruhantu. Police ku turant suchana diajauchi.", False

        has_sanitized_number = False
        potential_phones = re.findall(r'(?:\+91[\-\s]?)?[6-9]\d{9}\b|\b0\d{2,4}[-\s]?\d{6,8}\b|\b\d{3,6}\b|[୦-୯]{3,6}|[०-९]{3,6}', validated_text)
        for token in potential_phones:
            normalized_token = token.translate(cls.INDIC_DIGIT_MAP)
            clean_digits = re.sub(r'\D', '', normalized_token)
            # Check if this token is an approved helpline
            if clean_digits in cls.APPROVED_NUMBERS:
                continue
            # Check if this is a statutory act year (e.g. 1989, 1995, 2015)
            if clean_digits in cls.WHITELISTED_YEARS:
                continue
            # Check if small number (< 3 digits) or valid legal section reference
            if len(clean_digits) < 3 or len(clean_digits) > 12:
                continue

            # If it's a 10-digit mobile or unknown 3-6 digit shortcode not in approved helplines:
            logger.warning(f"[SafetyValidator] Unauthorized number sanitized in-place: {token} -> 14566")
            validated_text = re.sub(r'\b' + re.escape(token) + r'\b', '14566', validated_text)
            has_sanitized_number = True

        if has_sanitized_number:
            return validated_text, False

        return validated_text, True
