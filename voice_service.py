"""
Voice Service for Automated Resume Screening
Provides Speech-to-Text (STT) transcription and Text-to-Speech (TTS) audio response generation.
Supports dual-engine TTS (gTTS online + pyttsx3 offline fallback) and conversational AI screening.
"""

import io
import os
import re
import base64
import tempfile
import wave
import speech_recognition as sr
from gtts import gTTS
import pyttsx3

from main import screen_candidates

# Fallback presets definition if not imported directly
FALLBACK_PRESETS = [
    {"id": "data-engineer", "title": "Data Engineer (Spark, Airflow, Kafka, ETL, SQL)"},
    {"id": "ml-python", "title": "Python & Machine Learning Engineer"},
    {"id": "frontend-react", "title": "Senior Frontend React Developer"}
]


def is_arabic_text(text: str) -> bool:
    """Check if the text contains Arabic characters."""
    return bool(re.search(r'[\u0600-\u06FF]', text))


def transcribe_audio_file(file_obj_or_path, language: str = "auto") -> dict:
    """
    Transcribe a speech audio file (WAV) into text using SpeechRecognition.
    Handles auto language detection (Arabic or English).
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    # Determine if input is path or file-like object
    temp_wav_path = None
    try:
        if isinstance(file_obj_or_path, str):
            wav_source_path = file_obj_or_path
        else:
            # Save file object content to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                temp_wav_path = tf.name
                if hasattr(file_obj_or_path, "read"):
                    data = file_obj_or_path.read()
                else:
                    data = bytes(file_obj_or_path)
                tf.write(data)
            wav_source_path = temp_wav_path

        # Read audio with SpeechRecognition
        with sr.AudioFile(wav_source_path) as source:
            # Adjust for ambient noise and record
            audio_data = recognizer.record(source)

        # Transcribe
        transcribed_text = ""
        detected_lang = language

        # If language is auto or ar, try Arabic first or English
        languages_to_try = []
        if language == "ar" or language == "ar-EG":
            languages_to_try = ["ar-EG", "ar-SA", "en-US"]
        elif language == "en" or language == "en-US":
            languages_to_try = ["en-US", "ar-EG"]
        else:
            # Auto: Try English then Arabic
            languages_to_try = ["en-US", "ar-EG"]

        last_error = None
        for lang_code in languages_to_try:
            try:
                transcribed_text = recognizer.recognize_google(audio_data, language=lang_code)
                if transcribed_text:
                    detected_lang = "ar" if "ar" in lang_code else "en"
                    break
            except sr.UnknownValueError:
                last_error = "Speech was unintelligible"
                continue
            except sr.RequestError as e:
                last_error = f"Google Speech Recognition service error: {e}"
                break
            except Exception as e:
                last_error = str(e)
                continue

        if not transcribed_text:
            return {
                "success": False,
                "text": "",
                "error": last_error or "Could not transcribe audio. Please speak clearly.",
                "language": detected_lang
            }

        return {
            "success": True,
            "text": transcribed_text.strip(),
            "language": detected_lang,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "error": f"Audio processing error: {str(e)}",
            "language": language
        }
    finally:
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except Exception:
                pass


def generate_audio_speech(text: str, language: str = "en") -> dict:
    """
    Generate speech audio for the given text.
    First tries Google TTS (gTTS) for natural voice;
    falls back to pyttsx3 offline synthesizer on failure.
    Returns base64 data URI and metadata.
    """
    if not text or not text.strip():
        text = "Hello! No response text provided."

    clean_text = text.strip()
    is_ar = is_arabic_text(clean_text) or language.startswith("ar")
    tts_lang = "ar" if is_ar else "en"

    # Attempt 1: gTTS (High quality MP3)
    try:
        mp3_fp = io.BytesIO()
        tts = gTTS(text=clean_text, lang=tts_lang, slow=False)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        audio_bytes = mp3_fp.read()
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        return {
            "success": True,
            "audio_base64": f"data:audio/mp3;base64,{b64_audio}",
            "format": "mp3",
            "engine": "gTTS",
            "text": clean_text
        }
    except Exception as gtts_err:
        # Attempt 2: pyttsx3 offline fallback (Standard WAV)
        temp_wav = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                temp_wav = tf.name

            engine = pyttsx3.init()
            engine.setProperty("rate", 160)
            engine.setProperty("volume", 0.95)
            engine.save_to_file(clean_text, temp_wav)
            engine.runAndWait()

            with open(temp_wav, "rb") as f:
                wav_bytes = f.read()

            b64_audio = base64.b64encode(wav_bytes).decode("utf-8")
            return {
                "success": True,
                "audio_base64": f"data:audio/wav;base64,{b64_audio}",
                "format": "wav",
                "engine": "pyttsx3",
                "text": clean_text
            }
        except Exception as pyttsx3_err:
            return {
                "success": False,
                "audio_base64": None,
                "error": f"TTS generation failed: gTTS({gtts_err}), pyttsx3({pyttsx3_err})",
                "text": clean_text
            }
        finally:
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass


def formulate_screening_speech_response(job_desc: str, candidates_dict: dict, query_text: str = "") -> tuple[str, list]:
    """
    Screens candidates and crafts a natural, concise spoken response
    highlighting the winner, matching score, and top skills.
    """
    if not job_desc or not candidates_dict:
        return ("Please provide a job description and candidate resumes to run screening.", [])

    detailed = screen_candidates(job_desc, candidates_dict)
    if not detailed:
        return ("No candidate resumes were found to evaluate.", [])

    top = detailed[0]
    top_name = top["name"]
    top_score_pct = f"{top['score'] * 100:.0f}%"
    matched_skills = top.get("matched", [])

    is_ar = is_arabic_text(query_text)

    if is_ar:
        skills_str = ", ".join(matched_skills[:3]) if matched_skills else "المهارات العامة"
        msg = (
            f"تم الفحص والفرز بنجاح! أفضل مرشح هو {top_name} بنسبة توافق {top_score_pct}. "
            f"أبرز المهارات المطابقة لديه: {skills_str}. "
        )
        if len(detailed) > 1:
            runner_up = detailed[1]
            runner_up_pct = f"{runner_up['score'] * 100:.0f}%"
            msg += f"يليه في المركز الثاني {runner_up['name']} بنسبة {runner_up_pct}."
    else:
        skills_str = ", ".join(matched_skills[:3]) if matched_skills else "core competencies"
        msg = (
            f"Screening complete! The top ranked candidate is {top_name} with a {top_score_pct} match score. "
            f"Key matching competencies include: {skills_str}. "
        )
        if len(detailed) > 1:
            runner_up = detailed[1]
            runner_up_pct = f"{runner_up['score'] * 100:.0f}%"
            msg += f"In second place is {runner_up['name']} with a {runner_up_pct} match."

    return (msg, detailed)


def process_voice_command(
    audio_file_or_bytes=None,
    fallback_text: str = "",
    current_job_desc: str = "",
    current_candidates: dict = None,
    language: str = "auto"
) -> dict:
    """
    End-to-end voice pipeline:
    1. Transcribes audio input (or uses fallback text if mic was transcribed in browser).
    2. Identifies user intent (screen candidates, dictate requirements, load preset, analyze).
    3. Executes the corresponding action.
    4. Generates an audio voice recording response.
    5. Returns unified payload for the client.
    """
    current_candidates = current_candidates or {}
    transcribed_text = ""

    # Step 1: Speech-to-Text Transcription
    if audio_file_or_bytes:
        transcription_res = transcribe_audio_file(audio_file_or_bytes, language=language)
        if transcription_res.get("success"):
            transcribed_text = transcription_res.get("text", "")

    # If audio transcription didn't yield text, check fallback text from browser Web Speech API
    if not transcribed_text and fallback_text and fallback_text.strip():
        transcribed_text = fallback_text.strip()

    if not transcribed_text:
        default_err = "لم يتم التعرف على الصوت بوضوح، يرجى المحاولة مرة أخرى." if language.startswith("ar") else "Could not detect clear speech in the recording. Please try again."
        speech_gen = generate_audio_speech(default_err, language=language)
        return {
            "success": False,
            "transcribed_text": "",
            "response_text": default_err,
            "audio_base64": speech_gen.get("audio_base64"),
            "action": "none",
            "error": "No clear speech detected"
        }

    lower_text = transcribed_text.lower()
    is_ar = is_arabic_text(transcribed_text) or language.startswith("ar")
    resp_lang = "ar" if is_ar else "en"

    # Intent Detection
    # Intent A: Screening / Ranking
    screen_keywords = [
        "screen", "rank", "evaluate", "compare", "who is the best", "top candidate",
        "leaderboard", "results", "score", "candidates", "winner",
        "فرز", "ترتيب", "تقييم", "مين أفضل", "أفضل مرشح", "نتائج", "قارن", "فحص"
    ]
    is_screen_intent = any(k in lower_text for k in screen_keywords)

    # Intent B: Load Preset
    preset_keywords = ["preset", "example", "load", "نموذج", "مثال", "تحميل"]
    is_preset_intent = any(k in lower_text for k in preset_keywords)

    action = "none"
    response_text = ""
    action_data = {}

    if is_preset_intent:
        action = "load_preset"
        if "data" in lower_text or "spark" in lower_text or "بيانات" in lower_text:
            action_data["preset_id"] = "data-engineer"
            response_text = "تم تحميل نموذج وظيفة مهندس البيانات بنجاح." if is_ar else "Loaded the Data Engineer preset with candidates."
        elif "react" in lower_text or "frontend" in lower_text or "واجهة" in lower_text:
            action_data["preset_id"] = "frontend-react"
            response_text = "تم تحميل نموذج وظيفة مطور الواجهات React بنجاح." if is_ar else "Loaded the Frontend React Developer preset."
        else:
            action_data["preset_id"] = "ml-python"
            response_text = "تم تحميل نموذج وظيفة الذكاء الاصطناعي وبايثون بنجاح." if is_ar else "Loaded the Python & Machine Learning preset."

    elif is_screen_intent or (current_job_desc and current_candidates and len(current_candidates) > 0 and len(lower_text.split()) < 8):
        # Run Resume Screening
        if not current_job_desc:
            response_text = (
                "يرجى تحديد الوصف الوظيفي أولاً للبدء في الفرز."
                if is_ar else
                "Please provide a Job Description before screening resumes."
            )
        elif not current_candidates:
            response_text = (
                "يرجى إضافة سيرة ذاتية واحدة على الأقل للمرشحين."
                if is_ar else
                "Please add at least one candidate resume to screen."
            )
        else:
            speech_resp, detailed_candidates = formulate_screening_speech_response(
                current_job_desc, current_candidates, query_text=transcribed_text
            )
            response_text = speech_resp
            action = "screen"
            action_data["ranked"] = detailed_candidates

    elif "job" in lower_text or "require" in lower_text or "looking for" in lower_text or "مطلوب" in lower_text or "وظيفة" in lower_text:
        # Dictating / Updating Job Description
        action = "update_job"
        clean_desc = transcribed_text
        action_data["job_description"] = clean_desc
        response_text = (
            f"تم تحديث متطلبات الوظيفة بناءً على تسجيلك الصوتي: {clean_desc[:120]}..."
            if is_ar else
            f"Job requirements updated based on your voice input: {clean_desc[:120]}..."
        )

    else:
        # Conversational assistance
        action = "speak"
        if is_ar:
            response_text = (
                f"أهلاً بك! لقد استلمت تسجيلك الصوتي: \"{transcribed_text}\". "
                "يمكنك أن تطلب مني فرز المرشحين، أو تحميل النماذج الجاهزة، أو إملاء متطلبات الوظيفة."
            )
        else:
            response_text = (
                f"Hello! I heard: \"{transcribed_text}\". "
                "You can ask me to screen resumes, compare candidates, or load quick presets."
            )

    # Step 3: Generate the Audio Voice Response (Record back to the user!)
    speech_output = generate_audio_speech(response_text, language=resp_lang)

    return {
        "success": True,
        "transcribed_text": transcribed_text,
        "response_text": response_text,
        "audio_base64": speech_output.get("audio_base64"),
        "audio_format": speech_output.get("format", "mp3"),
        "action": action,
        "action_data": action_data
    }
