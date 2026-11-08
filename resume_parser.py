"""
Resume Parser and NLP Analysis Utilities
Extracts text from PDF, DOCX, and TXT files, and analyzes keyword matches
including negation detection and competency mapping.
"""

import io
import re
from typing import BinaryIO, Union
from main import (
    detect_negations,
    extract_competencies,
    normalize_text,
    stem_phrase,
    stemmer,
    match_competency_in_resume,
    TECH_ALIASES
)


def extract_text_from_file(file_source: Union[str, BinaryIO], filename: str) -> str:
    """Extract text from PDF, DOCX, or plain text file."""
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        try:
            try:
                import pypdf
                reader = pypdf.PdfReader(file_source)
            except ImportError:
                import PyPDF2 as pypdf
                reader = pypdf.PdfReader(file_source)

            text_pages = []
            for page in reader.pages:
                try:
                    extracted = page.extract_text()
                    if extracted:
                        text_pages.append(extracted)
                except Exception:
                    continue
            return "\n".join(text_pages).strip()
        except ImportError:
            raise RuntimeError("PDF parsing requires the 'pypdf' package. Please run: pip install pypdf")
        except Exception as e:
            raise RuntimeError(f"Error extracting text from PDF '{filename}': {e}")

    elif filename_lower.endswith(".docx"):
        import docx

        doc = docx.Document(file_source)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragraphs.append(cell.text.strip())
        return "\n".join(paragraphs).strip()

    else:
        # Plain text / Markdown / unknown
        if isinstance(file_source, str):
            with open(file_source, "rb") as f:
                content = f.read()
        else:
            content = file_source.read()

        for encoding in ["utf-8", "utf-16", "cp1252", "latin-1"]:
            try:
                return content.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="ignore").strip()


