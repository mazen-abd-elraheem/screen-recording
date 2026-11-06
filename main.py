"""
Automated Resume Screening - Universal High-Accuracy NLP Engine
Powered by NLTK Porter Stemming, Dynamic Tech Competency Extraction,
Negation Detection, and Sublinear TF-IDF Contextual Analysis.
"""

import re
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.stem import PorterStemmer

# Ensure UTF-8 encoding for console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Initialize Porter Stemmer for grammatical root normalization
stemmer = PorterStemmer()

STOPWORDS = {
    "and", "the", "for", "with", "that", "this", "from", "have", "has", "had",
    "are", "was", "were", "been", "will", "would", "should", "could", "about",
    "into", "through", "during", "before", "after", "above", "below", "between",
    "under", "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "too", "very",
    "can", "our", "you", "your", "they", "them", "their", "his", "her", "its",
    "looking", "candidate", "candidates", "experience", "years", "year", "knowledge",
    "plus", "role", "team", "daily", "strong", "active", "built", "using",
    "building", "know", "familiar", "skilled", "developer", "engineer", "work",
    "worked", "working", "proficient", "seeking", "responsible", "proven", "hands-on",
    "must", "deploy", "deploying", "good", "great", "excellent", "ability", "responsibilities"
}

# Broad Domain Tech Taxonomy (Data Engineering, Cloud, DevOps, Backend, Frontend, AI)
TECH_ALIASES = {
    # Data Engineering & Databases
    "postgresql": ["sql", "databases", "relational database", "rdbms"],
    "postgres": ["sql", "databases", "relational database", "rdbms"],
    "mysql": ["sql", "databases", "relational database", "rdbms"],
    "sqlite": ["sql", "databases", "relational database", "rdbms"],
    "oracle": ["sql", "databases", "relational database", "rdbms"],
    "sql server": ["sql", "databases", "relational database"],
    "pyspark": ["spark", "apache spark", "big data", "data pipelines", "distributed computing"],
    "spark": ["pyspark", "apache spark", "big data", "data pipelines"],
    "apache spark": ["spark", "pyspark", "big data"],
    "airflow": ["apache airflow", "data orchestration", "etl", "data pipelines", "scheduling"],
    "apache airflow": ["airflow", "data orchestration", "etl", "data pipelines"],
    "kafka": ["apache kafka", "event streaming", "data pipelines", "message broker"],
    "apache kafka": ["kafka", "event streaming", "data pipelines"],
    "snowflake": ["data warehouse", "data warehousing", "cloud dw", "sql"],
    "bigquery": ["data warehouse", "data warehousing", "google cloud", "gcp", "sql"],
    "databricks": ["spark", "lakehouse", "data lake", "delta lake", "pyspark"],
    "dbt": ["data transformation", "sql", "analytics engineering", "etl"],
    "hadoop": ["big data", "mapreduce", "hdfs", "distributed computing"],
    "etl": ["data pipelines", "data pipeline", "data ingestion", "data integration"],
    "elt": ["etl", "data pipelines", "data pipeline"],
    "data pipeline": ["etl", "data pipelines", "data ingestion"],
    "data pipelines": ["etl", "data pipeline", "data ingestion"],
    "data warehouse": ["data warehousing", "dw", "bi", "data modeling"],
    "data warehousing": ["data warehouse", "dw", "bi", "data modeling"],

    # Cloud & DevOps
    "aws": ["amazon web services", "cloud", "cloud computing", "cloud infrastructure"],
    "amazon web services": ["aws", "cloud", "cloud computing"],
    "gcp": ["google cloud", "google cloud platform", "cloud"],
    "google cloud": ["gcp", "google cloud platform", "cloud"],
    "azure": ["microsoft azure", "cloud", "cloud computing"],
    "docker": ["containers", "containerization", "dockerization"],
    "kubernetes": ["k8s", "container orchestration", "devops"],
    "k8s": ["kubernetes", "container orchestration"],
    "terraform": ["infrastructure as code", "iac", "devops"],
    "ci/cd": ["cicd", "continuous integration", "pipelines", "devops"],
    "cicd": ["ci/cd", "continuous integration", "devops"],

    # Web & Backend
    "restful": ["rest", "rest apis", "rest api", "apis", "api"],
    "restful apis": ["rest apis", "rest api", "rest", "apis", "api"],
    "rest api": ["rest apis", "rest", "apis", "api"],
    "rest apis": ["rest api", "rest", "apis", "api"],
    "fastapi": ["python", "rest apis", "web framework", "backend"],
    "flask": ["python", "rest apis", "web framework", "backend"],
    "django": ["python", "rest apis", "web framework", "backend"],
    "spring boot": ["java", "spring", "backend", "microservices"],
    "spring": ["spring boot", "java", "backend"],
    "nodejs": ["node.js", "node", "javascript", "backend"],
    "node.js": ["nodejs", "node", "javascript", "backend"],

    # Frontend
    "react": ["react.js", "reactjs", "frontend", "ui"],
    "react.js": ["react", "frontend", "ui"],
    "next.js": ["nextjs", "next", "react", "frontend"],
    "nextjs": ["next.js", "next", "react", "frontend"],
    "ts": ["typescript"],
    "js": ["javascript"],
    "tailwind": ["tailwind css", "css"],
    "tailwind css": ["tailwind", "css"],

    # AI & ML
    "machine learning": ["ml", "predictive modeling", "statistical modeling"],
    "deep learning": ["neural networks", "dl", "machine learning"],
    "scikit-learn": ["sklearn", "machine learning", "python"],
    "sklearn": ["scikit-learn", "machine learning", "python"],
    "tensorflow": ["deep learning", "machine learning", "neural networks"],
    "pytorch": ["deep learning", "machine learning", "neural networks"],
    "nlp": ["natural language processing", "text mining", "llm"],
    "llm": ["large language models", "generative ai", "nlp", "llms"],
    "llms": ["large language models", "generative ai", "nlp", "llm"],
}

