import math
import mimetypes
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from google.genai.errors import APIError
import httpx
from pydantic import BaseModel, Field
from supabase import Client, create_client

# Load environment variables from .env if present
load_dotenv()

# Initialize FastAPI application
app = FastAPI(
    title="Next-Gen AI Applicant Tracking System (ATS) API",
    description=(
        "Multimodal temporal ingestion, strict reality verification, async GitHub audit, "
        "pgvector semantic matching, 55/25/20 Skill-Dominant scoring, and 7-Archetype Minus interview generation."
    ),
    version="5.0.0",
)

# ---------------------------------------------------------------------------
# CORS Middleware Configuration
# Configured for seamless React Native/Expo integration (web, emulator, physical devices)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Client Providers (Gemini & Supabase)
# ---------------------------------------------------------------------------
def get_genai_client() -> genai.Client:
    """Instantiate and return the Google GenAI client using GEMINI_API_KEY."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Gemini API key not configured. Please set GEMINI_API_KEY or "
                "GOOGLE_API_KEY in your environment or .env file."
            ),
        )
    return genai.Client(api_key=api_key)


def get_supabase_client() -> Optional[Client]:
    """
    Returns Supabase client if SUPABASE_URL and SUPABASE_KEY are provided.
    Gracefully returns None if not configured.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if url and key and not url.startswith("https://your-project"):
        try:
            return create_client(url, key)
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class SkillTimelineItem(BaseModel):
    """
    Temporal skill acquisition item extracted from the candidate's history.
    """
    skill_name: str = Field(..., description="Name of the technology or skill.")
    complexity_weight: int = Field(
        ...,
        ge=1,
        le=5,
        description="Technical complexity weight on a 1 (basic) to 5 (advanced architecture) scale.",
    )
    months_to_acquire: float = Field(
        ...,
        ge=0.1,
        description="Estimated months candidate took to acquire/master this skill.",
    )
    github_verified: bool = Field(
        default=False,
        description="Whether this skill has been verified against active GitHub repositories.",
    )


class CandidateExtraction(BaseModel):
    """
    Structured extraction schema passed to Gemini 2.5 Flash.
    """
    candidate_name: str = Field(..., description="Full name of candidate.")
    cgpa: float = Field(
        ...,
        description=(
            "Candidate's Cumulative Grade Point Average (CGPA) on a 10.0 scale. "
            "Convert 4.0 scales to 10.0 proportionally. If not found, return 0.0."
        ),
    )
    twelfth_grade_percentage: float = Field(
        ...,
        description="Candidate's 12th grade / Senior Secondary percentage (0.0 to 100.0). If not found, return 0.0.",
    )
    skill_timeline: List[SkillTimelineItem] = Field(
        default_factory=list,
        description="List of skills with complexity weight (1-5) and months to acquire.",
    )
    fraud_index_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Strict auditor evaluation of keyword stuffing, timeline anomalies, "
            "or inflated claims without contextual proof-of-work (0=authentic, 100=pure fluff/fraud)."
        ),
    )
    experience_summary: str = Field(
        ...,
        description="Dense synthesis of practical project accomplishments, work experience, and architectural depth.",
    )


class ProcessCandidateResponse(BaseModel):
    """
    Full evaluated response returned to the frontend.
    """
    candidate_name: str
    cgpa: float
    twelfth_grade_percentage: float
    skill_timeline: List[SkillTimelineItem]
    fraud_index_score: float
    experience_summary: str
    github_verification: Dict[str, Any]
    academic_score: float
    verified_reality_score: float
    skill_velocity_score: float
    semantic_match_score: float
    final_score: float
    job_description_summary: str


class MinusInterviewQuestion(BaseModel):
    """
    A single mock interview question corresponding to one of the 7 strict archetypes.
    """
    category_number: int = Field(..., ge=1, le=7, description="Category index 1 through 7.")
    category_name: str = Field(
        ...,
        description="One of the strict 7 Minus archetypes.",
    )
    target_focus: str = Field(
        ...,
        description="Specific project, framework, repo, metric, or transition being scrutinized.",
    )
    question: str = Field(
        ...,
        description="In-depth, highly technical question targeted specifically at the candidate.",
    )
    evaluation_criteria: str = Field(
        ...,
        description="Technical bar, architectural trade-offs, and details expected in a strong answer.",
    )


class MinusQuestionsExtraction(BaseModel):
    """
    Enforces Gemini 2.5 Flash to output exactly 7 structured questions.
    """
    questions: List[MinusInterviewQuestion] = Field(
        ...,
        min_length=7,
        max_length=7,
        description="Strictly 7 questions covering all required categories.",
    )


class GenerateMinusQuestionsRequest(BaseModel):
    """
    Request payload for generating the 7-archetype Minus interview questions.
    """
    candidate_name: str
    experience_summary: str
    skill_timeline: List[SkillTimelineItem]
    fraud_index_score: float = 0.0
    github_verification: Optional[Dict[str, Any]] = Field(default_factory=dict)
    job_description: str


