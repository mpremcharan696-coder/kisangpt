"""
voice_chatbot.py
================
Bilingual AI Conversational Engine for KrishiMitra AI.
Generates 2 replies:
1. One in English (stored in variable `english_reply`)
2. One in Kannada (stored in variable `kannada_reply`)

Enforces single speaking language lock until the farmer explicitly asks for a change.
Connects with Groq LLM (openai/gpt-oss-120b) with guaranteed JSON output,
manages context, extracts farmer memory, and prevents raw JSON leaks.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
from groq import Groq

import chatbot_db as cdb

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "openai/gpt-oss-120b"

_client: Optional[Groq] = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=API_KEY)
    return _client


def detect_language_change_request(user_message: str) -> Optional[str]:
    """
    Detect if the farmer explicitly requests a language change.
    Returns 'English' or 'Kannada' if detected, else None.
    """
    t = user_message.lower().strip()
    
    # Standalone exact language selection
    if t in ["english", "english language", "english please", "ಇಂಗ್ಲಿಷ್"]:
        return "English"
    if t in ["kannada", "kannada language", "kannada please", "ಕನ್ನಡ", "ಕನ್ನಡ ಭಾಷೆ"]:
        return "Kannada"

    # English trigger phrases
    if any(p in t for p in [
        "speak in english", "talk in english", "switch to english",
        "change language to english", "in english", "english please",
        "use english", "only english", "answer in english", "tell me in english",
        "prefer english", "choose english", "i want english", "i prefer english",
        "i speak english", "reply in english"
    ]):
        return "English"

    # Kannada trigger phrases
    if any(p in t for p in [
        "speak in kannada", "talk in kannada", "switch to kannada",
        "change language to kannada", "in kannada", "kannada please",
        "use kannada", "only kannada", "answer in kannada", "tell me in kannada",
        "prefer kannada", "choose kannada", "i want kannada", "i prefer kannada",
        "i speak kannada", "reply in kannada",
        "ಕನ್ನಡದಲ್ಲಿ", "ಕನ್ನಡ ಬಳಸಿ", "ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಿ", "ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ", "ಕನ್ನಡ ಮಾತಾಡಿ"
    ]):
        return "Kannada"

    return None



def _clean_json_response(raw_text: str) -> Dict[str, Any]:
    """
    Extract and validate clean English and Kannada replies from LLM text.
    Strictly guarantees that raw JSON syntax never leaks into reply strings.
    """
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]

    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        try:
            # Fix trailing commas or control characters
            text_fixed = re.sub(r",\s*([\]}])", r"\1", text)
            parsed = json.loads(text_fixed)
        except Exception:
            pass

    if not isinstance(parsed, dict):
        parsed = {}

    english_val = parsed.get("english_reply")
    kannada_val = parsed.get("kannada_reply")

    # If parsing failed or string contains raw JSON fragments, extract via regex
    if not english_val or not isinstance(english_val, str) or '{"english_reply"' in str(english_val) or '"kannada_reply"' in str(english_val):
        en_match = re.search(r'"english_reply"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_text, re.DOTALL)
        if en_match:
            try:
                english_val = json.loads('"' + en_match.group(1) + '"')
            except Exception:
                english_val = en_match.group(1)
        else:
            english_val = ""

    if not kannada_val or not isinstance(kannada_val, str) or '{"english_reply"' in str(kannada_val) or '"kannada_reply"' in str(kannada_val):
        kn_match = re.search(r'"kannada_reply"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_text, re.DOTALL)
        if kn_match:
            try:
                kannada_val = json.loads('"' + kn_match.group(1) + '"')
            except Exception:
                kannada_val = kn_match.group(1)
        else:
            kannada_val = ""

    # Sanitize strings: strip any stray JSON artifacts
    def _strip_json_artifacts(s: str) -> str:
        if not s:
            return ""
        s = re.sub(r'^\s*\{\s*"english_reply"\s*:\s*"?', '', str(s))
        s = re.sub(r'^\s*\{\s*"kannada_reply"\s*:\s*"?', '', s)
        s = re.sub(r'"?,\s*"kannada_reply".*$', '', s, flags=re.DOTALL)
        s = re.sub(r'"?,\s*"english_reply".*$', '', s, flags=re.DOTALL)
        s = re.sub(r'["\}]+$', '', s)
        return s.strip().strip('"').strip("'")

    clean_en = _strip_json_artifacts(str(english_val))
    clean_kn = _strip_json_artifacts(str(kannada_val))

    if not clean_en:
        clean_en = "I am here to guide you with your farming and crop questions."
    if not clean_kn:
        clean_kn = "ನಾನು ನಿಮ್ಮ ಕೃಷಿ ಮತ್ತು ಬೆಳೆಗಳ ಬಗ್ಗೆ ಮಾರ್ಗದರ್ಶನ ನೀಡಲು ಇಲ್ಲಿದ್ದೇನೆ."

    visual_aid = parsed.get("visual_aid") if isinstance(parsed.get("visual_aid"), dict) else {}

    return {
        "english_reply": clean_en,
        "kannada_reply": clean_kn,
        "intent": parsed.get("intent", "general"),
        "extracted_memory": parsed.get("extracted_memory") if isinstance(parsed.get("extracted_memory"), dict) else {},
        "visual_aid": visual_aid
    }


SYSTEM_PROMPT = """
You are 'KrishiMitra AI' (ಕೃಷಿಮಿತ್ರ AI), a warm, supportive, and knowledgeable digital farming assistant for Indian farmers, especially in Karnataka.
You have two primary duties:
1. Communicate fluently with farmers about agriculture: what crops they grow, seed varieties, package of practices, fertilizer application, irrigation, pest management, weather, and cultivation budgets.
2. ALWAYS generate TWO distinct replies for every farmer turn:
   - One reply in ENGLISH ('english_reply') containing only clean English text (plain conversational sentences, NO JSON).
   - One reply in KANNADA ('kannada_reply') containing only clean Kannada text in Kannada script (ಕನ್ನಡ) (NO JSON).