def analyze_keyword_matches(job_desc: str, resume_text: str, top_n: int = 15) -> dict:
    """
    Find matched, missing, and explicitly negated competencies between job description
    and candidate resume using morphological stemming and technology thesaurus.
    """
    job_competencies = extract_competencies(job_desc)
    resume_norm = normalize_text(resume_text)
    resume_stemmed_norm = stem_phrase(resume_text)

    cand_tokens = set(re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{1,25}\b", resume_norm))
    cand_stemmed_tokens = {stemmer.stem(t) for t in cand_tokens}
    negated_set = detect_negations(resume_text)

    matched = []
    missing = []
    negated = []

    for comp in job_competencies:
        comp_stemmed = stem_phrase(comp)
        is_negated = (
            comp in negated_set or
            comp_stemmed in negated_set or
            any(neg in comp for neg in negated_set if len(neg) > 2)
        )

        if is_negated:
            negated.append(comp)
        elif match_competency_in_resume(comp, resume_norm, resume_stemmed_norm, cand_tokens, cand_stemmed_tokens):
            matched.append(comp)
        else:
            missing.append(comp)

    total = max(1, len(job_competencies))
    skill_coverage = len(matched) / total

    return {
        "matched": matched[:top_n],
        "missing": missing[:top_n],
        "negated": negated[:top_n],
        "total_job_competencies": len(job_competencies),
        "matched_count": len(matched),
        "negated_count": len(negated),
        "skill_score_percent": f"{skill_coverage * 100:.1f}%",
        "skills_ratio": f"{len(matched)} of {len(job_competencies)} skills found"
    }


# ============================================================================
# Genuine CV / Resume Validation Engine
# ============================================================================

CV_EXPERIENCE_KEYWORDS = [
    r"\bexperience\b", r"\bemployment\b", r"\bwork history\b", r"\bprofessional background\b",
    r"\bcareer\b", r"\bjob history\b", r"\broles?\b", r"\bresponsibilit(y|ies)\b",
    r"خبر[ةه]", r"الخبرات", r"سجل العمل", r"العمل السابق", r"الوظائف", r"المسؤوليات"
]

CV_EDUCATION_KEYWORDS = [
    r"\beducation\b", r"\buniversity\b", r"\bcollege\b", r"\bdegree\b", r"\bbachelor\b",
    r"\bmaster\b", r"\bphd\b", r"\bdiploma\b", r"\bgraduat(e|ed|ion)\b", r"\bfaculty\b",
    r"تعليم", r"المؤهل", r"المؤهلات", r"جامع[ةه]", r"كلي[ةه]", r"بكالوريوس", r"ماجستير",
    r"دكتوراه", r"شهادة", r"دبلوم", r"دراسة"
]

CV_SKILLS_KEYWORDS = [
    r"\bskills?\b", r"\bcompetenc(y|ies)\b", r"\bproficienc(y|ies)\b", r"\btechnolog(y|ies)\b",
    r"\btools?\b", r"\bframeworks?\b", r"\bprogramming\b", r"\bstack\b",
    r"مهار[ةات]", r"المهارات", r"كفاء[ةات]", r"الأدوات", r"تقنيات", r"لغات البرمجة"
]

CV_PROJECT_KEYWORDS = [
    r"\bprojects?\b", r"\bsummary\b", r"\bprofile\b", r"\bobjective\b", r"\bportfolio\b",
    r"\bcertificat(e|ion|ions)\b", r"\bachievements?\b",
    r"مشاريع", r"مشروع", r"نبذ[ةه]", r"ملخص", r"إنجازات", r"شهادات", r"الهدف المهني"
]

INVOICE_BILL_PATTERNS = [
    r"\binvoice\b", r"\bbill to\b", r"\bamount due\b", r"\bsubtotal\b", r"\bunit price\b",
    r"\bvat number\b", r"\bpurchase order\b", r"\btax invoice\b",
    r"فاتور[ةه]", r"إيصال", r"المبلغ المستحق", r"سند قبض"
]


def is_valid_resume(text: str) -> tuple[bool, str, dict]:
    """
    Validate whether the given document text represents a genuine candidate Resume / CV.
    Returns:
        (is_valid: bool, reason: str, details: dict)
    """
    if not text or not text.strip():
        return (
            False,
            "الملف فارغ أو لا يحتوي على نصوص قابلة للقراءة (File contains no readable text).",
            {"score": 0, "reason": "empty"}
        )

    clean_text = text.strip()
    words = clean_text.split()
    word_count = len(words)

    if word_count < 12:
        return (
            False,
            f"محتوى الملف قصير جداً ({word_count} كلمة فقط) ولا يستوفي هيكل السيرة الذاتية (Content is too short to be a valid CV).",
            {"score": 0, "word_count": word_count, "reason": "too_short"}
        )

    text_lower = clean_text.lower()

    # Reject obvious non-resume documents like invoices / receipts
    invoice_matches = [p for p in INVOICE_BILL_PATTERNS if re.search(p, text_lower)]
    if len(invoice_matches) >= 2 and not any(re.search(p, text_lower) for p in CV_EXPERIENCE_KEYWORDS):
        return (
            False,
            "الملف يبدو كفاتورة أو مستند تجاري/مالي وليس سيرة ذاتية (Detected Invoice or Financial Receipt document).",
            {"score": 0, "detected_type": "invoice", "reason": "invoice_detected"}
        )

    # Detect presence of core CV sections
    has_experience = any(re.search(p, text_lower) for p in CV_EXPERIENCE_KEYWORDS)
    has_education = any(re.search(p, text_lower) for p in CV_EDUCATION_KEYWORDS)
    has_skills = any(re.search(p, text_lower) for p in CV_SKILLS_KEYWORDS)
    has_projects = any(re.search(p, text_lower) for p in CV_PROJECT_KEYWORDS)

    # Detect contact details
    has_email = bool(re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", clean_text))
    has_phone = bool(re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,5}", clean_text))
    has_links = bool(re.search(r"(linkedin\.com|github\.com|portfolio|gitlab\.com)", text_lower))
    has_contact = has_email or has_phone or has_links

    # Scoring indicators
    sections_found = []
    score = 0
    if has_experience:
        score += 2
        sections_found.append("Experience/الخبرات")
    if has_education:
        score += 2
        sections_found.append("Education/التعليم")
    if has_skills:
        score += 2
        sections_found.append("Skills/المهارات")
    if has_projects:
        score += 1
        sections_found.append("Projects/المشاريع")
    if has_contact:
        score += 1

    # Check for technical job title / skill keywords
    tech_keywords = [
        "python", "sql", "react", "docker", "spark", "kafka", "aws", "cloud",
        "developer", "engineer", "designer", "architect", "analyst", "manager",
        "backend", "frontend", "fullstack", "machine learning", "data", "software"
    ]
    tech_hits = sum(1 for k in tech_keywords if k in text_lower)
    if tech_hits >= 2:
        score += 1

    details = {
        "word_count": word_count,
        "score": score,
        "has_experience": has_experience,
        "has_education": has_education,
        "has_skills": has_skills,
        "has_projects": has_projects,
        "has_contact": has_contact,
        "sections_found": sections_found
    }

    # Validation condition:
    # Must meet reasonable CV density
    is_valid = (
        score >= 3 or
        (len([s for s in [has_experience, has_education, has_skills] if s]) >= 2) or
        (has_contact and (has_experience or has_skills) and word_count >= 20) or
        (has_experience and tech_hits >= 1 and word_count >= 20) or
        (has_skills and tech_hits >= 2 and word_count >= 20)
    )

    if not is_valid:
        missing_sections = []
        if not has_experience:
            missing_sections.append("الخبرات المهنية (Experience)")
        if not has_education:
            missing_sections.append("التعليم والمؤهلات (Education)")
        if not has_skills:
            missing_sections.append("المهارات التقنية (Skills)")

        missing_str = "، ".join(missing_sections[:2])
        return (
            False,
            f"الملف لا يستوفي هيكل السيرة الذاتية (يفتقر إلى: {missing_str}).",
            details
        )

    return (True, "تم التحقق من هيكل السيرة الذاتية بنجاح.", details)