COMMON_TECH_PATTERNS = [
    # Multi-word technical patterns
    "data pipeline", "data pipelines", "data engineering", "data science",
    "data analysis", "data warehousing", "data warehouse", "data lake",
    "machine learning", "deep learning", "apache airflow", "apache spark",
    "apache kafka", "cloud infrastructure", "infrastructure as code",
    "spring boot", "rest apis", "restful apis", "rest api", "version control",
    "web applications", "front end", "frontend", "back end", "backend",
    "full stack", "fullstack", "scikit-learn", "tailwind css", "next.js",
    "node.js", "sql databases", "relational database", "nosql database",
    "ci/cd", "continuous integration", "unit testing", "large language models"
]


def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase and stripping excess whitespace."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def stem_phrase(phrase: str) -> str:
    """Stem words in a phrase to their morphological root (e.g. 'pipelines' -> 'pipelin')."""
    tokens = re.findall(r"\b[a-zA-Z0-9+#.-]{1,25}\b", phrase.lower())
    return " ".join(stemmer.stem(t) for t in tokens)


def detect_negations(text: str) -> set[str]:
    """
    Detect negated skills like 'no machine learning background' or 'limited Python experience'.
    Returns a set of negated terms in both original and stemmed form.
    """
    normalized = normalize_text(text)
    pattern = (
        r"\b(no|not|never|without|limited|minimal|lacking|zero|little)\s+"
        r"(?:prior\s+|hands-on\s+|real-world\s+)?"
        r"(?:experience|background|knowledge|skills?)?\s*"
        r"(?:in|with|of)?\s*"
        r"([a-z0-9+#.-]+(?:\s+[a-z0-9+#.-]+)?)"
    )
    matches = re.findall(pattern, normalized)
    negated = set()
    for _, phrase in matches:
        phrase_clean = phrase.strip()
        if phrase_clean:
            negated.add(phrase_clean)
            negated.add(stem_phrase(phrase_clean))
            for part in phrase_clean.split():
                if part not in STOPWORDS and len(part) > 2:
                    negated.add(part)
                    negated.add(stemmer.stem(part))
    return negated