3. PICTORIAL / VISUAL AID DETERMINATION:
   Determine whether a picture is necessary to help the farmer easily understand:
   - Set "needs_visual": true ONLY when explaining:
     * Crop pest, insect, or leaf disease symptoms (e.g. blast, blight, caterpillar damage).
     * Sowing line spacing or planting distance (e.g. row-to-row, plant-to-plant).
     * Method of fertilizer application or spraying technique.
     * Crop maturity and harvesting signs.
   - Set "needs_visual": false for greetings, language switches, general budgets, or simple conversational confirmations.

Your response must strictly be valid JSON in this exact structure:
{
  "english_reply": "Clear, friendly, conversational response in English. Keep it concise (2-4 sentences) so it sounds natural when spoken aloud. DO NOT include Kannada or JSON inside this field.",
  "kannada_reply": "ನೈಸರ್ಗಿಕ ಕನ್ನಡದಲ್ಲಿ ಸ್ಪಷ್ಟ ಮತ್ತು ಸ್ನೇಹಪರ ಉತ್ತರ (2-4 ವಾಕ್ಯಗಳು). ಧ್ವನಿಯಲ್ಲಿ ಕೇಳಲು ಸುಲಭವಾಗಿರಬೇಕು. ಈ ಭಾಗದಲ್ಲಿ ಇಂಗ್ಲಿಷ್ ಅಥವಾ JSON ಇರಬಾರದು.",
  "intent": "greeting | crop_inquiry | language_selection | budget_inquiry | task_inquiry | general",
  "extracted_memory": {
    "farmer_name": null or extracted name,
    "preferred_language": "Kannada" or "English",
    "crop": null or crop mentioned,
    "acres": null or acres mentioned,
    "district": null or district mentioned,
    "irrigation": null or irrigation mentioned
  },
  "visual_aid": {
    "needs_visual": true or false,
    "image_prompt": "Clear photorealistic photo prompt (e.g. 'Close-up of Ragi leaf blast spindle brown spots on green foliage, Indian farm context')",
    "caption_kannada": "ಚಿತ್ರ: ರಾಗಿ ಬೆಳೆಯ ಎಲೆಗಳಲ್ಲಿ ಬೆಂಕಿ ರೋಗದ ಲಕ್ಷಣಗಳು",
    "caption_english": "Visual: Blast disease symptoms on finger millet leaves"
  }
}