class GenerateMinusQuestionsResponse(BaseModel):
    """
    Response returned with the strict 7 Minus interview questions.
    """
    candidate_name: str
    total_questions: int = 7
    questions: List[MinusInterviewQuestion]


class CapabilityReport(BaseModel):
    """
    Personalized capability and upskill report generated by Gemini 2.5 Flash.
    """
    is_capable: bool = Field(
        ...,
        description="Whether candidate's composite score clears the dynamic capability threshold.",
    )
    strongest_area: str = Field(
        ...,
        description="What the candidate demonstrated highest proficiency in.",
    )
    weakest_area: str = Field(
        ...,
        description="The primary gap or deficiency hindering candidate's capability.",
    )
    actionable_advice: str = Field(
        ...,
        description="Rule-governed custom upskill recommendation (enforcing Rule A or Rule B).",
    )


class GenerateFeedbackRequest(BaseModel):
    """
    Request payload for the Candidate Feedback & Upskill Engine.
    """
    candidate_name: str = Field(..., description="Full name of candidate.")
    academic_score: float = Field(
        ..., ge=0.0, le=100.0, description="Academic sub-score (0-100)."
    )
    semantic_match_score: float = Field(
        ..., ge=0.0, le=100.0, description="Coding / semantic match sub-score (0-100)."
    )
    skill_velocity_score: float = Field(
        ..., ge=0.0, le=100.0, description="Skill acquisition velocity sub-score (0-100)."
    )
    verified_reality_score: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Proof-of-work reality sub-score (0-100)."
    )
    final_score: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Composite weighted score (0-100)."
    )
    passing_threshold: float = Field(
        default=70.0,
        ge=0.0,
        le=100.0,
        description="Dynamic capability threshold percentage (default 70.0%).",
    )


class GenerateFeedbackResponse(BaseModel):
    """
    Response payload from the Candidate Feedback & Upskill Engine.
    """
    candidate_name: str
    passing_threshold: float
    final_score: float
    capability_report: CapabilityReport


# ---------------------------------------------------------------------------
# Helper Utility Functions
# ---------------------------------------------------------------------------
def normalize_token(text: str) -> str:
    """Normalize a skill or technology name for robust matching."""
    return "".join(c.lower() for c in text.strip() if c.isalnum() or c in ("+", "#", "."))


def resolve_mime_type(upload_file: UploadFile) -> str:
    """
    Determine MIME type across documents (.pdf, .docx, .txt), images, and videos (.mp4, .mov).
    """
    if upload_file.content_type and upload_file.content_type != "application/octet-stream":
        return upload_file.content_type

    filename = upload_file.filename or "resume.pdf"
    guessed_type, _ = mimetypes.guess_type(filename)
    if guessed_type:
        return guessed_type

    ext = os.path.splitext(filename)[1].lower()
    mapping = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
    }
    return mapping.get(ext, "application/pdf")


# ---------------------------------------------------------------------------
# Engine 1: Asynchronous GitHub Verification Engine
# ---------------------------------------------------------------------------
async def verify_github_candidate(
    username: Optional[str],
    skill_timeline: List[SkillTimelineItem],
) -> tuple[List[SkillTimelineItem], Dict[str, Any]]:
    """
    Asynchronously queries GitHub REST API for candidate's repositories.
    Cross-references repository languages and topics with extracted skill timeline.
    Sets github_verified = True on matching skills.
    """
    if not username or not username.strip():
        return skill_timeline, {
            "username": None,
            "status": "not_provided",
            "verified_skills_count": 0,
            "repositories_analyzed": 0,
            "detected_languages": [],
        }

    clean_user = username.strip().lstrip("@")
    url = f"https://api.github.com/users/{clean_user}/repos"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-ATS-Verification-Engine/5.0",
    }

    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    detected_languages = set()
    detected_topics = set()
    repos_analyzed = 0

    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            resp = await http_client.get(
                url,
                headers=headers,
                params={"per_page": 100, "sort": "pushed"},
            )

        if resp.status_code == 200:
            repos_data = resp.json()
            repos_analyzed = len(repos_data)
            for repo in repos_data:
                lang = repo.get("language")
                if lang:
                    detected_languages.add(lang.strip().lower())
                topics = repo.get("topics") or []
                for t in topics:
                    detected_topics.add(t.strip().lower())
                repo_name = repo.get("name") or ""
                detected_topics.add(repo_name.lower())

            # Match against skill timeline
            verified_count = 0
            for skill in skill_timeline:
                norm_skill = normalize_token(skill.skill_name)
                matched = any(
                    norm_skill == normalize_token(lang)
                    or norm_skill in normalize_token(lang)
                    or normalize_token(lang) in norm_skill
                    for lang in detected_languages
                ) or any(
                    norm_skill == normalize_token(top)
                    or norm_skill in normalize_token(top)
                    or normalize_token(top) in norm_skill
                    for top in detected_topics
                )
                if matched:
                    skill.github_verified = True
                    verified_count += 1

            return skill_timeline, {
                "username": clean_user,
                "status": "verified",
                "repositories_analyzed": repos_analyzed,
                "detected_languages": sorted(list(detected_languages)),
                "detected_topics": sorted(list(detected_topics))[:20],
                "verified_skills_count": verified_count,
            }
        elif resp.status_code == 404:
            return skill_timeline, {
                "username": clean_user,
                "status": "user_not_found",
                "verified_skills_count": 0,
                "repositories_analyzed": 0,
                "detected_languages": [],
            }
        else:
            return skill_timeline, {
                "username": clean_user,
                "status": f"github_api_status_{resp.status_code}",
                "verified_skills_count": 0,
                "repositories_analyzed": 0,
                "detected_languages": [],
            }
    except Exception as exc:
        return skill_timeline, {
            "username": clean_user,
            "status": "verification_error",
            "error_detail": str(exc),
            "verified_skills_count": 0,
            "repositories_analyzed": 0,
            "detected_languages": [],
        }


