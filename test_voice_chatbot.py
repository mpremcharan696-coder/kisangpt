"""
test_voice_chatbot.py
======================
Unit tests for the 1-to-1 Interactive Bilingual Voice Chatbot and Sarvam AI voice engine.
Verifies that 2 separate replies (one in English, one in Kannada) are generated, stored
in respective variables, and persisted into SQLite memory.
"""

import json
import unittest
from app import create_app
import chatbot_db as cdb
import voice_chatbot as vc
import sarvam_voice as sv


class TestVoiceChatbot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flask_app = create_app({"TESTING": True})
        cls.client = cls.flask_app.test_client()
        cdb.init_chat_tables()

    def test_speakers_list_endpoint(self):
        """Verify available Sarvam AI speakers list endpoint."""
        res = self.client.get("/api/voice/speakers")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("speakers", data)
        speaker_ids = [s["id"] for s in data["speakers"]]
        self.assertIn("kavya", speaker_ids)
        self.assertIn("aditya", speaker_ids)

    def test_onboarding_turn_generates_two_replies(self):
        """Verifies onboarding generates dual English and Kannada replies stored in respective variables."""
        session_id = "test_onboarding_sess_1"
        res = vc.generate_onboarding_turn(session_id)
        self.assertEqual(res["status"], "success")
        
        # Verify English reply variable
        english_reply = res["english_reply"]
        self.assertIsInstance(english_reply, str)
        self.assertIn("KrishiMitra", english_reply)
        self.assertIn("Kannada", english_reply)

        # Verify Kannada reply variable
        kannada_reply = res["kannada_reply"]
        self.assertIsInstance(kannada_reply, str)
        self.assertIn("ಕೃಷಿಮಿತ್ರ", kannada_reply)
        self.assertIn("ಕನ್ನಡ", kannada_reply)

    def test_api_chat_onboarding_endpoint(self):
        """Verifies POST /api/chat/onboarding endpoint."""
        res = self.client.post("/api/chat/onboarding", json={
            "session_id": "test_api_onboarding_sess",
            "voice_speaker": "kavya",
            "voice_pace": 1.0
        })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("english_reply", data)
        self.assertIn("kannada_reply", data)
        self.assertGreater(len(data["english_reply"]), 10)
        self.assertGreater(len(data["kannada_reply"]), 10)

    def test_bilingual_chat_message_endpoint(self):
        """Verifies POST /api/chat/message returns dual replies and updates memory."""
        session_id = "test_chat_msg_sess"
        user_message = "I cultivate Maize and Ragi on 4 acres in Dharwad"
        
        res = self.client.post("/api/chat/message", json={
            "session_id": session_id,
            "message": user_message,
            "preferred_language": "Both",
            "voice_speaker": "arvind",
            "voice_pace": 1.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        
        # Both respective replies must be populated
        self.assertTrue(len(data["english_reply"]) > 0)
        self.assertTrue(len(data["kannada_reply"]) > 0)
        
        # Verify history is saved in SQLite
        history_res = self.client.get(f"/api/chat/history?session_id={session_id}")
        self.assertEqual(history_res.status_code, 200)
        history_data = history_res.get_json()
        self.assertGreaterEqual(len(history_data["history"]), 2)

    def test_sqlite_chat_memory_persistence(self):
        """Verifies conversational memory persistence in schemes_dev.db."""
        session_id = "test_memory_sess"
        cdb.save_farmer_memory(session_id, "crop", "Sugarcane")
        cdb.save_farmer_memory(session_id, "acres", 5.0)
        cdb.save_farmer_memory(session_id, "district", "Mandya")

        mem = cdb.get_all_farmer_memory(session_id)
        self.assertEqual(mem.get("crop"), "Sugarcane")
        self.assertEqual(mem.get("acres"), 5.0)
        self.assertEqual(mem.get("district"), "Mandya")

    def test_speaking_language_lock_until_change(self):
        """Verifies that the bot speaks in strictly 1 language until the user explicitly asks for a change."""
        session_id = "test_lang_lock_sess_99"

        # 1. Onboarding sets locked speaking language to Kannada by default
        onboarding = vc.generate_onboarding_turn(session_id)
        self.assertEqual(onboarding["active_speaking_language"], "Kannada")

        # 2. General message should NOT change the speaking language (remains Kannada)
        turn1 = vc.generate_bilingual_reply(
            user_message="I cultivate groundnut on 3 acres",
            session_id=session_id
        )
        self.assertEqual(turn1["active_speaking_language"], "Kannada")

        # 3. User explicitly requests English: should switch to English
        turn2 = vc.generate_bilingual_reply(
            user_message="Please speak in English",
            session_id=session_id
        )
        self.assertEqual(turn2["active_speaking_language"], "English")

        # 4. Next conversational question without language instruction: stays locked to English!
        turn3 = vc.generate_bilingual_reply(
            user_message="How much fertilizer do I need?",
            session_id=session_id
        )
        self.assertEqual(turn3["active_speaking_language"], "English")

    def test_replies_stored_separately_without_mixing(self):
        """Verifies that english_reply and kannada_reply are stored separately with no JSON leak."""
        import uuid
        session_id = f"test_separate_replies_{uuid.uuid4().hex[:8]}"
        cdb.save_message_turn(
            session_id=session_id,
            sender="bot",
            kannada_reply="ನಮಸ್ಕಾರ! ನಿಮ್ಮ ರಾಗಿ ಬೆಳೆಗೆ ನೀರು ಹಾಯಿಸಲು ಇದು ಉತ್ತಮ ಸಮಯ.",
            english_reply="Namaskara! This is a good time to irrigate your finger millet crop.",
            intent="irrigation"
        )

        history = cdb.get_chat_history(session_id)
        self.assertGreaterEqual(len(history), 1)
        record = history[-1]

        # Respective columns check
        self.assertEqual(record["english_reply"], "Namaskara! This is a good time to irrigate your finger millet crop.")
        self.assertEqual(record["kannada_reply"], "ನಮಸ್ಕಾರ! ನಿಮ್ಮ ರಾಗಿ ಬೆಳೆಗೆ ನೀರು ಹಾಯಿಸಲು ಇದು ಉತ್ತಮ ಸಮಯ.")

        # Ensure neither column contains raw JSON or braces
        for col in ["english_reply", "kannada_reply"]:
            val = record[col]
            self.assertNotIn('{"english_reply"', val)
            self.assertNotIn('{"kannada_reply"', val)
            self.assertFalse(val.startswith("{"))
            self.assertFalse(val.endswith("}"))

    def test_free_agricultural_visual_generation(self):
        """Verifies zero-cost high-definition agricultural pictorial generation."""
        import hf_image_service as hf_svc
        res = hf_svc.generate_agricultural_visual("finger millet leaf blast symptoms")
        self.assertEqual(res["status"], "success")
        self.assertIn(res["provider"], ["free_visual_engine", "huggingface", "direct_url"])
        self.assertTrue(bool(res.get("image_url")))


if __name__ == "__main__":
    unittest.main()