Guidelines:
- If the farmer states or picks a language, note it in extracted_memory.
- If the farmer says what crop they grow (e.g. Ragi, Maize, Cotton, Tur, Sugarcane), acknowledge it encouragingly and ask if they need guidance on practices, sowing calendar, or budget.
- If the farmer needs help selecting a crop, ask about their land size or soil type to guide them.
- Keep spoken text easy to understand for rural farmers.
- Return ONLY the JSON object.
"""


def generate_onboarding_turn(session_id: str) -> Dict[str, Any]:
    """
    Generate initial greeting turn when user lands on site.
    Generates 2 replies: one in English and other in Kannada, stored in respective variables.
    Defaults to Kannada speaking language until the user requests otherwise.
    """
    # 1. English reply stored in variable english_reply
    english_reply: str = (
        "Namaskara! I am KrishiMitra AI, your personal farming decision assistant. "
        "Which language would you prefer to talk in: Kannada or English? "
        "And tell me, what crop do you grow on your farm, or do you need help in selecting the right crop?"
    )

    # 2. Kannada reply stored in variable kannada_reply
    kannada_reply: str = (
        "ನಮಸ್ಕಾರ! ನಾನು ಕೃಷಿಮಿತ್ರ AI, ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಕೃಷಿ ಸಲಹೆಗಾರ. "
        "ನೀವು ಯಾವ ಭಾಷೆಯಲ್ಲಿ ಮಾತನಾಡಲು ಇಷ್ಟಪಡುತ್ತೀರಿ: ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್? "
        "ಮತ್ತು ನಿಮ್ಮ ಹೊಲದಲ್ಲಿ ನೀವು ಯಾವ ಬೆಳೆ ಬೆಳೆಯುತ್ತಿದ್ದೀರಿ, ಅಥವಾ ಹೊಸ ಬೆಳೆ ಆಯ್ಕೆ ಮಾಡಲು ನಿಮಗೆ ಸಹಾಯ ಬೇಕೇ?"
    )

    # By default, lock speaking language to Kannada
    active_speaking_language: str = "Kannada"

    cdb.create_or_get_session(session_id, preferred_language=active_speaking_language)
    cdb.save_farmer_memory(session_id, "preferred_language", active_speaking_language)
    cdb.save_message_turn(
        session_id=session_id,
        sender="bot",
        kannada_reply=kannada_reply,
        english_reply=english_reply,
        intent="onboarding"
    )

    return {
        "status": "success",
        "session_id": session_id,
        "english_reply": english_reply,
        "kannada_reply": kannada_reply,
        "intent": "onboarding",
        "active_speaking_language": active_speaking_language,
        "extracted_memory": {
            "preferred_language": active_speaking_language,
            "onboarding_completed": False
        }
    }


def generate_bilingual_reply(
    user_message: str,
    session_id: str,
    preferred_language: str = "Kannada"
) -> Dict[str, Any]:
    """
    Process user input, query LLM, generate 2 replies (one in English, other in Kannada),
    store them in respective variables, update conversational memory, and enforce
    single speaking language until the farmer explicitly asks for a change.
    """
    # Retrieve existing session memory to see currently locked speaking language
    existing_memory = cdb.get_all_farmer_memory(session_id)
    current_locked_lang = existing_memory.get("preferred_language", preferred_language or "Kannada")

    # Check if current user message requests a language change
    explicit_lang_change = detect_language_change_request(user_message)
    if explicit_lang_change:
        active_speaking_language = explicit_lang_change
    else:
        # KEEP THE EXISTING LANGUAGE LOCKED UNTIL EXPLICITLY CHANGED
        active_speaking_language = current_locked_lang

    cdb.create_or_get_session(session_id, preferred_language=active_speaking_language)
    cdb.save_farmer_memory(session_id, "preferred_language", active_speaking_language)
    cdb.update_session(session_id, preferred_language=active_speaking_language)

    # Save user message
    cdb.save_message_turn(
        session_id=session_id,
        sender="user",
        kannada_reply=user_message,
        english_reply=user_message,
        intent="user_input"
    )

    # Retrieve existing conversation history
    history = cdb.get_chat_history(session_id, limit=8)

    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Provide memory context to LLM
    memory_context = (
        f"Active Farmer Memory: {json.dumps(existing_memory)}\n"
        f"Current Speaking Language: {active_speaking_language}"
    )
    messages.append({"role": "system", "content": memory_context})

    # Add past turns
    for turn in history[:-1]:  # Exclude latest user turn already added
        if turn["sender"] == "user":
            messages.append({"role": "user", "content": turn["english_reply"] or turn["kannada_reply"] or ""})
        elif turn["sender"] == "bot":
            bot_text = json.dumps({
                "english_reply": turn["english_reply"],
                "kannada_reply": turn["kannada_reply"]
            })
            messages.append({"role": "assistant", "content": bot_text})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # Query LLM with forced JSON response format and ample tokens
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        raw_content = response.choices[0].message.content or "{}"
        parsed = _clean_json_response(raw_content)
    except Exception as err:
        print(f"[Groq Chatbot Error] {err}")
        # Robust fallback dual replies
        parsed = {
            "english_reply": "Thank you for sharing. Could you tell me more about your farm and what crop you are cultivating?",
            "kannada_reply": "ಧನ್ಯವಾದಗಳು! ನಿಮ್ಮ ಹೊಲ ಮತ್ತು ನೀವು ಯಾವ ಬೆಳೆ ಬೆಳೆಯುತ್ತಿದ್ದೀರಿ ಎಂಬುದರ ಬಗ್ಗೆ ಇನ್ನಷ್ಟು ಹೇಳಬಹುದೇ?",
            "intent": "fallback",
            "extracted_memory": {}
        }

    # Store 2 replies in respective variables without mixing
    english_reply: str = parsed.get("english_reply") or "I am here to help you with your crops."
    kannada_reply: str = parsed.get("kannada_reply") or "ನಾನು ನಿಮ್ಮ ಬೆಳೆಗಳ ಬಗ್ಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿದ್ದೇನೆ."
    intent: str = parsed.get("intent", "general")
    extracted_memory: Dict[str, Any] = parsed.get("extracted_memory") or {}

    # Update SQLite farmer memory for any detected facts
    for key, val in extracted_memory.items():
        if val is not None and str(val).strip():
            # If LLM detected a language in memory, respect it if user explicitly requested it
            if key == "preferred_language" and explicit_lang_change:
                cdb.save_farmer_memory(session_id, key, active_speaking_language)
            elif key != "preferred_language":
                cdb.save_farmer_memory(session_id, key, val)

    # Check if a visual aid is required and generate it
    visual_aid_data = None
    raw_visual = parsed.get("visual_aid")
    if isinstance(raw_visual, dict) and raw_visual.get("needs_visual") and raw_visual.get("image_prompt"):
        try:
            import hf_image_service as hf_svc
            img_res = hf_svc.generate_agricultural_visual(raw_visual["image_prompt"])
            if img_res.get("status") == "success":
                visual_aid_data = {
                    "image_url": img_res.get("image_url"),
                    "image_base64": img_res.get("image_base64"),
                    "caption_kannada": raw_visual.get("caption_kannada", "ಚಿತ್ರ: ಕೃಷಿ ಮಾಹಿತಿ"),
                    "caption_english": raw_visual.get("caption_english", "Visual: Agricultural guidance"),
                    "provider": img_res.get("provider")
                }
        except Exception as img_err:
            print(f"[Visual Aid Generation Error] {img_err}")

    # Persist the bot's turn with both replies stored in their respective columns
    cdb.save_message_turn(
        session_id=session_id,
        sender="bot",
        kannada_reply=kannada_reply,
        english_reply=english_reply,
        intent=intent
    )

    return {
        "status": "success",
        "session_id": session_id,
        "english_reply": english_reply,
        "kannada_reply": kannada_reply,
        "intent": intent,
        "active_speaking_language": active_speaking_language,
        "extracted_memory": extracted_memory,
        "total_memory": cdb.get_all_farmer_memory(session_id),
        "visual_aid": visual_aid_data
    }
