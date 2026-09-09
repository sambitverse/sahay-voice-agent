"""
Conversational State Machine for Trauma Voice Agent.
Guides the interaction through structured clinical-safety phases:
GREETING -> PROBLEM_ASSESSMENT -> EMPATHY_GROUNDING -> SUPPORT_VERIFICATION -> ESCALATION_HANDOFF / CONCLUSION

Includes strict Spatial Environment Grounding (Wilderness/Forest vs Indoor)
to prevent inappropriate hallucinations (e.g. telling forest callers to lock doors).
"""

from enum import Enum
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    GREETING = "GREETING"
    PROBLEM_ASSESSMENT = "PROBLEM_ASSESSMENT"
    EMPATHY_GROUNDING = "EMPATHY_GROUNDING"
    SUPPORT_VERIFICATION = "SUPPORT_VERIFICATION"
    ESCALATION_HANDOFF = "ESCALATION_HANDOFF"
    CONCLUSION = "CONCLUSION"


class ConversationStateManager:
    """
    Manages stage progression for each active call session to maintain conversational
    structure and avoid premature escalation or cyclical responses.
    """

    def __init__(self):
        self.session_states: Dict[str, ConversationState] = {}
        self.session_turns: Dict[str, int] = {}

    def get_state(self, call_id: str) -> ConversationState:
        return self.session_states.get(call_id, ConversationState.GREETING)

    def transition(
        self,
        call_id: str,
        risk_level: str,
        turn_count: int,
        requires_escalation: bool
    ) -> ConversationState:
        """
        Determines the next conversation phase based on multi-turn investigative triage.
        Crucial Mandate: The voice agent must first conduct active situational inquiry across
        early turns (Turns 1 to 3) before escalating to a human supervisor or providing closing numbers.
        """
        current = self.get_state(call_id)
        self.session_turns[call_id] = turn_count

        # Turn 1: Always PROBLEM_ASSESSMENT (first inquiry into caller's scenario & physical safety)
        if current == ConversationState.GREETING or turn_count <= 1:
            new_state = ConversationState.PROBLEM_ASSESSMENT
        # Turn 4+: Resolution, Escalation Handoff, or Conclusion
        elif turn_count >= 4 or current == ConversationState.SUPPORT_VERIFICATION:
            if requires_escalation or risk_level in ["CRITICAL", "HIGH"]:
                new_state = ConversationState.ESCALATION_HANDOFF
            else:
                new_state = ConversationState.CONCLUSION
        # Turn 3: SUPPORT_VERIFICATION (statutory rights, legal guidance, immediate needs assessment)
        elif turn_count == 3 or current == ConversationState.EMPATHY_GROUNDING:
            new_state = ConversationState.SUPPORT_VERIFICATION
        # Turn 2: EMPATHY_GROUNDING (deeper scenario probing: perpetrators, injuries, location)
        elif turn_count == 2 or current == ConversationState.PROBLEM_ASSESSMENT:
            new_state = ConversationState.EMPATHY_GROUNDING
        else:
            new_state = current

        self.session_states[call_id] = new_state
        return new_state

    @staticmethod
    def detect_environment(text: str) -> Dict[str, bool]:
        """Detect the caller's physical environment and pursuit state from transcript."""
        t = (text or "").lower()
        is_wilderness = any(w in t for w in [
            "jangala", "bana", "bir", "dongar", "pahar", "nadi", "khet", "jami", "jungle", "forest",
            "ଜଙ୍ଗଲ", "ବଣ", "ପାହାଡ଼", "ନଈ", "ଖେତ", "जंगल", "पहाड़", "नदी", "खेत"
        ])
        is_outdoor_public = any(w in t for w in [
            "rasta", "sadak", "gali", "bata", "bazar", "highway", "road", "dahar",
            "ରାସ୍ତା", "ଗଳି", "ବଜାର", "सड़क", "रास्ता", "गली", "बाजार"
        ])
        is_pursuit = any(w in t for w in [
            "godauchanti", "godauchhan", "godauchhe", "panjayedina", "pache", "chasing",
            "pache padichhanti", "mariba pain", "gojing", "khojuchhanti",
            "ଗୋଡ଼ାଉଛନ୍ତି", "ମାରିବାକୁ ଖୋଜୁଛନ୍ତି", "ଦୌଡ଼ାଉଛନ୍ତି", "दौड़ा रहे", "पीछे पड़े", "जान से मारने"
        ])
        is_indoors = any(w in t for w in [
            "ghara", "ghar", "kothari", "kamra", "room", "house", "orak", "office", "dukan",
            "ଘର", "କୋଠରୀ", "घर", "कमरा"
        ]) and not (is_wilderness or is_pursuit)

        return {
            "wilderness": is_wilderness,
            "outdoor_public": is_outdoor_public,
            "pursuit": is_pursuit,
            "indoors": is_indoors
        }

    def get_system_prompt_for_state(
        self,
        state: ConversationState,
        language_code: str,
        risk_level: str,
        latest_transcript: str = ""
    ) -> str:
        """Returns prompt guidance conditioned on current conversation phase and situational context."""
        lc = (language_code or "or-IN").lower()

        # Language guidance: Odia primary, regional dialects, or Indian English (Zero Hindi)
        if "sp" in lc or "sambalpur" in lc or "kosli" in lc:
            base_lang_instruction = "You MUST speak in natural, empathetic, spoken SAMBALPURI / KOSLI ODIA. Directly address the caller's specific situation."
        elif "sat" in lc or "santali" in lc:
            base_lang_instruction = "You MUST speak in simple, reassuring ODIA or Santali-contact phrasing. Directly address the caller's specific situation."
        elif "des" in lc or "desia" in lc or "koraput" in lc:
            base_lang_instruction = "You MUST speak in natural, empathetic, spoken DESIA / KORAPUT ODIA (or simple reassuring Odia). Directly address the caller's specific situation."
        elif "kui" in lc or "kandha" in lc:
            base_lang_instruction = "You MUST speak in simple, reassuring ODIA with Kandha/Kui contact vocabulary. Directly address the caller's specific situation."
        elif "en" in lc:
            base_lang_instruction = "You MUST speak in natural, empathetic, spoken INDIAN ENGLISH. Directly address the caller's specific problem."
        else:
            base_lang_instruction = "You MUST speak in natural, empathetic, spoken ODIA. Directly address the caller's specific problem."

        # Detect spatial environment from the caller's speech
        env = self.detect_environment(latest_transcript)
        if env["wilderness"] or env["pursuit"]:
            spatial_mandate = (
                "CRITICAL SPATIAL MANDATE — CALLER IS OUTDOORS IN JUNGLE/WILDERNESS OR BEING PURSUED:\n"
                "- ABSOLUTE BAN: NEVER tell the caller to lock house doors, stay in a room, or close windows!\n"
                "- Tell them to stay low, keep phone on SILENT mode, and reassure them emergency police are being alerted."
            )
        else:
            spatial_mandate = ""

        state_guidance = {
            ConversationState.GREETING: (
                "Acknowledge the caller warmly and respectfully. "
                "Ask gently what issue, grievance, or emergency they would like to report today."
            ),
            ConversationState.PROBLEM_ASSESSMENT: (
                "The caller just described their problem or situation. "
                "1. Acknowledge and empathize with their specific situation in ONE short sentence referring directly to the topic they mentioned. "
                "2. ASK ONE DIRECT QUESTION relevant to their specific situation (if an atrocity/threat: check immediate safety/location; if an administrative issue: ask about application/office details; if a dispute: ask about the parties involved). "
                "CRITICAL MANDATE: DO NOT mention transferring to a supervisor. DO NOT recite helpline numbers."
            ),
            ConversationState.EMPATHY_GROUNDING: (
                "The caller answered your previous question. "
                "1. Validate their answer with calm understanding. "
                "2. ASK ONE DIRECT FOLLOW-UP QUESTION to clarify the context (e.g., who is involved, where did it take place, or what assistance is immediately needed). "
                "CRITICAL MANDATE: DO NOT mention transferring to a supervisor yet."
            ),
            ConversationState.SUPPORT_VERIFICATION: (
                "Address the caller's answers and situation directly. "
                "1. If an atrocity or discrimination case: explain concrete legal protection under the SC/ST PoA Act 1989 (Zero FIR, Section 15A protection, free legal aid, interim relief). "
                "2. If an administrative or civil case: provide the exact procedural pathway or grievance redressal procedure. "
                "3. Ask what immediate support they require."
            ),
            ConversationState.ESCALATION_HANDOFF: (
                "The assessment is complete and all case details have been documented into an official dossier. "
                "Calmly inform the caller that you are now connecting them directly to our specialized officer / supervisor on this active line. "
                "DO NOT tell the caller to call any toll-free number. Tell them to stay on the line."
            ),
            ConversationState.CONCLUSION: (
                "The assistance is complete. Provide clear, actionable advice and confirm that their inquiry/grievance has been officially recorded. "
                "DO NOT tell the caller to call any toll-free number."
            )
        }

        guidance = state_guidance.get(state, state_guidance[ConversationState.PROBLEM_ASSESSMENT])
        spatial_section = f"{spatial_mandate}\n\n" if spatial_mandate else ""

        return (
            f"{base_lang_instruction}\n"
            f"Assessed Risk Tier: {risk_level}\n"
            f"Conversation Phase: {state.value}\n\n"
            f"{spatial_section}"
            f"MANDATE — SITUATION & SEVERITY MATCHING (NO DISCONNECTED HALLUCINATIONS):\n"
            f"You are the voice assistant for the National Helpline Against Atrocities (NHAA - 14566) under the Ministry of Social Justice and Empowerment.\n"
            f"You MUST analyze the caller's actual words and dynamically adapt your response to their exact situation:\n"
            f"1. CATEGORY 1: CRITICAL EMERGENCY (Immediate physical attack, weapons, severe bleeding, ongoing mob violence):\n"
            f"   - Prioritize physical safety directives (e.g. lock doors if indoors, or stay hidden if outdoors).\n"
            f"   - Keep response calm, urgent, and concise. State that emergency police/medical units are being coordinated right now.\n"
            f"2. CATEGORY 2: CASTE ATROCITY / DISCRIMINATION / SOCIAL BOYCOTT / HARASSMENT:\n"
            f"   - Situations of caste abuse, eviction, boycott ('samaja ru bahiskara', denial of water), threats ('dhamki'), police refusal to register FIR.\n"
            f"   - Validate their pain empathetically with direct reference to their specific incident.\n"
            f"   - Ask focused investigative questions about the perpetrators, location, and injuries.\n"
            f"   - Inform them of their rights under the SC/ST (PoA) Act (Zero FIR, Section 15A witness/victim protection, free legal aid).\n"
            f"3. CATEGORY 3: CIVIL DISPUTE / PROPERTY / FAMILY / NEIGHBORHOOD CONFLICT:\n"
            f"   - Inquire specifically about the dispute facts, location, and relevant authorities.\n"
            f"   - DO NOT assume violence or ask if they are in fear of their life unless they mentioned it.\n"
            f"4. CATEGORY 4: ADMINISTRATIVE / WELFARE / SCHEME INQUIRIES (Scholarships, voter card, pension, certificates, helpline queries):\n"
            f"   - Provide clear, direct, polite informational assistance regarding the scheme, application, or office procedure.\n"
            f"   - STRICT BAN: DO NOT ask 'Are you in a safe place?' or 'Are you terrified?' for administrative queries.\n\n"
            f"PHASE OBJECTIVE:\n{guidance}\n\n"
            f"CONVERSATIONAL RULES:\n"
            f"1. DIRECT RELEVANCE: Your response MUST explicitly mention and address the specific issue the caller spoke about.\n"
            f"2. EARLY TURNS (Turns 1-3): Focus on understanding the caller's situation through active, targeted questions. DO NOT transfer to supervisor or recite phone numbers yet.\n"
            f"3. LATER TURNS (Turn 4+): Provide concrete assistance or state that a supervisor transfer is being completed directly on this call.\n"
            f"4. NO TOLL-FREE NUMBERS: NEVER tell the caller to dial 14566 or 112 because they are already on this active call!\n"
            f"5. ANTI-REPETITION: Never repeat boilerplate phrases like 'daya kari bhaya karantu nahi' or 'surakshita sthana re achhanti ki' if already said or inappropriate.\n"
            f"6. SPOKEN SPEECH ONLY: No markdown formatting (**bold**, # headers, bullet points). Maximum 18 to 22 words (1 to 2 crisp, compassionate sentences). Keep it brief, natural, and immediate for voice conversation."
        )

    @classmethod
    def get_fallback_phrase(
        cls,
        language_code: Any = "or-IN",
        state: Any = ConversationState.PROBLEM_ASSESSMENT,
        latest_transcript: str = "",
        *args,
        **kwargs
    ) -> str:
        """
        Provide safe, conversational fallback phrases if LLM call is delayed, dynamically adapted to caller situation.
        Accepts both:
          1. (language_code, state, latest_transcript)
          2. (language_code="or-IN", state=..., latest_transcript=...)
          3. (risk_level, language_code, text)
        """
        # Resolve argument variations
        if isinstance(language_code, str) and language_code.upper() in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            lang = str(state or "or-IN").lower()
            conv_state = ConversationState.PROBLEM_ASSESSMENT
            transcript = latest_transcript or (args[0] if args else "")
        elif isinstance(state, ConversationState):
            lang = str(language_code or "or-IN").lower()
            conv_state = state
            transcript = latest_transcript
        elif isinstance(state, str) and any(c in state.lower() for c in ("or", "en", "sp", "des")):
            lang = state.lower()
            conv_state = ConversationState.PROBLEM_ASSESSMENT
            transcript = latest_transcript or ""
        else:
            lang = str(language_code or "or-IN").lower()
            conv_state = state if isinstance(state, ConversationState) else ConversationState.PROBLEM_ASSESSMENT
            transcript = latest_transcript

        env = cls.detect_environment(transcript)
        t = (transcript or "").lower()

        # 1. Outdoors / Jungle / Wilderness Pursuit
        if env["wilderness"] or env["pursuit"]:
            if "en" in lang:
                return "Please stay quiet, silence your phone, and remain hidden in the bushes. Can you whisper any nearby landmark or road? Emergency police are being dispatched."
            else:
                return "Apan shanta ruhantu, phone silent karantu o jangala re nuchiki ruhantu. Pakhare kounasi rasta ba landmark achhi ki? Police ku suchana diajauchi."

        # 2. Physical Assault / Home Break-in / Severe Injury / Weapons
        is_assault = any(w in t for w in [
            "lathi", "maruchhanti", "pituchhanti", "pitile", "mada", "marpit", "ghare dhuki", "ghare pasi",
            "rakta", "matha phatigala", "churi", "talwar", "marideba", "dalan", "dohpa", "marba",
            "peet rahe", "mar rahe", "khoon", "beating", "attack", "bleeding", "injured",
            "ପିଟୁଛନ୍ତି", "ମାରୁଛନ୍ତି", "ଲାଠି", "ରକ୍ତ", "ଘରେ ପଶି"
        ])
        if is_assault:
            if "en" in lang:
                return "I understand your crisis. Please stay safe, emergency police PCR 112 and medical support are being dispatched to you right now. Please tell your location."
            else:
                return "Mu apananka katha bujhili. Daya kari niraapadare rahantu, aame turanta police PCR 112 o medical team pathauchu. Apananka ghara pakha landmark kuhan tu."

        # 3. Police Arrival / Dispatch Inquiry
        is_police_inquiry = any(w in t for w in [
            "police dak", "police ku pathao", "police pathantu", "police kebe asiba", "police kab aayegi",
            "help pathantu", "help bhejo", "madad bhejo", "send police", "police ku dakantu",
            "ପୋଲିସ", "ଡାକନ୍ତୁ", "ପଠାନ୍ତୁ"
        ])
        if is_police_inquiry:
            if "en" in lang:
                return "Police 112 has been alerted immediately and emergency response is en route to you. Please keep your phone close and stay safe."
            else:
                return "Police 112 ku turanta suchana diajaichhi, police gadi apananka ade baharigalaani. Apan phone paakhare rakhantu o surakshita sthana re rahantu."

        # 4. Caste Discrimination / Social Boycott / Drinking Water Denial
        is_boycott = any(w in t for w in [
            "pani band", "pani mana", "pani nebaku mana", "samaja ru bahiskara", "samaja bahiskara",
            "gaon ru khedi", "khedi dele", "jati gali", "boycott", "tube well", "dak nu mana",
            "ato khon ko orok", "ବାସନ୍ଦ", "ପାଣି ବନ୍ଦ", "ସାମାଜିକ ବାସନ୍ଦ"
        ])
        if is_boycott:
            if "en" in lang:
                return "Social boycott and denial of drinking water are serious offenses under the PoA Act. We are notifying district authorities and legal aid immediately."
            else:
                return "Saamajika baasanda o pani band kariba aieen anusare gurutara aparadha. Aame zilla prashasana o DLSA legal aid ku suchana deuchhu, apananku poora surakshya miliba."

        # 5. General Phase-based Conversational Support
        if "en" in lang:
            if conv_state == ConversationState.PROBLEM_ASSESSMENT:
                return "I hear you clearly. Are you currently in a safe location, and is anyone with you right now?"
            elif conv_state == ConversationState.EMPATHY_GROUNDING:
                return "Please take a deep breath, I understand. Where did this incident happen, and who is threatening you?"
            elif conv_state == ConversationState.SUPPORT_VERIFICATION:
                return "You have full legal protection and rights under the law. Do you require immediate police intervention or medical care?"
            elif conv_state == ConversationState.ESCALATION_HANDOFF:
                return "All details of your situation have been recorded. I am now connecting you directly to our supervisor on this line. Please stay on the line."
            else:
                return "Your grievance has been officially registered. Our response team will coordinate action immediately."
        else:
            # Odia default
            if conv_state == ConversationState.PROBLEM_ASSESSMENT:
                return "Mu apananka katha suni paruchhi. Apan ebe surakshita sthana re achhanti ki? Daya kari kuhan tu apananka paakhare kie achhanti."
            elif conv_state == ConversationState.EMPATHY_GROUNDING:
                return "Apan byasta huantu nahi, mu apananka katha bujhiparuchhi. Ehi ghatana ti kouthi ghatila, ebong kie apananku dhamaka deuchhanti?"
            elif conv_state == ConversationState.SUPPORT_VERIFICATION:
                return "Apananku aieen gata poora surakshya o sahajya miliba. Apananku bartaman medical sahajya na police sahajya darkar?"
            elif conv_state == ConversationState.ESCALATION_HANDOFF:
                return "Apananka samasta bibarani o abhijoga record karaigala. Mu bartaman amara supervisor nku ehi call re sidhasalakh connect karuchhi, line re rahantu."
            else:
                return "Apananka abhijoga darja karaigala. Amara team ehi bishayare karzyanushthana grahana karibe, apan nishchinta rahantu."
