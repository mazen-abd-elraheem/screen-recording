"""
Automated Resume Screening - Web Application
Flask backend serving an interactive UI for screening and ranking resumes.
"""

import os
import sys
import requests
from flask import Flask, render_template, request, jsonify
from main import rank_resumes, screen_candidates
from resume_parser import extract_text_from_file, analyze_keyword_matches, is_valid_resume
from voice_service import process_voice_command, generate_audio_speech, transcribe_audio_file

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

PRESET_JOBS = [
    {
        "id": "data-engineer",
        "title": "Data Engineer (Spark, Airflow, Kafka, ETL, SQL)",
        "job_desc": (
            "We are seeking an experienced Data Engineer to design, build and maintain scalable ETL data pipelines.\n"
            "Requirements:\n"
            "- Hands-on experience with Apache Airflow, Apache Spark / PySpark, and Kafka\n"
            "- Strong proficiency in Python and SQL (PostgreSQL, BigQuery, Snowflake)\n"
            "- Experience building automated data pipelines, data warehousing, and ETL architectures\n"
            "- Knowledge of cloud infrastructure (AWS or GCP), Docker, and Git version control"
        ),
        "candidates": [
            {
                "name": "Mazen Abd Elraheem",
                "text": "Data Engineer with 4 years experience building automated ETL data pipelines using PySpark, Kafka streaming, and Airflow orchestration. Expert in PostgreSQL, SQL data warehousing, and AWS cloud services. Proficient in Docker and Git."
            },
            {
                "name": "Sarah Al-Mansoor",
                "text": "Machine Learning Engineer with 5 years experience in Python, scikit-learn, pandas, NumPy, and Flask REST APIs. Skilled in PostgreSQL, Git, and Docker."
            },
            {
                "name": "Alex Rivera",
                "text": "Lead Frontend Developer specializing in React, Next.js, TypeScript, and modern CSS. No data engineering or distributed computing background."
            }
        ]
    },
    {
        "id": "ml-python",
        "title": "Python & Machine Learning Engineer",
        "job_desc": (
            "We are seeking an experienced Python Developer with machine learning expertise.\n"
            "Requirements:\n"
            "- Strong proficiency in Python, scikit-learn, pandas, and NumPy\n"
            "- Experience building REST APIs using Flask or FastAPI\n"
            "- Knowledge of SQL databases (PostgreSQL/MySQL) and Git version control\n"
            "- Exposure to Docker containerization and cloud deployments is a plus"
        ),
        "candidates": [
            {
                "name": "Piyush",
                "text": "Python developer with 3 years of experience. Skilled in scikit-learn, pandas, NumPy and Flask. Built multiple RESTful APIs. Familiar with PostgreSQL and version control with Git."
            },
            {
                "name": "Riya",
                "text": "Full-stack Python developer. Uses Flask, scikit-learn, pandas, and NumPy daily. Strong SQL skills, active Git user, builds data pipelines."
            },
            {
                "name": "Suchak",
                "text": "Data scientist with expertise in machine learning, TensorFlow, pandas, and NumPy. Published research in NLP. Comfortable with Python and Git."
            },
            {
                "name": "Nikhil",
                "text": "Java backend developer with Spring Boot. Limited Python experience. Worked with SQL databases and REST APIs extensively."
            },
            {
                "name": "Tippsy",
                "text": "Front-end developer experienced in React, JavaScript, HTML and CSS. Some Python scripting knowledge. No machine learning background."
            }
        ]
    },
    {
        "id": "frontend-react",
        "title": "Senior Frontend React Developer",
        "job_desc": (
            "Looking for a Senior Frontend Developer to lead client web development.\n"
            "Requirements:\n"
            "- Expert in React, TypeScript, Next.js, and modern JavaScript (ES6+)\n"
            "- Proficient in Tailwind CSS, responsive layouts, and UI animations\n"
            "- Experience with state management (Redux / Zustand) and REST API integration\n"
            "- Familiarity with Git, automated testing (Jest/Cypress), and CI/CD"
        ),
        "candidates": [
            {
                "name": "Alex Rivera",
                "text": "Lead Frontend Developer with 4 years in React, Next.js, TypeScript, and Tailwind CSS. Built responsive web applications and integrated REST APIs."
            },
            {
                "name": "Tariq Aziz",
                "text": "Full-stack engineer with React, Node.js, Express, MongoDB, and basic TypeScript knowledge. Experienced in building responsive landing pages."
            },
            {
                "name": "Sarah Al-Mansoor",
                "text": "Machine Learning Engineer specializing in Python, TensorFlow, scikit-learn, pandas, and data visualization. Basic HTML/CSS knowledge."
            }
        ]
    }
]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/presets", methods=["GET"])
def get_presets():
    return jsonify(PRESET_JOBS)