def extract_competencies(text: str) -> list[str]:
    """
    Dynamically extract technical competencies from text:
    1. Multi-word phrases (e.g. 'data pipelines', 'machine learning')
    2. Capitalized acronyms (e.g. ETL, AWS, GCP, SQL, API, CI/CD, DBT)
    3. Prominent technical vocabulary
    """
    norm = normalize_text(text)
    competencies = []

    # 1. Multi-word technical patterns
    cleaned_norm = norm
    for pattern in COMMON_TECH_PATTERNS:
        if pattern in cleaned_norm:
            competencies.append(pattern)
            cleaned_norm = cleaned_norm.replace(pattern, " ")

    # 2. Extract acronyms & proper tech names from raw text
    acronyms = re.findall(r"\b[A-Z][A-Z0-9+#.-]{1,15}\b", text)
    for acr in acronyms:
        acr_lower = acr.lower()
        if acr_lower not in STOPWORDS and len(acr_lower) > 1:
            competencies.append(acr_lower)

    # 3. Single words from cleaned text
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{1,25}\b", cleaned_norm)
    for w in words:
        if w not in STOPWORDS and len(w) > 2:
            competencies.append(w)

    # Return deduplicated list while preserving order
    return list(dict.fromkeys(competencies))


def match_competency_in_resume(
    comp: str,
    cand_raw_norm: str,
    cand_stemmed_norm: str,
    cand_tokens: set[str],
    cand_stemmed_tokens: set[str]
) -> bool:
    """
    Match a competency against candidate resume using:
    - Exact text match
    - Morphological Stemming (e.g. 'pipelines' matches 'pipeline', 'building' matches 'build')
    - Alias / Thesaurus mapping (e.g. 'PostgreSQL' matches 'SQL', 'PySpark' matches 'Spark')
    """
    comp_lower = comp.lower()
    comp_stemmed = stem_phrase(comp_lower)

    # Direct match
    if comp_lower in cand_tokens or comp_lower in cand_raw_norm:
        return True

    # Stemmed match
    if comp_stemmed in cand_stemmed_tokens or comp_stemmed in cand_stemmed_norm:
        return True

    # Alias / Taxonomy lookup
    # 1. Forward lookup: check if any alias of comp is in resume
    if comp_lower in TECH_ALIASES:
        for alias in TECH_ALIASES[comp_lower]:
            if alias in cand_tokens or alias in cand_raw_norm or stem_phrase(alias) in cand_stemmed_norm:
                return True

    # 2. Reverse lookup: check if any term in resume aliases to comp
    for resume_term, aliases in TECH_ALIASES.items():
        if resume_term in cand_tokens or resume_term in cand_raw_norm:
            if comp_lower in aliases or comp_stemmed in [stem_phrase(a) for a in aliases]:
                return True

    return False


def rank_resumes(job_desc: str, resumes: dict[str, str]) -> list[tuple[str, float]]:
    """
    Rank resumes using the Universal High-Accuracy NLP Engine.
    Returns list of (candidate_name, score) sorted descending by score.
    """
    detailed = screen_candidates(job_desc, resumes)
    return [(c["name"], c["score"]) for c in detailed]