# ---------------------------------------------------------------------------
# Engine 2: Semantic Matching Engine (Cosine Similarity & Supabase)
# ---------------------------------------------------------------------------
def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Computes cosine similarity between two float vectors and converts to a 0-100% score.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    similarity = dot / (norm_a * norm_b)
    score = max(0.0, min(100.0, round(similarity * 100.0, 2)))
    return score


def generate_content_with_fallback(
    client: genai.Client,
    contents: Any,
    config: Optional[types.GenerateContentConfig] = None,
) -> types.GenerateContentResponse:
    """
    Attempts generation with primary model (gemini-2.5-flash) and automatically
    falls back to gemini-3.6-flash if Google's API returns a 404 / no longer available.
    """
    models_to_try = [
        os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "gemini-3.6-flash",
    ]
    last_err = None
    for model_name in models_to_try:
        try:
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            last_err = exc
            if "404" in str(exc) or "no longer available" in str(exc) or "NOT_FOUND" in str(exc):
                continue
            raise exc
    raise last_err


def generate_vector_embedding(client: genai.Client, text: str) -> List[float]:
    """
    Generates high-dimensional vector embedding using text-embedding-004,
    falling back automatically to gemini-embedding-2 if Google API returns 404.
    """
    truncated_text = text[:8000] if len(text) > 8000 else text
    models_to_try = [
        os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004"),
        "gemini-embedding-2",
    ]
    last_err = None
    for model_name in models_to_try:
        try:
            res = client.models.embed_content(
                model=model_name,
                contents=truncated_text,
            )
            if res.embeddings and len(res.embeddings) > 0:
                return res.embeddings[0].values
        except Exception as exc:
            last_err = exc
            if "404" in str(exc) or "NOT_FOUND" in str(exc):
                continue
            raise exc
    if last_err:
        raise last_err
    return []


async def calculate_semantic_similarity(
    client: genai.Client,
    candidate_profile_text: str,
    job_description_text: str,
    supabase_client: Optional[Client] = None,
) -> float:
    """
    Generates embeddings for candidate profile and job description,
    optionally records pgvector data in Supabase, and calculates cosine similarity.
    """
    cand_vec = generate_vector_embedding(client, candidate_profile_text)
    jd_vec = generate_vector_embedding(client, job_description_text)

    score = compute_cosine_similarity(cand_vec, jd_vec)

    # Optional Supabase pgvector persistence if table exists
    if supabase_client and cand_vec:
        try:
            supabase_client.table("candidate_embeddings").insert(
                {
                    "profile_snippet": candidate_profile_text[:500],
                    "job_description_snippet": job_description_text[:500],
                    "similarity_score": score,
                    "created_at": "now()",
                }
            ).execute()
        except Exception:
            pass

    return score


