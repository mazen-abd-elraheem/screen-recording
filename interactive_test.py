"""
Interactive Resume Screening CLI Tool
Allows you to test custom job descriptions and resumes with live scoring and keyword analysis.
"""

import os
import sys
from main import rank_resumes
from resume_parser import analyze_keyword_matches, extract_text_from_file

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


PRESET_SCENARIOS = {
    "1": {
        "title": "Python Machine Learning Engineer",
        "job_desc": (
            "We are looking for a Python Machine Learning Engineer with deep experience in "
            "scikit-learn, TensorFlow, pandas, and NumPy. Experience building REST APIs with Flask "
            "or FastAPI, SQL databases, Docker, and Git is required."
        ),
        "resumes": {
            "Ahmed": "Machine learning engineer with 4 years experience in Python, scikit-learn, pandas, NumPy, Docker and Flask APIs.",
            "Sarah": "Full stack developer specializing in React, TypeScript, Node.js, and CSS. Minimal Python knowledge.",
            "Omar": "Data Scientist skilled in Python, SQL, pandas, machine learning, statistics, and version control with Git.",
            "Laila": "DevOps engineer experienced in Kubernetes, Docker, CI/CD pipelines, AWS and bash scripting."
        }
    },
    "2": {
        "title": "Frontend React / Next.js Developer",
        "job_desc": (
            "Seeking a Frontend Developer skilled in React, TypeScript, Next.js, Tailwind CSS, "
            "and state management with Redux. Must have experience with responsive web design and REST APIs."
        ),
        "resumes": {
            "Mona": "Frontend Engineer with 3 years of React, Next.js, TypeScript, and Tailwind CSS. Built responsive web applications.",
            "Kareem": "Backend developer specializing in Java Spring Boot, PostgreSQL, and microservices architecture.",
            "Zainab": "UI/UX designer and web developer proficient in HTML, CSS, JavaScript, and Figma to React conversion."
        }
    }
}


def print_banner():
    print("\n" + "═" * 60)
    print("  🚀  AUTOMATED RESUME SCREENING - INTERACTIVE TESTER")
    print("═" * 60)


def display_detailed_results(job_desc: str, ranked: list[tuple[str, float]], resumes: dict[str, str]):
    print("\n" + "═" * 60)
    print("  📊 SCREENING RESULTS & RANKINGS")
    print("═" * 60)
    print(f"  {'Rank':<6}{'Candidate':<15}{'Score':>10}   {'Visual Match':<15}")
    print("─" * 60)

    for rank, (name, score) in enumerate(ranked, start=1):
        bar_len = int(score * 25)
        bar = "█" * bar_len + "░" * (25 - bar_len)
        badge = "🏆 TOP MATCH" if rank == 1 and score > 0 else f"Rank #{rank}"
        print(f"  #{rank:<5}{name:<15}{score:>9.2%}   [{bar}]")

        # Keyword analysis
        analysis = analyze_keyword_matches(job_desc, resumes[name], top_n=6)
        matched_str = ", ".join(analysis["matched"]) if analysis["matched"] else "None"
        missing_str = ", ".join(analysis["missing"]) if analysis["missing"] else "None"
        print(f"        ✓ Matched:  {matched_str}")
        print(f"        ✗ Missing:  {missing_str}")
        print("─" * 60)

    if ranked:
        print(f"\n  🎉 Winner / Top Candidate: {ranked[0][0]} with {ranked[0][1]:.2%} match!\n")


def run_presets():
    print("\nChoose a preset job role:")
    for key, data in PRESET_SCENARIOS.items():
        print(f"  [{key}] {data['title']}")
    choice = input("\nEnter choice (1 or 2): ").strip()
    if choice in PRESET_SCENARIOS:
        scenario = PRESET_SCENARIOS[choice]
        print(f"\n📌 Selected: {scenario['title']}")
        print(f"Job Description:\n{scenario['job_desc']}\n")
        ranked = rank_resumes(scenario["job_desc"], scenario["resumes"])
        display_detailed_results(scenario["job_desc"], ranked, scenario["resumes"])
    else:
        print("Invalid option.")


def run_custom_text():
    print("\n" + "─" * 50)
    print("Enter or paste your Job Description:")
    print("(Press ENTER twice when finished)")
    lines = []
    while True:
        line = input()
        if not line and lines:
            break
        if line:
            lines.append(line)
    job_desc = "\n".join(lines).strip()
    if not job_desc:
        print("Job description cannot be empty.")
        return

    resumes = {}
    print("\nNow enter candidate resumes (type 'done' as candidate name when finished):")
    while True:
        name = input("\nCandidate Name (or 'done'): ").strip()
        if name.lower() == 'done' or not name:
            if not resumes:
                print("At least one candidate is needed.")
                continue
            break

        print(f"Enter or paste resume text for '{name}':")
        print("(Press ENTER twice when finished)")
        res_lines = []
        while True:
            r_line = input()
            if not r_line and res_lines:
                break
            if r_line:
                res_lines.append(r_line)
        res_text = "\n".join(res_lines).strip()
        if res_text:
            resumes[name] = res_text
            print(f"✓ Added '{name}'")
        else:
            print("Resume text was empty, skipped.")

    if resumes:
        ranked = rank_resumes(job_desc, resumes)
        display_detailed_results(job_desc, ranked, resumes)


def run_real_files():
    print("\n" + "─" * 50)
    print("Scan resumes from a folder (supports .pdf, .docx, .txt):")
    folder_path = input("Enter directory path (e.g. ./sample_resumes): ").strip()
    if not os.path.isdir(folder_path):
        print(f"Directory '{folder_path}' does not exist.")
        return

    job_desc = input("\nEnter short Job Description / Requirements:\n").strip()
    if not job_desc:
        print("Job description cannot be empty.")
        return

    resumes = {}
    valid_exts = (".pdf", ".docx", ".txt", ".md")
    for fname in os.listdir(folder_path):
        if any(fname.lower().endswith(ext) for ext in valid_exts):
            full_path = os.path.join(folder_path, fname)
            try:
                text = extract_text_from_file(full_path, fname)
                if text.strip():
                    candidate_name = os.path.splitext(fname)[0]
                    resumes[candidate_name] = text
                    print(f"  ✓ Loaded: {fname} ({len(text)} chars)")
            except Exception as e:
                print(f"  ✗ Failed to read {fname}: {e}")

    if not resumes:
        print("No valid resume files found in that folder.")
        return

    ranked = rank_resumes(job_desc, resumes)
    display_detailed_results(job_desc, ranked, resumes)


def main():
    while True:
        print_banner()
        print("  1. Run Preset Job Scenarios (Machine Learning / Frontend)")
        print("  2. Test with Custom Job Description & Paste Resumes")
        print("  3. Screen Real Resume Files (.pdf, .docx, .txt) from a folder")
        print("  4. Exit")
        choice = input("\nSelect an option [1-4]: ").strip()

        if choice == "1":
            run_presets()
        elif choice == "2":
            run_custom_text()
        elif choice == "3":
            run_real_files()
        elif choice == "4":
            print("\nGoodbye! 👋\n")
            break
        else:
            print("Please enter a number between 1 and 4.")


if __name__ == "__main__":
    main()
