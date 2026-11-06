import pytest
from main import rank_resumes, screen_candidates, display_results, JOB_DESCRIPTION, RESUMES


class TestResumeScreening:
    def test_default_dataset_ranking(self):
        """Test default job description and resumes rankings."""
        ranked = rank_resumes(JOB_DESCRIPTION, RESUMES)
        
        # Verify all candidates are accounted for
        candidate_names = [name for name, _ in ranked]
        assert set(candidate_names) == set(RESUMES.keys())
        assert len(ranked) == len(RESUMES)
        
        # Piyush is top candidate with strong Python/ML match
        assert ranked[0][0] == "Piyush"
        assert ranked[0][1] >= 0.55

    def test_ranking_is_sorted_descending(self):
        """Verify scores are in descending order."""
        ranked = rank_resumes(JOB_DESCRIPTION, RESUMES)
        scores = [score for _, score in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_scores_are_within_valid_bounds(self):
        """Verify all scores are strictly between 0.0 and 1.0."""
        ranked = rank_resumes(JOB_DESCRIPTION, RESUMES)
        for name, score in ranked:
            assert 0.0 <= score <= 1.0, f"Score for {name} ({score}) out of bounds [0, 1]"

    def test_perfect_match_score(self):
        """A resume that matches the job description exactly should achieve 1.0."""
        job = "Python Machine Learning Data Science SQL Docker"
        resumes = {
            "PerfectCandidate": "Python Machine Learning Data Science SQL Docker",
            "UnrelatedCandidate": "Cooking Baking Pastry French Cuisine Culinary",
        }
        ranked = rank_resumes(job, resumes)
        scores_dict = dict(ranked)

        assert scores_dict["PerfectCandidate"] == pytest.approx(1.0, rel=1e-3)
        assert scores_dict["UnrelatedCandidate"] == pytest.approx(0.0, abs=1e-3)
        assert ranked[0][0] == "PerfectCandidate"

    def test_stemming_variation_matching(self):
        """Verify that morphological variations (pipelines vs pipeline, building vs built) match."""
        job = "Experience building data pipelines and managing relational databases."
        resumes = {
            "StemmedMatch": "Built scalable data pipeline architecture with relational database management.",
            "Unrelated": "Gardening flowers plants landscaping."
        }
        ranked = rank_resumes(job, resumes)
        assert ranked[0][0] == "StemmedMatch"
        assert ranked[0][1] >= 0.70

    def test_data_engineering_domain(self):
        """Verify screening on real Data Engineering skills (Airflow, Spark, Kafka, SQL, ETL)."""
        job = """
        Looking for a Data Engineer with Apache Airflow, PySpark, Kafka, and SQL experience.
        Must build ETL data pipelines and deploy on AWS.
        """
        resumes = {
            "Mazen": "Data Engineer experienced in building ETL data pipelines with PySpark, Kafka streaming, and Airflow. Expert in PostgreSQL and AWS.",
            "FrontendDev": "Frontend developer with React, TypeScript, and Tailwind CSS. No data engineering or distributed systems experience."
        }
        detailed = screen_candidates(job, resumes)
        mazen_res = next(c for c in detailed if c["name"] == "Mazen")
        frontend_res = next(c for c in detailed if c["name"] == "FrontendDev")

        assert mazen_res["score"] >= 0.80
        assert mazen_res["skill_score"] >= 0.80
        assert frontend_res["score"] < 0.20
        assert len(frontend_res["negated"]) > 0

    def test_negation_penalty_applied(self):
        """
        Verify that saying 'No machine learning background' penalizes the candidate
        compared to an otherwise similar candidate without that negative statement.
        """
        job = "Machine learning engineer with Python and TensorFlow experience."
        resumes = {
            "PositiveCandidate": "Python developer with machine learning and TensorFlow experience.",
            "NegatedCandidate": "Python developer. No machine learning background. Limited TensorFlow knowledge."
        }
        ranked = rank_resumes(job, resumes)
        scores = dict(ranked)
        
        assert scores["PositiveCandidate"] > scores["NegatedCandidate"]
        assert scores["NegatedCandidate"] < 0.25

    def test_relative_qualification_ranking(self):
        """Candidate with more relevant keywords should rank strictly higher."""
        job = "Looking for Senior React developer proficient with TypeScript, Next.js, and CSS."
        resumes = {
            "CandidateHigh": "Senior React and TypeScript developer with extensive Next.js and modern CSS experience.",
            "CandidateMedium": "Junior React developer with basic JavaScript and CSS.",
            "CandidateLow": "Java backend developer with Spring Boot and Oracle database.",
        }
        ranked = rank_resumes(job, resumes)
        
        names_order = [name for name, _ in ranked]
        assert names_order[0] == "CandidateHigh"
        assert names_order[1] == "CandidateMedium"
        assert names_order[2] == "CandidateLow"

    def test_single_candidate(self):
        """Test screening when only one candidate is provided."""
        job = "Data Analyst Python SQL Tableau"
        resumes = {"Alice": "Python and SQL data analysis"}
        ranked = rank_resumes(job, resumes)
        assert len(ranked) == 1
        assert ranked[0][0] == "Alice"
        assert ranked[0][1] > 0.0

    def test_display_results_runs_without_error(self, capsys):
        """Verify display_results executes cleanly and prints expected output."""
        ranked = [("CandidateA", 0.854), ("CandidateB", 0.421)]
        display_results(ranked)
        captured = capsys.readouterr().out
        assert "AUTOMATED RESUME SCREENING RESULTS" in captured
        assert "CandidateA" in captured
        assert "CandidateB" in captured
        assert "85.40%" in captured
        assert "Top candidate: CandidateA" in captured