# ---------------------------------------------------------------------------
# Engine 3: 55/25/20 Skill-Dominant Scoring Matrix (Skill Factor > 50%)
# ---------------------------------------------------------------------------
def calculate_verified_reality_score(
    cgpa: float,
    twelfth_grade_percentage: float,
    fraud_index_score: float,
    github_verification: Dict[str, Any],
) -> tuple[float, float]:
    """
    Calculates raw academic score and the fraud/GitHub-adjusted 'Verified Reality' score.
    If Gemini detects high fraud or GitHub doesn't match the resume, this score tanks.
    """
    # 1. Base academic score (0-100)
    academic_base = ((cgpa / 10.0) * 50.0) + (twelfth_grade_percentage * 0.5)
    academic_base = max(0.0, min(100.0, round(academic_base, 2)))

    # 2. Fraud Index Factor (0.0 to 1.0)
    # 0 fraud index = 1.0 authenticity; 100 fraud index = 0.0 authenticity (tanks completely)
    authenticity_factor = max(0.0, min(1.0, (100.0 - fraud_index_score) / 100.0))

    # Severe fraud penalty: If fraud index > 60%, halve authenticity factor
    if fraud_index_score > 60.0:
        authenticity_factor = authenticity_factor * 0.5

    # 3. GitHub Verification Factor (0.25 to 1.0)
    status_val = github_verification.get("status")
    verified_count = github_verification.get("verified_skills_count", 0)

    if status_val == "verified":
        if verified_count > 0:
            github_factor = min(1.0, 0.70 + 0.10 * min(3, verified_count))
        else:
            github_factor = 0.35
    elif status_val == "user_not_found":
        github_factor = 0.25
    else:
        github_factor = 0.75

    verified_reality = academic_base * authenticity_factor * github_factor
    verified_reality_score = max(0.0, min(100.0, round(verified_reality, 2)))

    return academic_base, verified_reality_score


def calculate_skill_dominant_matrix(
    cgpa: float,
    twelfth_grade_percentage: float,
    skill_timeline: List[SkillTimelineItem],
    semantic_match_score: float,
    fraud_index_score: float,
    github_verification: Dict[str, Any],
) -> tuple[float, float, float, float]:
    """
    Skill-Dominant Scoring Matrix (> 50% Skill Emphasis):
    - Skill & Semantic Match: 55% (Over 50% as requested)
    - Skill Velocity: 25% (With 10% boost if github_verified)
    - Verified Reality: 20% (Academics & Proof of Work, penalized by fraud/mismatch)
    Total Skill Factors = 55% + 25% = 80%!
    """
    academic_score, verified_reality_score = calculate_verified_reality_score(
        cgpa=cgpa,
        twelfth_grade_percentage=twelfth_grade_percentage,
        fraud_index_score=fraud_index_score,
        github_verification=github_verification,
    )

    # Skill Velocity Score (out of 100)
    raw_velocity = 0.0
    for item in skill_timeline:
        months = max(item.months_to_acquire, 0.5)
        raw_velocity += float(item.complexity_weight) / months

    benchmark = 10.0
    normalized_velocity = min(100.0, (raw_velocity / benchmark) * 100.0)

    # 10% boost if skills are verified on GitHub
    has_github_verified = any(item.github_verified for item in skill_timeline)
    if has_github_verified:
        normalized_velocity = min(100.0, normalized_velocity * 1.10)

    skill_velocity_score = round(normalized_velocity, 2)

    # 55% Skill Semantic Match + 25% Skill Velocity + 20% Verified Reality
    final = (
        (semantic_match_score * 0.55)
        + (skill_velocity_score * 0.25)
        + (verified_reality_score * 0.20)
    )
    final_score = round(final, 2)

    return academic_score, verified_reality_score, skill_velocity_score, final_score


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
async def health_check():
    """Health check and Next-Gen ATS API capabilities overview."""
    gemini_key_present = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    supabase_configured = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))
    return {
        "service": "Next-Gen AI ATS Backend",
        "version": "5.0.0",
        "status": "healthy",
        "gemini_status": "ready" if gemini_key_present else "api_key_required",
        "model": "gemini-2.5-flash",
        "embedding_model": "text-embedding-004",
        "scoring_matrix": "55% Skill/Semantic Match + 25% Skill Velocity + 20% Verified Reality",
        "skill_factor_percentage": "55% (Core Skill) + 25% (Skill Velocity) = 80% Total Skill Weight",
        "supabase_pgvector": "configured" if supabase_configured else "in-memory-fallback",
        "endpoints": {
            "health": "GET /",
            "diagnostics": "GET /diagnostics",
            "process_candidate": "POST /process-candidate",
            "generate_minus_questions": "POST /generate-minus-questions",
            "generate_feedback": "POST /generate-feedback",
        },
    }