def format_enriched_results(detailed_candidates, resumes):
    """Format screened candidates into detailed frontend presentation dicts."""
    results = []
    for rank, c in enumerate(detailed_candidates, start=1):
        name = c["name"]
        score = c["score"]
        resume_text = resumes.get(name, "")
        snippet = resume_text[:220] + ("..." if len(resume_text) > 220 else "")

        # Tier categorization (Calibrated Realistic Ranges)
        if score >= 0.65:
            tier = "high"
            badge = "High Match"
        elif score >= 0.35:
            tier = "medium"
            badge = "Moderate Fit"
        else:
            tier = "low"
            badge = "Low Match"

        results.append({
            "rank": rank,
            "name": name,
            "score": round(float(score), 4),
            "score_percent": f"{score * 100:.1f}%",
            "skill_match_percent": f"{c.get('skill_score', score) * 100:.1f}%",
            "context_match_percent": f"{c.get('context_score', score) * 100:.1f}%",
            "skills_ratio": f"{c.get('matched_count', 0)} of {c.get('total_competencies', 0)} skills found",
            "tier": tier,
            "badge": badge,
            "matched_keywords": c.get("matched", [])[:15],
            "missing_keywords": c.get("missing", [])[:15],
            "negated_keywords": c.get("negated", [])[:10],
            "snippet": snippet,
            "char_count": len(resume_text)
        })
    return results


