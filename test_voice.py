"""
Unit and Integration Tests for Voice Recording & Speech Response Feature
Tests Speech-to-Text, Text-to-Speech (gTTS & pyttsx3 fallback),
Voice Intent Understanding, and Flask Voice API Endpoints.
"""

import io
import wave
import struct
import base64
import pytest
from app import app
from voice_service import (
    generate_audio_speech,
    transcribe_audio_file,
    process_voice_command,
    is_arabic_text,
    formulate_screening_speech_response
)


def create_dummy_wav_bytes(duration_sec: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Helper to create a valid 16-bit PCM WAV in memory."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        num_samples = int(duration_sec * sample_rate)
        # Write silence / low amplitude wave
        samples = [struct.pack("<h", 0) for _ in range(num_samples)]
        wf.writeframes(b"".join(samples))
    buf.seek(0)
    return buf.read()


class TestVoiceServiceUnit:
    def test_is_arabic_text_detection(self):
        """Verify Arabic script detection."""
        assert is_arabic_text("افرز السير الذاتية") is True
        assert is_arabic_text("Hello screening candidates") is False
        assert is_arabic_text("Mix عربي and English") is True

    def test_generate_audio_speech_english(self):
        """Verify speech synthesis for English text produces valid base64 audio."""
        text = "Screening complete! Mazen is the top candidate with a 92% match."
        res = generate_audio_speech(text, language="en")
        assert res["success"] is True
        assert res["audio_base64"].startswith("data:audio/")
        assert len(res["audio_base64"]) > 1000
        assert res["text"] == text

    def test_generate_audio_speech_arabic(self):
        """Verify speech synthesis for Arabic text produces valid base64 audio."""
        text = "تم الفرز بنجاح وأفضل مرشح هو مازن بنسبة توافق عالية."
        res = generate_audio_speech(text, language="ar")
        assert res["success"] is True
        assert res["audio_base64"].startswith("data:audio/")
        assert len(res["audio_base64"]) > 1000

    def test_generate_audio_speech_empty_text_fallback(self):
        """Verify empty string is safely handled with a friendly default."""
        res = generate_audio_speech("", language="en")
        assert res["success"] is True
        assert len(res["audio_base64"]) > 500

    def test_formulate_screening_speech_response(self):
        """Verify concise spoken evaluation is formulated from screening results."""
        job = "Python developer with scikit-learn, SQL, and Docker."
        candidates = {
            "Piyush": "Python developer with scikit-learn, SQL, and Docker experience.",
            "Tippsy": "Frontend developer with HTML and CSS."
        }
        speech_text, detailed = formulate_screening_speech_response(job, candidates)
        assert len(detailed) == 2
        assert detailed[0]["name"] == "Piyush"
        assert "Piyush" in speech_text
        assert "Screening complete" in speech_text or "top ranked" in speech_text

    def test_process_voice_command_screen_intent(self):
        """Verify voice command 'screen candidates' triggers screening action."""
        job = "Python SQL Docker developer"
        candidates = {
            "Alice": "Python SQL Docker engineer",
            "Bob": "Graphic designer"
        }
        res = process_voice_command(
            fallback_text="Please screen the candidates and rank them",
            current_job_desc=job,
            current_candidates=candidates
        )
        assert res["success"] is True
        assert res["action"] == "screen"
        assert "ranked" in res["action_data"]
        assert res["audio_base64"] is not None
        assert "Alice" in res["response_text"]

    def test_process_voice_command_load_preset(self):
        """Verify voice command to load a preset triggers load_preset action."""
        res = process_voice_command(fallback_text="Load Data Engineer preset")
        assert res["success"] is True
        assert res["action"] == "load_preset"
        assert res["action_data"]["preset_id"] == "data-engineer"
        assert res["audio_base64"] is not None

    def test_process_voice_command_update_job(self):
        """Verify voice dictation of job requirements triggers update_job action."""
        job_spoken = "Looking for Senior React developer proficient with TypeScript and Tailwind CSS"
        res = process_voice_command(fallback_text=job_spoken)
        assert res["success"] is True
        assert res["action"] == "update_job"
        assert "React" in res["action_data"]["job_description"]
        assert res["audio_base64"] is not None

    def test_transcribe_audio_file_safe_handling(self):
        """Verify audio file reading doesn't raise unhandled exceptions on silence."""
        wav_bytes = create_dummy_wav_bytes(0.3)
        res = transcribe_audio_file(wav_bytes)
        # With silence, success may be False with friendly error, but must not crash
        assert isinstance(res, dict)
        assert "success" in res


class TestVoiceApiIntegration:
    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_api_voice_speak_success(self, client):
        """Test POST /api/voice/speak returns generated base64 audio response."""
        res = client.post("/api/voice/speak", json={
            "text": "Hello, testing the speech response endpoint.",
            "language": "en"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "audio_base64" in data
        assert data["audio_base64"].startswith("data:audio/")

    def test_api_voice_speak_missing_text(self, client):
        """Test POST /api/voice/speak returns 400 when text is empty."""
        res = client.post("/api/voice/speak", json={"text": ""})
        assert res.status_code == 400
        data = res.get_json()
        assert data["success"] is False

    def test_api_voice_interact_with_text_command(self, client):
        """Test POST /api/voice/interact handles voice text command and replies with voice record."""
        payload = {
            "text": "Screen candidates now",
            "job_description": "Data Engineer with Spark and Kafka",
            "candidates": [
                {"name": "Mazen", "text": "Data Engineer with Apache Spark, Airflow and Kafka pipelines."},
                {"name": "John", "text": "Frontend CSS developer."}
            ]
        }
        res = client.post("/api/voice/interact", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["action"] == "screen"
        assert "audio_base64" in data
        assert data["audio_base64"].startswith("data:audio/")
        assert "ranked" in data
        assert data["ranked"][0]["name"] == "Mazen"
        assert "Mazen" in data["response_text"]

    def test_api_voice_interact_with_audio_file_upload(self, client):
        """Test POST /api/voice/interact accepts multipart/form-data audio file."""
        wav_bytes = create_dummy_wav_bytes(0.5)
        data = {
            "audio": (io.BytesIO(wav_bytes), "user_voice.wav"),
            "fallback_text": "Load Python preset",
            "language": "en"
        }
        res = client.post(
            "/api/voice/interact",
            data=data,
            content_type="multipart/form-data"
        )
        assert res.status_code == 200
        resp_data = res.get_json()
        assert resp_data["success"] is True
        assert resp_data["action"] == "load_preset"
        assert "audio_base64" in resp_data
        assert resp_data["audio_base64"].startswith("data:audio/")

    def test_api_voice_transcribe_missing_file(self, client):
        """Test POST /api/voice/transcribe returns 400 when no file is sent."""
        res = client.post("/api/voice/transcribe")
        assert res.status_code == 400
        data = res.get_json()
        assert data["success"] is False