@app.get("/diagnostics", tags=["System Diagnostics"])
async def run_diagnostics():
    """
    Live Diagnostic Engine:
    Actively checks and tests:
    1. Gemini 2.5 Flash Engine connectivity & prompt execution.
    2. Gemini text-embedding-004 vector embedding engine.
    3. Supabase connectivity & pgvector database state.
    4. GitHub API network reachability.
    """
    diag_results: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall_status": "ok",
        "services": {},
    }

    # 1. Check Gemini Engine
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        diag_results["services"]["gemini_2_5_flash"] = {
            "status": "unconfigured",
            "message": "GEMINI_API_KEY not found in environment or .env file. Export GEMINI_API_KEY='your_key' to enable.",
        }
        diag_results["services"]["gemini_embeddings"] = {
            "status": "unconfigured",
            "message": "GEMINI_API_KEY not found.",
        }
        diag_results["overall_status"] = "partially_degraded"
    else:
        try:
            start_t = time.time()
            client = genai.Client(api_key=api_key)
            test_resp = generate_content_with_fallback(
                client=client,
                contents="Ping. Respond with exactly the single word: PONG",
            )
            elapsed = round((time.time() - start_t) * 1000, 2)
            diag_results["services"]["gemini_engine"] = {
                "status": "active_and_operational",
                "model": os.getenv("GEMINI_MODEL", "gemini-3.6-flash / gemini-2.5-flash"),
                "response": test_resp.text.strip() if test_resp.text else "OK",
                "latency_ms": elapsed,
            }
        except Exception as e:
            diag_results["services"]["gemini_engine"] = {
                "status": "error",
                "error_detail": str(e),
            }
            diag_results["overall_status"] = "partially_degraded"

        # Check Gemini Embeddings
        try:
            start_t = time.time()
            cand_vec = generate_vector_embedding(client, "AI ATS diagnostic verification embedding")
            elapsed = round((time.time() - start_t) * 1000, 2)
            dim = len(cand_vec)
            diag_results["services"]["gemini_embeddings"] = {
                "status": "active_and_operational",
                "model": os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2 / text-embedding-004"),
                "vector_dimensions": dim,
                "latency_ms": elapsed,
            }
        except Exception as e:
            diag_results["services"]["gemini_embeddings"] = {
                "status": "error",
                "error_detail": str(e),
            }
            diag_results["overall_status"] = "partially_degraded"

    # 2. Check Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_key or supabase_url.startswith("https://your-project"):
        diag_results["services"]["supabase"] = {
            "status": "in_memory_mode",
            "message": "SUPABASE_URL not configured. Cosine similarity executes directly in high-performance in-memory mode without persistence.",
        }
    else:
        try:
            start_t = time.time()
            sb = create_client(supabase_url, supabase_key)
            # Test ping query
            sb.table("candidate_embeddings").select("*").limit(1).execute()
            elapsed = round((time.time() - start_t) * 1000, 2)
            diag_results["services"]["supabase"] = {
                "status": "connected_and_operational",
                "url": supabase_url,
                "latency_ms": elapsed,
            }
        except Exception as e:
            diag_results["services"]["supabase"] = {
                "status": "connection_warning",
                "message": f"Connected to client, but table query returned: {str(e)}. In-memory vector calculation remains active as fallback.",
            }

    # 3. Check GitHub API Reachability
    try:
        start_t = time.time()
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            gh_resp = await http_client.get("https://api.github.com/zen", headers={"User-Agent": "AI-ATS-Check/5.0"})
            elapsed = round((time.time() - start_t) * 1000, 2)
            diag_results["services"]["github_api"] = {
                "status": "reachable",
                "http_code": gh_resp.status_code,
                "zen_quote": gh_resp.text.strip() if gh_resp.status_code == 200 else None,
                "latency_ms": elapsed,
            }
    except Exception as e:
        diag_results["services"]["github_api"] = {
            "status": "unreachable",
            "error_detail": str(e),
        }

    return diag_results


