import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from main import (
    app,
    calculate_skill_dominant_matrix,
    calculate_verified_reality_score,
    compute_cosine_similarity,
    verify_github_candidate,
    CandidateExtraction,
    CapabilityReport,
    GenerateFeedbackRequest,
    MinusInterviewQuestion,
    MinusQuestionsExtraction,
    SkillTimelineItem,
)

client = TestClient(app)


def test_health_check():
    """Verify health check endpoint returns 200 and version 5.0.0."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "5.0.0"
    assert "55%" in data["scoring_matrix"]
    assert "diagnostics" in data["endpoints"]


def test_diagnostics_endpoint():
    """Verify GET /diagnostics tests all services and returns structured health report."""
    response = client.get("/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert "gemini_engine" in data["services"] or "gemini_2_5_flash" in data["services"]
    assert "supabase" in data["services"]
    assert "github_api" in data["services"]


def test_cors_headers():
    """Verify CORS headers are returned properly for preflight requests."""
    response = client.options(
        "/process-candidate",
        headers={
            "Origin": "http://localhost:8081",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8081"


def test_skill_dominant_scoring_matrix_over_50_percent():
    """
    Test the Skill-Dominant Scoring Matrix:
    - Skill & Semantic Match: 55% (> 50% dominant factor)
    - Skill Velocity: 25% (+10% boost for GitHub verified)
    - Verified Reality: 20%
    Total Skill Factors = 55% + 25% = 80.0%
    """
    timeline = [
        SkillTimelineItem(skill_name="Python", complexity_weight=4, months_to_acquire=2.0, github_verified=True),
        SkillTimelineItem(skill_name="FastAPI", complexity_weight=3, months_to_acquire=1.0, github_verified=True),
        SkillTimelineItem(skill_name="Distributed Systems", complexity_weight=5, months_to_acquire=2.0, github_verified=False),
    ]
    gh_meta = {"status": "verified", "verified_skills_count": 2}
    semantic_match = 80.0

    academic_score, reality_score, velocity_score, final_score = calculate_skill_dominant_matrix(
        cgpa=8.5,
        twelfth_grade_percentage=80.0,
        skill_timeline=timeline,
        semantic_match_score=semantic_match,
        fraud_index_score=10.0,
        github_verification=gh_meta,
    )

    assert academic_score == 82.5
    # Velocity: (4/2 + 3/1 + 5/2) = 7.5 -> normalized 75.0 -> +10% boost = 82.5
    assert velocity_score == 82.5
    # Final = (80.0 * 0.55) + (82.5 * 0.25) + (reality_score * 0.20)
    expected_final = round((80.0 * 0.55) + (82.5 * 0.25) + (reality_score * 0.20), 2)
    assert final_score == expected_final


def test_verified_reality_score_and_fraud_tanking():
    """
    Verify that Verified Reality score tanks when Gemini detects high fraud
    or when GitHub verification fails.
    """
    gh_verified = {"status": "verified", "verified_skills_count": 3}
    acad_clean, reality_clean = calculate_verified_reality_score(
        cgpa=9.0,
        twelfth_grade_percentage=90.0,
        fraud_index_score=5.0,
        github_verification=gh_verified,
    )
    assert acad_clean == 90.0
    assert reality_clean >= 80.0

    acad_fraud, reality_fraud = calculate_verified_reality_score(
        cgpa=9.0,
        twelfth_grade_percentage=90.0,
        fraud_index_score=85.0,
        github_verification=gh_verified,
    )
    assert reality_fraud < 15.0


@patch("main.get_genai_client")
def test_process_candidate_endpoint(mock_get_client):
    """Test /process-candidate endpoint with 55/25/20 response fields."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_file = MagicMock()
    mock_file.name = "files/mock-proof-of-work"
    mock_file.state = "ACTIVE"
    mock_client.files.upload.return_value = mock_file

    mock_response = MagicMock()
    mock_response.parsed = CandidateExtraction(
        candidate_name="Alex River",
        cgpa=9.0,
        twelfth_grade_percentage=88.0,
        skill_timeline=[
            SkillTimelineItem(skill_name="Python", complexity_weight=4, months_to_acquire=1.5),
            SkillTimelineItem(skill_name="PostgreSQL", complexity_weight=3, months_to_acquire=1.0),
        ],
        fraud_index_score=12.5,
        experience_summary="Engineered event-driven microservices using Python and PostgreSQL.",
    )
    mock_response.text = None
    mock_client.models.generate_content.return_value = mock_response

    mock_embed = MagicMock()
    mock_content_embed = MagicMock()
    mock_content_embed.values = [0.1, 0.2, 0.3, 0.4]
    mock_embed.embeddings = [mock_content_embed]
    mock_client.models.embed_content.return_value = mock_embed

    files = {"file": ("demo.mp4", b"mock-video-bytes", "video/mp4")}
    data = {
        "job_description": "Senior Python Backend Engineer building distributed APIs with PostgreSQL.",
        "github_username": "alexriver",
    }

    mock_gh_repos = [
        {"name": "async-python-service", "language": "Python", "topics": ["postgresql", "api"]},
    ]
    mock_gh_resp = MagicMock()
    mock_gh_resp.status_code = 200
    mock_gh_resp.json.return_value = mock_gh_repos

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_gh_resp
        response = client.post("/process-candidate", files=files, data=data)

    assert response.status_code == 200
    res_data = response.json()

    assert res_data["candidate_name"] == "Alex River"
    assert "academic_score" in res_data
    assert "verified_reality_score" in res_data
    assert "skill_velocity_score" in res_data
    assert "semantic_match_score" in res_data
    assert "final_score" in res_data