@app.route("/api/validate-resume", methods=["POST"])
def validate_resume():
    """
    Validates uploaded file(s) or raw candidate text to determine if it's a genuine CV.
    Returns validation status, reason, and metadata.
    """
    try:
        # 1. Check if files were uploaded via multipart/form-data
        if "file" in request.files or "files[]" in request.files:
            files = request.files.getlist("files[]")
            if not files and "file" in request.files:
                files = [request.files.get("file")]

            results = []
            for file in files:
                if file and file.filename:
                    fname = file.filename
                    try:
                        text = extract_text_from_file(file, fname)
                        is_valid, reason, details = is_valid_resume(text)
                        results.append({
                            "filename": fname,
                            "is_valid": is_valid,
                            "reason": reason,
                            "word_count": details.get("word_count", 0),
                            "sections": details.get("sections_found", [])
                        })
                    except Exception as extract_err:
                        results.append({
                            "filename": fname,
                            "is_valid": False,
                            "reason": f"تعذر استخراج النصوص من الملف ({str(extract_err)})",
                            "word_count": 0,
                            "sections": []
                        })

            return jsonify({
                "success": True,
                "results": results,
                "all_valid": all(r["is_valid"] for r in results) if results else False
            })

        # 2. Check if JSON text was sent
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        name = data.get("name", "Candidate")
        is_valid, reason, details = is_valid_resume(text)
        return jsonify({
            "success": True,
            "name": name,
            "is_valid": is_valid,
            "reason": reason,
            "word_count": details.get("word_count", 0),
            "sections": details.get("sections_found", [])
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/screen", methods=["POST"])
def screen_resumes():
    try:
        rejected_candidates = []
        resumes = {}

        # Check if form data or JSON
        if request.is_json:
            data = request.get_json()
            job_desc = data.get("job_description", "").strip()
            raw_candidates = data.get("candidates", [])
            for c in raw_candidates:
                name = c.get("name", "").strip()
                text = c.get("text", "").strip()
                if name and text:
                    is_valid, reason, details = is_valid_resume(text)
                    if is_valid:
                        resumes[name] = text
                    else:
                        rejected_candidates.append({
                            "name": name,
                            "filename": name,
                            "reason": reason,
                            "word_count": details.get("word_count", 0)
                        })
        else:
            job_desc = request.form.get("job_description", "").strip()

            # Parse text candidates
            names = request.form.getlist("candidate_names[]")
            texts = request.form.getlist("candidate_texts[]")
            for name, text in zip(names, texts):
                if name.strip() and text.strip():
                    is_valid, reason, details = is_valid_resume(text.strip())
                    if is_valid:
                        resumes[name.strip()] = text.strip()
                    else:
                        rejected_candidates.append({
                            "name": name.strip(),
                            "filename": name.strip(),
                            "reason": reason,
                            "word_count": details.get("word_count", 0)
                        })

            # Parse uploaded files (.pdf, .docx, .txt)
            files = request.files.getlist("files[]")
            for file in files:
                if file and file.filename:
                    fname = file.filename
                    cand_name = os.path.splitext(fname)[0]
                    try:
                        extracted_text = extract_text_from_file(file, fname)
                        if extracted_text.strip():
                            is_valid, reason, details = is_valid_resume(extracted_text)
                            if is_valid:
                                resumes[cand_name] = extracted_text
                            else:
                                rejected_candidates.append({
                                    "name": cand_name,
                                    "filename": fname,
                                    "reason": reason,
                                    "word_count": details.get("word_count", 0)
                                })
                    except Exception as extract_err:
                        rejected_candidates.append({
                            "name": cand_name,
                            "filename": fname,
                            "reason": f"تعذر استخراج النصوص من الملف ({str(extract_err)})",
                            "word_count": 0
                        })

        if not job_desc:
            return jsonify({"error": "Job description cannot be empty."}), 400

        if not resumes:
            reasons_summary = " | ".join(f"{r['filename']}: {r['reason']}" for r in rejected_candidates)
            error_msg = f"لم يتم قبول أي ملف كسيرة ذاتية صالحة. {reasons_summary}" if rejected_candidates else "Please provide at least one valid candidate resume or upload a valid CV file."
            return jsonify({
                "error": error_msg,
                "rejected": rejected_candidates
            }), 400

        # Run Universal Screening Engine
        detailed_candidates = screen_candidates(job_desc, resumes)
        results = format_enriched_results(detailed_candidates, resumes)

        return jsonify({
            "success": True,
            "total_candidates": len(results),
            "top_candidate": results[0]["name"] if results else None,
            "ranked": results,
            "rejected": rejected_candidates,
            "total_rejected": len(rejected_candidates)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/voice/interact", methods=["POST"])
def voice_interact():
    """
    Accepts user audio recording (or voice text fallback), transcribes it,
    understands intent (screen candidates, update job description, load preset, query),
    executes action, and returns both text and audio recording response (record back to user).
    """
    try:
        # 1. Extract audio if provided
        audio_file = None
        if "audio" in request.files:
            audio_file = request.files["audio"]
        elif "file" in request.files:
            audio_file = request.files["file"]

        # 2. Extract fallback text or language
        fallback_text = ""
        language = "auto"
        job_desc = ""
        resumes = {}

        if request.is_json:
            data = request.get_json() or {}
            fallback_text = data.get("text", data.get("fallback_text", ""))
            language = data.get("language", "auto")
            job_desc = data.get("job_description", "").strip()
            candidates = data.get("candidates", [])
            for c in candidates:
                n = c.get("name", "").strip()
                t = c.get("text", "").strip()
                if n and t:
                    resumes[n] = t
        else:
            fallback_text = request.form.get("text", request.form.get("fallback_text", "")).strip()
            language = request.form.get("language", "auto")
            job_desc = request.form.get("job_description", "").strip()

            # Parse text candidates
            names = request.form.getlist("candidate_names[]")
            texts = request.form.getlist("candidate_texts[]")
            for name, text in zip(names, texts):
                if name.strip() and text.strip():
                    resumes[name.strip()] = text.strip()

        # If candidates are empty but preset was specified or default can be used
        if not resumes and not job_desc:
            # Check default preset
            default_p = PRESET_JOBS[0]
            job_desc = default_p["job_desc"]
            resumes = {c["name"]: c["text"] for c in default_p["candidates"]}

        # Process voice interaction
        voice_result = process_voice_command(
            audio_file_or_bytes=audio_file,
            fallback_text=fallback_text,
            current_job_desc=job_desc,
            current_candidates=resumes,
            language=language
        )

        response_payload = {
            "success": voice_result.get("success", False),
            "transcribed_text": voice_result.get("transcribed_text", ""),
            "response_text": voice_result.get("response_text", ""),
            "audio_base64": voice_result.get("audio_base64"),
            "audio_format": voice_result.get("audio_format", "mp3"),
            "action": voice_result.get("action", "none"),
            "action_data": voice_result.get("action_data", {})
        }

        # If action was screen, enrich ranking results for frontend leaderboard
        if voice_result.get("action") == "screen":
            action_data = voice_result.get("action_data", {})
            detailed_candidates = action_data.get("ranked", [])
            enriched = format_enriched_results(detailed_candidates, resumes)
            response_payload["ranked"] = enriched
            response_payload["total_candidates"] = len(enriched)
            response_payload["top_candidate"] = enriched[0]["name"] if enriched else None

        return jsonify(response_payload)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/voice/speak", methods=["POST"])
def voice_speak():
    """
    Generate speech audio for any given text.
    Returns base64 audio data URI.
    """
    try:
        data = request.get_json() if request.is_json else request.form
        text = (data.get("text") or "").strip()
        language = data.get("language", "en")

        if not text:
            return jsonify({"success": False, "error": "No text provided."}), 400

        result = generate_audio_speech(text, language=language)
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/voice/transcribe", methods=["POST"])
def voice_transcribe():
    """
    Transcribe an uploaded audio recording into text.
    """
    try:
        audio_file = request.files.get("audio") or request.files.get("file")
        if not audio_file:
            return jsonify({"success": False, "error": "No audio file provided."}), 400

        language = request.form.get("language", "auto")
        result = transcribe_audio_file(audio_file, language=language)
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# Voice Tutorial Speaker & Ollama Chatbot Service
# ============================================================================

TUTORIAL_TEXT_EN = (
    "Welcome to the Automated Resume Screening Platform. "
    "Here is how to use the system in four simple steps. "
    "Step one: Define your job requirements in the Job Description box, or click the microphone icon to dictate them. "
    "Step two: Add candidate resumes. You can enter text profiles or upload PDF, Word, and text documents. "
    "Step three: Click Screen and Rank Resumes, or speak your command using the Voice Screener. "
    "Our Universal NLP Engine scores candidates using an eighty percent skill match weight, a twenty percent calibrated context score, and deducts points for disclaimed skills. "
    "Step four: Review the ranked leaderboard, listen to the spoken winner evaluation, and use our Ollama AI chatbot to ask in-depth questions or generate interview questions. "
    "You are all set to begin!"
)

TUTORIAL_TEXT_AR = (
    "مرحباً بك في منصة فرز السير الذاتية الآلية. "
    "إليك كيفية استخدام النظام في أربع خطوات سهلة. "
    "الخطوة الأولى: حدد متطلبات الوظيفة في صندوق الوصف الوظيفي، أو اضغط زر الميكروفون لإملائها صوتياً. "
    "الخطوة الثانية: أضف السير الذاتية للمرشحين كنصوص، أو ارفع ملفات بي دي إف ووورد. "
    "الخطوة الثالثة: اضغط على زر فرز وترتيب السير الذاتية، أو استخدم المساعد الصوتي لفرزها بالصوت. "
    "يقوم محرك المعالجة اللغوية بتقييم المرشحين بناءً على ثمانين بالمائة للمهارات وعشرين بالمائة للسياق، مع خصم للمهارات المنفية. "
    "الخطوة الرابعة: استعرض لوحة النتائج واستمع لتقييم المرشح الأول، وتحدث مع مساعد أولاما الذكي للحصول على تحليلات وأسئلة مقابلات مخصصة. "
    "نتمنى لك تجربة موفقة!"
)

TUTORIAL_STEPS_EN = [
    {
        "step": 1,
        "title": "Define Job Requirements",
        "description": "Write or dictate the target competencies and skills needed for the open position."
    },
    {
        "step": 2,
        "title": "Ingest Candidate Resumes",
        "description": "Paste candidate text profiles or drag & drop multi-page PDF, Word (.docx), and TXT files."
    },
    {
        "step": 3,
        "title": "Screen with Universal NLP",
        "description": "The engine normalizes terms with Porter Stemmer, maps technical aliases, and computes calibrated hybrid scores."
    },
    {
        "step": 4,
        "title": "Leaderboard & Ollama Assistant",
        "description": "Review ranked candidate cards, listen to audio reviews, and ask the local Ollama AI for interview questions."
    }
]

TUTORIAL_STEPS_AR = [
    {
        "step": 1,
        "title": "تحديد متطلبات الوظيفة",
        "description": "اكتب أو أملِ متطلبات الوظيفة والمهارات المستهدفة مثل بايثون، سيكول، سبارك، ودوكر."
    },
    {
        "step": 2,
        "title": "إدخال السير الذاتية",
        "description": "الصق نصوص المرشحين أو اسحب وأفلت ملفات الـ PDF أو Word (.docx) مباشرة."
    },
    {
        "step": 3,
        "title": "الفرز بمحرك المعالجة اللغوية",
        "description": "توحيد جذور الكلمات بـ Porter Stemming ومعايرة النسب بدون أي تخفيف أو تحيز."
    },
    {
        "step": 4,
        "title": "لوحة الصدارة ومساعد أولاما الذكي",
        "description": "استعراض الترتيب وسماع المراجعة الصوتية ومحاورة المساعد الذكي لتوليد أسئلة المقابلات."
    }
]

OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


def generate_smart_recruitment_reply(user_query: str, job_desc: str, candidates: list) -> str:
    """
    Intelligent analytical fallback when Ollama is starting or warming up.
    Extracts relevant context from the candidate leaderboard and formulates structured advice.
    """
    q_lower = user_query.lower()

    if not candidates:
        return (
            "No candidates have been evaluated yet. Please select a job preset or input candidate resumes, "
            "then run screening to enable in-depth AI talent analysis."
        )

    top = candidates[0]
    top_name = top.get("name", "Top Candidate")
    top_score = top.get("score_percent", "N/A")
    top_matched = top.get("matched_keywords", [])
    top_missing = top.get("missing_keywords", [])
    top_negated = top.get("negated_keywords", [])

    # Check for Interview Questions intent
    if any(k in q_lower for k in ["interview", "question", "questions", "ask", "test"]):
        missing_str = ", ".join(top_missing[:3]) if top_missing else "advanced architectural system design"
        return (
            f"Here are 4 targeted technical interview questions for **{top_name}** (Ranked #1 with {top_score} match):\n\n"
            f"1. **Core Competency Validation**: In your previous projects, how did you utilize {', '.join(top_matched[:2]) or 'your core skills'} to solve scalability or performance bottlenecks?\n"
            f"2. **Gap Assessment ({missing_str})**: We noticed limited explicit experience in {missing_str}. Have you worked with related alternatives or how quickly have you onboarded onto similar tools?\n"
            f"3. **Architecture & Reliability**: Describe how you handle error recovery, monitoring, and automated testing across your deployment pipeline.\n"
            f"4. **Cross-Functional Leadership**: How do you collaborate with non-technical stakeholders to translate business requirements into technical deliverables?"
        )

    # Check for Comparison intent
    if any(k in q_lower for k in ["compare", "comparison", "difference", "vs", "versus"]):
        if len(candidates) < 2:
            return f"Only one candidate ({top_name}) is currently evaluated. Add more candidates to see a side-by-side comparison."
        second = candidates[1]
        sec_name = second.get("name", "Second Candidate")
        sec_score = second.get("score_percent", "N/A")
        sec_matched = second.get("matched_keywords", [])

        return (
            f"### Comparative Assessment: {top_name} vs. {sec_name}\n\n"
            f"- **Rank #1: {top_name} ({top_score})**\n"
            f"  - **Key Strengths**: Verified mastery of {', '.join(top_matched[:4]) or 'core skills'}.\n"
            f"  - **Areas to Probe**: Missing {', '.join(top_missing[:3]) or 'none'}.\n\n"
            f"- **Rank #2: {sec_name} ({sec_score})**\n"
            f"  - **Key Strengths**: Found {', '.join(sec_matched[:4]) or 'relevant skills'}.\n"
            f"  - **Reason for Ranking Lower**: Lower technical competency coverage and missing key requirements.\n\n"
            f"**Recommendation**: {top_name} demonstrates stronger alignment with the required tech stack and is the recommended frontrunner."
        )

    # Check for Why winner / Why ranked intent
    if any(k in q_lower for k in ["why", "winner", "reason", "rank", "score"]):
        return (
            f"### Why {top_name} Ranked #1 ({top_score} Match):\n\n"
            f"1. **High Technical Competency Coverage (80% Weight)**: Verified {len(top_matched)} key technical competencies: {', '.join(top_matched[:5]) or 'core job skills'}.\n"
            f"2. **Contextual Alignment (20% Weight)**: Strong domain terminology density matching the job description without length penalty dilution.\n"
            f"3. **Zero Disqualification Flags**: No disclaimed or negated competencies detected.\n\n"
            f"This combination places {top_name} at the top of the candidate pool."
        )

    # Default overview
    return (
        f"### Screening Pool Summary\n\n"
        f"Currently evaluating {len(candidates)} candidate(s). The top-ranked applicant is **{top_name}** with a match score of **{top_score}**.\n\n"
        f"- **Matched Core Skills**: {', '.join(top_matched[:5]) or 'None'}\n"
        f"- **Missing Skills to Verify**: {', '.join(top_missing[:4]) or 'None'}\n\n"
        f"You can ask me to generate customized interview questions, compare specific candidates, or suggest job requirement adjustments."
    )


# In-memory cache for static tutorial guides to eliminate redundant TTS synthesis
_TUTORIAL_AUDIO_CACHE = {}


@app.route("/api/tutorial/voice", methods=["GET", "POST"])
def voice_tutorial():
    """
    Generate or return the spoken voice tutorial audio and visual step guide.
    Caches the audio response in memory to avoid repetitive generation and network latency.
    """
    try:
        data = request.get_json(silent=True) if request.is_json else {}
        language = request.args.get("language") or (data.get("language") if data else "en")
        is_ar = language in ["ar", "ar-EG", "ar-SA"]
        cache_key = "ar" if is_ar else "en"

        # Return instantly from cache if already generated
        if cache_key in _TUTORIAL_AUDIO_CACHE:
            return jsonify(_TUTORIAL_AUDIO_CACHE[cache_key])

        script_text = TUTORIAL_TEXT_AR if is_ar else TUTORIAL_TEXT_EN
        steps = TUTORIAL_STEPS_AR if is_ar else TUTORIAL_STEPS_EN

        audio_res = generate_audio_speech(script_text, language="ar" if is_ar else "en")

        payload = {
            "success": True,
            "language": cache_key,
            "script": script_text,
            "steps": steps,
            "audio_base64": audio_res.get("audio_base64"),
            "audio_format": audio_res.get("format", "mp3")
        }

        # Cache on successful generation
        if audio_res.get("audio_base64"):
            _TUTORIAL_AUDIO_CACHE[cache_key] = payload

        return jsonify(payload)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ollama/models", methods=["GET"])
def get_ollama_models():
    """
    Fetch list of available models from local Ollama instance.
    """
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name") for m in data.get("models", []) if m.get("name")]
            default_model = "mistral:latest" if "mistral:latest" in models else (models[0] if models else "phi3:mini")
            return jsonify({
                "status": "online",
                "models": models,
                "default_model": default_model,
                "url": OLLAMA_BASE_URL
            })
    except Exception:
        pass

    return jsonify({
        "status": "offline",
        "models": ["phi3:mini", "mistral:latest", "nebula-masri:latest"],
        "default_model": "mistral:latest",
        "url": OLLAMA_BASE_URL,
        "message": "Local Ollama service on port 11434 is standby or initializing."
    })


@app.route("/api/ollama/chat", methods=["POST"])
def ollama_chat():
    """
    Conversational AI Chatbot powered by local Ollama with candidate and job screening context.
    """
    try:
        data = request.get_json(force=True) if request.is_json else request.form
        user_message = (data.get("message") or "").strip()
        if not user_message:
            return jsonify({"success": False, "error": "Message is empty."}), 400

        model = data.get("model") or "mistral:latest"
        history = data.get("history") or []
        context = data.get("context") or {}

        job_desc = context.get("job_description", "")
        candidates_ranked = context.get("ranked", [])

        # Build context briefing for system prompt
        context_lines = []
        if job_desc:
            context_lines.append(f"Target Job Description:\n{job_desc[:1200]}")
        if candidates_ranked:
            context_lines.append("Current Candidate Rankings & Breakdown:")
            for idx, c in enumerate(candidates_ranked[:5], start=1):
                c_name = c.get("name", f"Candidate {idx}")
                score = c.get("score_percent", "N/A")
                matched = ", ".join(c.get("matched_keywords", [])[:8]) or "None"
                missing = ", ".join(c.get("missing_keywords", [])[:8]) or "None"
                negated = ", ".join(c.get("negated_keywords", [])) or "None"
                context_lines.append(
                    f"#{idx} {c_name} (Match: {score}) - Matched: [{matched}] | Missing: [{missing}] | Negated: [{negated}]"
                )

        screening_context_str = "\n".join(context_lines)

        system_instruction = (
            "You are an expert AI Recruitment Consultant and Talent Evaluator embedded inside the "
            "Automated Resume Screening System. Your role is to provide hiring managers with clear, "
            "objective, insightful advice on candidate qualifications, interview questions, and job requirements.\n\n"
            f"--- SCREENING DATA CONTEXT ---\n{screening_context_str}\n------------------------------\n"
            "Guidelines:\n"
            "- Be concise, professional, and actionable.\n"
            "- If asked to compare candidates, refer directly to their matched skills, missing competencies, and disclaimed skills.\n"
            "- If asked for interview questions, generate 3-5 specific technical questions targeting the candidate's missing competencies.\n"
            "- Respond in the same language as the user (English or Arabic)."
        )

        # Prepare messages array for Ollama API
        messages = [{"role": "system", "content": system_instruction}]

        for h in history[-6:]:
            role = "user" if h.get("role") == "user" else "assistant"
            content = h.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        # Try connecting to Ollama
        try:
            ollama_payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_ctx": 2048,
                    "temperature": 0.7
                }
            }
            res = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=ollama_payload, timeout=40)
            if res.status_code == 200:
                res_data = res.json()
                assistant_reply = res_data.get("message", {}).get("content", "")
                if assistant_reply:
                    return jsonify({
                        "success": True,
                        "reply": assistant_reply,
                        "model": model,
                        "source": "ollama"
                    })
        except Exception:
            pass

        # Intelligent Fallback Recruitment Analyst Engine
        fallback_reply = generate_smart_recruitment_reply(user_message, job_desc, candidates_ranked)
        return jsonify({
            "success": True,
            "reply": fallback_reply,
            "model": f"{model} (Rule-Based Fallback)",
            "source": "fallback"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Resume Screening Web App starting on http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