@app.post(
    "/process-candidate",
    response_model=ProcessCandidateResponse,
    status_code=status.HTTP_200_OK,
    tags=["Candidate Processing"],
    summary="Multimodal ingestion, strict reality audit, GitHub verification, and 55/25/20 scoring",
)
async def process_candidate(
    file: UploadFile = File(
        ...,
        description="Candidate resume document (.pdf, .docx, .txt) or Video Demo (.mp4, .mov, .webm)",
    ),
    job_description: str = Form(
        ...,
        description="Target job description / role requirements.",
    ),
    github_username: Optional[str] = Form(
        None,
        description="Candidate's GitHub username for async code verification.",
    ),
):
    """
    Next-Gen ATS Candidate Ingestion Pipeline:
    1. Multimodal ingestion via Gemini 2.5 Flash Files API.
    2. Strict Reality Audit: Cross-references graduation dates, age, and claimed timelines.
       Anomaly detection (e.g. claiming 10 yrs React after graduating last year) aggressively inflates fraud_index_score.
    3. Async GitHub verification: checks repos, languages, and topics for proof-of-work.
    4. Semantic vector embedding & Cosine Similarity matching against job description.
    5. 55/25/20 Skill-Dominant Scoring Matrix computation:
       - 55% Skill Semantic Match (> 50%)
       - 25% Skill Velocity
       - 20% Verified Reality
    """
    client = get_genai_client()
    supabase = get_supabase_client()

    suffix = os.path.splitext(file.filename or "")[1]
    if not suffix:
        suffix = ".pdf"

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = temp_file.name
    gemini_file_name = None

    try:
        # Stream file to local temp buffer
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        mime_type = resolve_mime_type(file)

        # Ingest file into Gemini Files API
        uploaded_file = client.files.upload(
            file=temp_path,
            config=types.UploadFileConfig(
                mime_type=mime_type,
                display_name=file.filename or "candidate_submission",
            ),
        )
        gemini_file_name = uploaded_file.name

        # Wait if video or audio is currently processing
        poll_count = 0
        while uploaded_file.state == types.FileState.PROCESSING:
            if poll_count >= 30:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="File processing took too long on Gemini Files API. Please retry.",
                )
            time.sleep(1)
            poll_count += 1
            uploaded_file = client.files.get(name=gemini_file_name)

        if uploaded_file.state == types.FileState.FAILED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Gemini Files API failed to process the uploaded candidate media file.",
            )

        extraction_prompt = (
            "You are a STRICT TECHNICAL AUDITOR and Forensic Proof-of-Work Verification Engine.\n"
            "Analyze the candidate's uploaded resume, portfolio, or video demonstration with extreme skepticism.\n\n"
            "MANDATORY TIMELINE AUDITING RULES:\n"
            "- Cross-reference all claimed skills and experience against graduation dates, career chronology, and education.\n"
            "- If a candidate claims chronological impossibilities (for example: claiming 8-10 years of React or Kubernetes "
            "experience but graduated high school or university only 1 or 2 years ago, or claiming more years of experience "
            "than a technology has existed), you MUST aggressively flag this timeline anomaly.\n"
            "- Scrutinize buzzword stuffing without architectural context or code proof.\n"
            "- Assign fraud_index_score strictly:\n"
            "  * 0.0 - 25.0: Highly authentic, realistic timeline, credible projects with depth.\n"
            "  * 25.1 - 50.0: Minor buzzword density, slightly optimistic claims.\n"
            "  * 50.1 - 75.0: Notable timeline mismatches, inflated senior claims with junior education.\n"
            "  * 75.1 - 100.0: Blatant timeline impossibilities (e.g. 10 years experience right after high school) or fabricated claims.\n\n"
            "Extract structured temporal data strictly conforming to the schema:\n"
            "1. candidate_name: Full name of candidate.\n"
            "2. cgpa: Undergraduate CGPA on a 10.0 scale. If represented on a 4.0 scale, convert proportionally (gpa/4.0 * 10). "
            "If not mentioned, return 0.0.\n"
            "3. twelfth_grade_percentage: Senior secondary / 12th grade percentage (0.0 to 100.0). If not found, return 0.0.\n"
            "4. skill_timeline: Extract technical skills, languages, frameworks, and databases mentioned with:\n"
            "   - skill_name: Exact technology name.\n"
            "   - complexity_weight: Integer from 1 (simple markup/scripting) to 5 (advanced distributed systems, kernels, ML).\n"
            "   - months_to_acquire: Realistic months the candidate spent acquiring or working with it.\n"
            "5. fraud_index_score: Float between 0.0 and 100.0 following the strict auditing rules above.\n"
            "6. experience_summary: Dense 2-4 sentence synthesis of real systems built, architecture, and scope."
        )

        response = generate_content_with_fallback(
            client=client,
            contents=[uploaded_file, extraction_prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CandidateExtraction,
                temperature=0.1,
            ),
        )

        if response.parsed and isinstance(response.parsed, CandidateExtraction):
            candidate_data = response.parsed
        elif response.text:
            candidate_data = CandidateExtraction.model_validate_json(response.text)
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini returned an empty structured response.",
            )

        # 2. Asynchronous GitHub Verification Engine
        verified_timeline, github_verification_meta = await verify_github_candidate(
            github_username, candidate_data.skill_timeline
        )
        candidate_data.skill_timeline = verified_timeline

        # 3. Semantic Matching Engine (Vector Embeddings & Cosine Similarity)
        candidate_semantic_text = (
            f"Candidate: {candidate_data.candidate_name}\n"
            f"Summary: {candidate_data.experience_summary}\n"
            f"Skills: {', '.join(s.skill_name for s in candidate_data.skill_timeline)}"
        )
        semantic_match_score = await calculate_semantic_similarity(
            client=client,
            candidate_profile_text=candidate_semantic_text,
            job_description_text=job_description,
            supabase_client=supabase,
        )

        # 4. 55/25/20 Skill-Dominant Scoring Matrix
        academic_score, verified_reality_score, skill_velocity_score, final_score = calculate_skill_dominant_matrix(
            cgpa=candidate_data.cgpa,
            twelfth_grade_percentage=candidate_data.twelfth_grade_percentage,
            skill_timeline=candidate_data.skill_timeline,
            semantic_match_score=semantic_match_score,
            fraud_index_score=candidate_data.fraud_index_score,
            github_verification=github_verification_meta,
        )

        return ProcessCandidateResponse(
            candidate_name=candidate_data.candidate_name,
            cgpa=candidate_data.cgpa,
            twelfth_grade_percentage=candidate_data.twelfth_grade_percentage,
            skill_timeline=candidate_data.skill_timeline,
            fraud_index_score=candidate_data.fraud_index_score,
            experience_summary=candidate_data.experience_summary,
            github_verification=github_verification_meta,
            academic_score=academic_score,
            verified_reality_score=verified_reality_score,
            skill_velocity_score=skill_velocity_score,
            semantic_match_score=semantic_match_score,
            final_score=final_score,
            job_description_summary=(
                job_description[:160] + "..." if len(job_description) > 160 else job_description
            ),
        )

    except APIError as api_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API Error: {api_err.message}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing candidate: {str(exc)}",
        )
    finally:
        # Cleanup local disk
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        # Cleanup Gemini Files API cloud storage
        if gemini_file_name and client:
            try:
                client.files.delete(name=gemini_file_name)
            except Exception:
                pass