@patch("main.get_genai_client")
def test_generate_feedback_rule_a(mock_get_client):
    """
    Test Rule A: High Academics (>=70), Low Coding (<60).
    AI suggests study habits are good, but needs to stop reading theory and push to GitHub.
    """
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.parsed = CapabilityReport(
        is_capable=False,
        strongest_area="Academic excellence and strong theoretical mastery.",
        weakest_area="Absence of real-world production coding and portfolio projects.",
        actionable_advice="You have good study habits and academic aptitude, but you must stop just reading theory and immediately start building real-world projects and pushing code to GitHub.",
    )
    mock_response.text = None
    mock_client.models.generate_content.return_value = mock_response

    payload = {
        "candidate_name": "David Scholar",
        "academic_score": 92.0,
        "semantic_match_score": 42.0,
        "skill_velocity_score": 50.0,
        "passing_threshold": 70.0,
    }

    response = client.post("/generate-feedback", json=payload)
    assert response.status_code == 200
    res_data = response.json()

    assert res_data["candidate_name"] == "David Scholar"
    assert res_data["capability_report"]["is_capable"] is False
    assert "pushing code to GitHub" in res_data["capability_report"]["actionable_advice"]


@patch("main.get_genai_client")
def test_generate_feedback_rule_b(mock_get_client):
    """
    Test Rule B: High Coding (>=70), Low Academics (<60).
    AI praises practical skills, but warns about missing CS fundamentals and recommends DS/algo review.
    """
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.parsed = CapabilityReport(
        is_capable=True,
        strongest_area="Exceptional hands-on framework proficiency and practical coding execution.",
        weakest_area="Gaps in core academic computer science fundamentals.",
        actionable_advice="Outstanding practical coding capabilities! However, you lack core computer science fundamentals. We recommend reviewing basic educational concepts like data structures, algorithms, and system design.",
    )
    mock_response.text = None
    mock_client.models.generate_content.return_value = mock_response

    payload = {
        "candidate_name": "Sam Hacker",
        "academic_score": 45.0,
        "semantic_match_score": 90.0,
        "skill_velocity_score": 85.0,
        "final_score": 75.0,
        "passing_threshold": 70.0,
    }

    response = client.post("/generate-feedback", json=payload)
    assert response.status_code == 200
    res_data = response.json()

    assert res_data["candidate_name"] == "Sam Hacker"
    assert res_data["capability_report"]["is_capable"] is True
    assert "computer science fundamentals" in res_data["capability_report"]["actionable_advice"]


@patch("main.get_genai_client")
def test_generate_minus_questions_endpoint(mock_get_client):
    """Test /generate-minus-questions endpoint ensuring exactly 7 strict archetypes."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    strict_questions = [
        MinusInterviewQuestion(
            category_number=i,
            category_name=f"Category {i}",
            target_focus=f"Focus {i}",
            question=f"Question {i}?",
            evaluation_criteria=f"Criteria {i}",
        )
        for i in range(1, 8)
    ]

    mock_response = MagicMock()
    mock_response.parsed = MinusQuestionsExtraction(questions=strict_questions)
    mock_response.text = None
    mock_client.models.generate_content.return_value = mock_response

    payload = {
        "candidate_name": "Alex River",
        "experience_summary": "Built event-driven backend systems with Python.",
        "skill_timeline": [
            {"skill_name": "Python", "complexity_weight": 4, "months_to_acquire": 2.0, "github_verified": True},
        ],
        "fraud_index_score": 10.0,
        "github_verification": {"verified_skills_count": 1},
        "job_description": "Senior Platform Engineer responsible for multi-tenant microservices.",
    }

    response = client.post("/generate-minus-questions", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["total_questions"] == 7


if __name__ == "__main__":
    test_health_check()
    test_diagnostics_endpoint()
    test_cors_headers()
    test_skill_dominant_scoring_matrix_over_50_percent()
    test_verified_reality_score_and_fraud_tanking()
    test_process_candidate_endpoint()
    test_generate_feedback_rule_a()
    test_generate_feedback_rule_b()
    test_generate_minus_questions_endpoint()
    print("✓ All Next-Gen ATS Backend tests passed successfully!")