def screen_candidates(job_desc: str, resumes: dict[str, str]) -> list[dict]:
    """
    Comprehensive screening engine returning detailed sub-scores and transparency metrics.
    """
    names = list(resumes.keys())
    if not names:
        return []

    job_norm = normalize_text(job_desc)
    job_competencies = extract_competencies(job_desc)

    # Context TF-IDF with sublinear scaling
    corpus = [job_desc] + [resumes[n] for n in names]
    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)
        context_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    except ValueError:
        context_scores = [0.0] * len(names)

    results = []
    for idx, name in enumerate(names):
        resume_raw = resumes[name]
        resume_norm = normalize_text(resume_raw)
        resume_stemmed_norm = stem_phrase(resume_raw)

        cand_tokens = set(re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{1,25}\b", resume_norm))
        cand_stemmed_tokens = {stemmer.stem(t) for t in cand_tokens}
        negated_set = detect_negations(resume_raw)

        # Shortcut: Identical resume to job description
        if resume_norm == job_norm:
            results.append({
                "name": name,
                "score": 1.0,
                "skill_score": 1.0,
                "context_score": 1.0,
                "matched_count": len(job_competencies),
                "total_competencies": len(job_competencies),
                "matched": job_competencies,
                "missing": [],
                "negated": []
            })
            continue

        if not job_competencies:
            score = float(context_scores[idx])
            results.append({
                "name": name,
                "score": round(score, 4),
                "skill_score": round(score, 4),
                "context_score": round(score, 4),
                "matched_count": 0,
                "total_competencies": 0,
                "matched": [],
                "missing": [],
                "negated": []
            })
            continue

        matched_comps = []
        missing_comps = []
        negated_comps = []

        for comp in job_competencies:
            comp_stemmed = stem_phrase(comp)
            is_negated = (
                comp in negated_set or
                comp_stemmed in negated_set or
                any(neg in comp for neg in negated_set if len(neg) > 2)
            )

            if is_negated:
                negated_comps.append(comp)
            elif match_competency_in_resume(comp, resume_norm, resume_stemmed_norm, cand_tokens, cand_stemmed_tokens):
                matched_comps.append(comp)
            else:
                missing_comps.append(comp)

        # Technical Skill Coverage Score
        skill_coverage = len(matched_comps) / len(job_competencies)

        # Negation Penalty (0.15 per negated core requirement, max 0.45)
        penalty = min(0.45, len(negated_comps) * 0.15)

        # Contextual Score (calibrated for real-world document lengths)
        context_sim = float(context_scores[idx])
        context_scaled = min(1.0, context_sim / 0.35)

        # Blended Scoring: 80% Technical Skill Match + 20% Calibrated Context Relevance - Penalty
        blended = (0.80 * skill_coverage + 0.20 * context_scaled) - penalty
        final_score = max(0.0, min(1.0, blended))

        results.append({
            "name": name,
            "score": round(final_score, 4),
            "skill_score": round(skill_coverage, 4),
            "context_score": round(context_sim, 4),
            "matched_count": len(matched_comps),
            "total_competencies": len(job_competencies),
            "matched": matched_comps,
            "missing": missing_comps,
            "negated": negated_comps
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def display_results(ranked: list[tuple[str, float]]) -> None:
    print("\n" + "═" * 56)
    print("  🤖  AUTOMATED RESUME SCREENING RESULTS (UNIVERSAL NLP)")
    print("═" * 56)
    print(f"  {'Rank':<6}{'Candidate':<16}{'Match Score':>12}")
    print("─" * 56)
    for rank, (name, score) in enumerate(ranked, start=1):
        bar = "█" * int(score * 30)
        print(f"  #{rank:<5}{name:<16}{score:>10.2%}  {bar}")
    print("═" * 56)
    if ranked:
        print(f"\n  ✅  Top candidate: {ranked[0][0]} with {ranked[0][1]:.2%} match\n")


# ── Sample Data ───────────────────────────────────────────────────────────

JOB_DESCRIPTION = """
We are looking for a Python Developer with experience in machine learning,
data analysis, and building REST APIs. The candidate should know scikit-learn,
pandas, NumPy, and Flask. Knowledge of SQL databases and Git is a plus.
"""

RESUMES = {
    "Piyush": """
        Python developer with 3 years of experience. Skilled in scikit-learn,
        pandas, NumPy and Flask. Built multiple RESTful APIs. Familiar with
        PostgreSQL and version control with Git.
    """,
    "Tippsy": """
        Front-end developer experienced in React, JavaScript, HTML and CSS.
        Some Python scripting knowledge. No machine learning background.
    """,
    "Suchak": """
        Data scientist with expertise in machine learning, TensorFlow, pandas,
        and NumPy. Published research in NLP. Comfortable with Python and Git.
    """,
    "Nikhil": """
        Java backend developer with Spring Boot. Limited Python experience.
        Worked with SQL databases and REST APIs extensively.
    """,
    "Riya": """
        Full-stack Python developer. Uses Flask, scikit-learn, pandas, and NumPy
        daily. Strong SQL skills, active Git user, builds data pipelines.
    """,
}


def main():
    print("Running Automated Resume Screening (Universal Engine) …")
    ranked = rank_resumes(JOB_DESCRIPTION, RESUMES)
    display_results(ranked)


if __name__ == "__main__":
    main()