@app.post(
    "/generate-minus-questions",
    response_model=GenerateMinusQuestionsResponse,
    status_code=status.HTTP_200_OK,
    tags=["Interview Preparation"],
    summary="Generate dynamic 'Minus' mock interview questions strictly covering all 7 archetypes",
)
async def generate_minus_questions(payload: GenerateMinusQuestionsRequest):
    """
    Generates EXACTLY 7 dynamic 'Minus' mock interview questions strictly adhering to:
    1. The Skill Gap Question (Migrating from known skill to missing required skill).
    2. The Skill Velocity Question (Hardest challenge faced during fastest learning period).
    3. The Proof-of-Work / Fraud Verification Question (Deep technical probe into video demo/commits).
    4. The Semantic Translation Question (Translating known framework to employer's different stack).
    5. The Career Trajectory (GPS) Question (Mismatch between past projects & current daily duties).
    6. The Impact Metric Question (Demanding specific monitoring tool/metric behind claimed %).
    7. The Collaboration Scenario (Scaling solo project to a 5-person team, merge conflicts, schemas).
    """
    client = get_genai_client()

    skills_summary = ", ".join(
        f"{s.skill_name} (weight: {s.complexity_weight}, months: {s.months_to_acquire}, verified: {s.github_verified})"
        for s in payload.skill_timeline
    )

    prompt = (
        "You are a Bar Raiser and Principal Software Architect conducting an elite technical interview.\n"
        "Generate a structured JSON list of EXACTLY 7 mock interview questions tailored strictly to this candidate.\n"
        "You MUST generate exactly one question for each of the 7 archetypes below in sequential order (1 through 7):\n\n"
        f"Candidate Name: {payload.candidate_name}\n"
        f"Experience Summary: {payload.experience_summary}\n"
        f"Skill Timeline & Proof-of-Work: {skills_summary}\n"
        f"Fraud Index Score: {payload.fraud_index_score}/100\n"
        f"GitHub Verification Summary: {payload.github_verification}\n"
        f"Target Job Description:\n\"{payload.job_description}\"\n\n"
        "Strict Archetype Rules:\n"
        "1. category_number: 1, category_name: 'The Skill Gap Question'\n"
        "   Focus on migrating from a known skill the candidate has to a missing required skill in the job description.\n"
        "2. category_number: 2, category_name: 'The Skill Velocity Question'\n"
        "   Focus on the hardest technical challenge faced during their fastest learning period in their timeline.\n"
        "3. category_number: 3, category_name: 'The Proof-of-Work / Fraud Verification Question'\n"
        "   Deep technical probe into their project architecture, video demo, or git commits to verify they did not fake or buzzword-stuff it.\n"
        "4. category_number: 4, category_name: 'The Semantic Translation Question'\n"
        "   Focus on translating their existing framework knowledge to the employer's different stack (e.g. Fastify vs FastAPI, Mongo vs Postgres).\n"
        "5. category_number: 5, category_name: 'The Career Trajectory (GPS) Question'\n"
        "   Address any mismatch between their past project types (e.g. solo hobby apps) and this role's production daily duties.\n"
        "6. category_number: 6, category_name: 'The Impact Metric Question'\n"
        "   Demand the specific monitoring tool, profiling technique, or telemetry metric they used to claim latency or throughput improvements.\n"
        "7. category_number: 7, category_name: 'The Collaboration Scenario'\n"
        "   Force them to explain how they would scale their solo project with a 5-person team, addressing Git merge conflicts, database schema migrations, and CI/CD."
    )

    try:
        response = generate_content_with_fallback(
            client=client,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MinusQuestionsExtraction,
                temperature=0.3,
            ),
        )

        if response.parsed and isinstance(response.parsed, MinusQuestionsExtraction):
            questions_data = response.parsed
        elif response.text:
            questions_data = MinusQuestionsExtraction.model_validate_json(response.text)
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini returned an empty response for Minus interview questions.",
            )

        for idx, q in enumerate(questions_data.questions, start=1):
            q.category_number = idx

        return GenerateMinusQuestionsResponse(
            candidate_name=payload.candidate_name,
            total_questions=len(questions_data.questions),
            questions=questions_data.questions,
        )

    except APIError as api_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API Error: {api_err.message}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating Minus interview questions: {str(exc)}",
        )


@app.post(
    "/generate-feedback",
    response_model=GenerateFeedbackResponse,
    status_code=status.HTTP_200_OK,
    tags=["Candidate Upskill Engine"],
    summary="Generate personalized capability report with strict rule-based upskilling advice",
)
async def generate_feedback(payload: GenerateFeedbackRequest):
    """
    Candidate Feedback & Upskill Engine:
    Takes sub-scores (Academic, Coding/Semantic, Velocity, Verified Reality) and generates a structured
    CapabilityReport via Gemini 2.5 Flash.

    Skill-Dominant Final Score Calculation:
    final_score = (semantic_match * 0.55) + (velocity * 0.25) + (reality * 0.20)

    Strict Logic Rules:
    - Rule A (High Academics, Low Coding):
      If academic_score is high (>=70) but semantic/coding match is low (<60),
      suggest good study habits but advise to stop reading theory and start building real-world projects on GitHub.
    - Rule B (High Coding, Low Academics):
      If semantic/coding match is high (>=70) but academic score is low (<60),
      praise practical skills but warn of missing CS fundamentals and suggest studying DS, algorithms, and system design.
    """
    client = get_genai_client()

    reality_score = (
        payload.verified_reality_score
        if payload.verified_reality_score is not None
        else payload.academic_score
    )

    if payload.final_score is not None:
        computed_final_score = payload.final_score
    else:
        # 55/25/20 Skill-Dominant Matrix
        computed_final_score = round(
            (payload.semantic_match_score * 0.55)
            + (payload.skill_velocity_score * 0.25)
            + (reality_score * 0.20),
            2,
        )

    is_capable_calculated = computed_final_score >= payload.passing_threshold

    feedback_prompt = (
        "You are an elite Principal Engineering Career Coach and ATS Capability Auditor.\n"
        "Generate a structured, actionable 'Capability Report' for this candidate.\n\n"
        f"Candidate Name: {payload.candidate_name}\n"
        f"Academic Score: {payload.academic_score}/100\n"
        f"Coding / Semantic Match Score: {payload.semantic_match_score}/100\n"
        f"Skill Velocity Score: {payload.skill_velocity_score}/100\n"
        f"Verified Reality Score: {reality_score}/100\n"
        f"Final Composite Score: {computed_final_score}/100\n"
        f"Passing Threshold: {payload.passing_threshold}%\n"
        f"Initial Capable Flag: {is_capable_calculated}\n\n"
        "CRITICAL UPSKILLING LOGIC RULES (You MUST strictly follow these rules for 'actionable_advice'):\n"
        "- RULE A (High Academics, Low Coding):\n"
        f"  Condition: academic_score >= 70.0 and semantic_match_score < 60.0. (Currently: Academic={payload.academic_score}, Coding={payload.semantic_match_score}).\n"
        "  Requirement: If this condition is met, you MUST explicitly state that the candidate has good study habits and academic aptitude, "
        "but they must stop just reading theory and immediately start building real-world end-to-end projects and pushing active code to GitHub.\n\n"
        "- RULE B (High Coding, Low Academics):\n"
        f"  Condition: semantic_match_score >= 70.0 and academic_score < 60.0. (Currently: Coding={payload.semantic_match_score}, Academic={payload.academic_score}).\n"
        "  Requirement: If this condition is met, you MUST enthusiastically praise their practical, hands-on coding capabilities, "
        "but warn them that they lack core computer science fundamentals. Suggest they review fundamental educational concepts "
        "(such as data structures, algorithmic complexity, or system design principles) to build a robust long-term engineering foundation.\n\n"
        "- RULE C (Balanced / Other Scenarios):\n"
        "  If neither Rule A nor Rule B applies, provide precise, personalized engineering advice targeting their lowest sub-score.\n\n"
        "Provide:\n"
        "1. is_capable: boolean (true if final_score >= passing_threshold, else false).\n"
        "2. strongest_area: concise sentence highlighting their top strength.\n"
        "3. weakest_area: concise sentence highlighting their main vulnerability.\n"
        "4. actionable_advice: the specific advice adhering strictly to Rule A, Rule B, or Rule C."
    )

    try:
        response = generate_content_with_fallback(
            client=client,
            contents=feedback_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CapabilityReport,
                temperature=0.2,
            ),
        )

        if response.parsed and isinstance(response.parsed, CapabilityReport):
            report_data = response.parsed
        elif response.text:
            report_data = CapabilityReport.model_validate_json(response.text)
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini returned an empty response for capability feedback.",
            )

        report_data.is_capable = is_capable_calculated

        return GenerateFeedbackResponse(
            candidate_name=payload.candidate_name,
            passing_threshold=payload.passing_threshold,
            final_score=computed_final_score,
            capability_report=report_data,
        )

    except APIError as api_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API Error: {api_err.message}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating capability feedback: {str(exc)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
