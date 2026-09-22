# Frontend Integration Brief: Next-Gen AI Applicant Tracking System (ATS)

This document provides the complete API specification, data models, and UI/UX recommendations for building the frontend (React Native / Expo, Next.js, or React).

---

## 1. Connection & Network Overview

- **Base URL (Local Development):** `http://localhost:8000`
- **Android Emulator:** `http://10.0.2.2:8000`
- **Expo Go (Physical Device):** `http://<YOUR_LOCAL_IP>:8000` (e.g. `http://192.168.1.15:8000`)
- **CORS Status:** Fully enabled (`allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`).
- **Interactive Swagger Docs:** `http://localhost:8000/docs`

---

## 2. API Endpoints & Request/Response Contracts

### A. Health Check & Diagnostics
#### `GET /`
Check API status and current scoring matrix configuration.

**Response `(200 OK)`:**
```json
{
  "service": "Next-Gen AI ATS Backend",
  "version": "5.0.0",
  "status": "healthy",
  "gemini_status": "ready",
  "model": "gemini-2.5-flash",
  "embedding_model": "text-embedding-004",
  "scoring_matrix": "55% Skill/Semantic Match + 25% Skill Velocity + 20% Verified Reality",
  "skill_factor_percentage": "55% (Core Skill) + 25% (Skill Velocity) = 80% Total Skill Weight",
  "supabase_pgvector": "in-memory-fallback",
  "endpoints": {
    "health": "GET /",
    "diagnostics": "GET /diagnostics",
    "process_candidate": "POST /process-candidate",
    "generate_minus_questions": "POST /generate-minus-questions",
    "generate_feedback": "POST /generate-feedback"
  }
}
```

#### `GET /diagnostics`
Test live status of Gemini 2.5 Flash, Supabase, and GitHub APIs.

---

### B. Ingestion & Scoring Engine
#### `POST /process-candidate`
Ingests a candidate resume or video demo, extracts temporal skill timelines, performs asynchronous GitHub verification, generates vector embeddings, and computes the 55/25/20 Skill-Dominant score.

- **Content-Type:** `multipart/form-data`
- **Parameters:**
  | Field | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `file` | `Binary File` | **Yes** | `.pdf`, `.docx`, `.txt`, `.png`, or Video Demo (`.mp4`, `.mov`, `.webm`) |
  | `job_description` | `String` | **Yes** | Text of job requirements / description |
  | `github_username` | `String` | No | GitHub handle (e.g., `octocat` or `@octocat`) |

**Sample Response `(200 OK)`:**
```json
{
  "candidate_name": "Jordan Chen",
  "cgpa": 8.8,
  "twelfth_grade_percentage": 85.0,
  "skill_timeline": [
    {
      "skill_name": "Python",
      "complexity_weight": 4,
      "months_to_acquire": 2.0,
      "github_verified": true
    },
    {
      "skill_name": "FastAPI",
      "complexity_weight": 3,
      "months_to_acquire": 1.0,
      "github_verified": true
    },
    {
      "skill_name": "Distributed Consensus (Raft)",
      "complexity_weight": 5,
      "months_to_acquire": 3.0,
      "github_verified": false
    }
  ],
  "fraud_index_score": 12.0,
  "experience_summary": "Architected low-latency microservices with FastAPI and Redis Streams. Handled 10k req/s under synthetic stress testing.",
  "github_verification": {
    "username": "jordanchen",
    "status": "verified",
    "repositories_analyzed": 18,
    "detected_languages": ["python", "typescript"],
    "detected_topics": ["fastapi", "docker", "redis"],
    "verified_skills_count": 2
  },
  "academic_score": 86.5,
  "verified_reality_score": 76.12,
  "skill_velocity_score": 77.0,
  "semantic_match_score": 84.0,
  "final_score": 80.67,
  "job_description_summary": "Looking for a Senior Python Developer with experience in FastAPI and microservices..."
}
```

---

### C. The 7-Archetype Mock Interview Generator
#### `POST /generate-minus-questions`
Generates **strictly 7 questions**, exactly one for each required archetype.

- **Content-Type:** `application/json`
- **Request Body:**
```json
{
  "candidate_name": "Jordan Chen",
  "experience_summary": "Architected low-latency microservices with FastAPI and Redis Streams.",
  "skill_timeline": [
    {
      "skill_name": "Python",
      "complexity_weight": 4,
      "months_to_acquire": 2.0,
      "github_verified": true
    }
  ],
  "fraud_index_score": 12.0,
  "github_verification": {
    "verified_skills_count": 2
  },
  "job_description": "Senior Platform Engineer responsible for multi-tenant microservices and Apache Kafka."
}
```

**Sample Response `(200 OK)`:**
```json
{
  "candidate_name": "Jordan Chen",
  "total_questions": 7,
  "questions": [
    {
      "category_number": 1,
      "category_name": "The Skill Gap Question",
      "target_focus": "Migrating from Redis Streams to Apache Kafka",
      "question": "In your past project you leveraged Redis Streams, but our stack relies on Apache Kafka. How do Kafka consumer group rebalances and offset commits differ from Redis XREADGROUP ack mechanisms during a crash loop?",
      "evaluation_criteria": "Candidate must explain partition assignments, cooperative sticky assignors, auto vs manual commits, and retention semantics."
    },
    {
      "category_number": 2,
      "category_name": "The Skill Velocity Question",
      "target_focus": "Mastering Raft in 3 months",
      "question": "Your timeline shows you picked up distributed consensus in 3 months. What was the subtlest split-brain edge case you encountered?",
      "evaluation_criteria": "Discuss election timeouts, term discrepancies, and log compaction snapshots."
    },
    {
      "category_number": 3,
      "category_name": "The Proof-of-Work / Fraud Verification Question",
      "target_focus": "Video Demo throughput benchmark",
      "question": "In your demo video, you showed 10,000 req/sec on your worker. What tool simulated the load and how did you verify Python GIL contention was not masking dropped packets?",
      "evaluation_criteria": "Details wrk/k6/Locust scripts, OS ulimits, and uvloop event loop lag."
    },
    {
      "category_number": 4,
      "category_name": "The Semantic Translation Question",
      "target_focus": "Translating FastAPI Pydantic Models to Go Structs",
      "question": "If we ported your service to Go, how would you handle Pydantic v2's recursive validation and custom field sanitizers?",
      "evaluation_criteria": "Explains struct tags, go-playground/validator, and unmarshaling overhead."
    },
    {
      "category_number": 5,
      "category_name": "The Career Trajectory (GPS) Question",
      "target_focus": "Solo Prototype vs 24/7 SLA Production",
      "question": "Your past projects were single-node deployments. How will you adjust when operating under strict 99.99% SLAs with zero-downtime rolling deploys?",
      "evaluation_criteria": "Must discuss blue-green deployments, readiness/liveness probe lifecycles, and connection draining."
    },
    {
      "category_number": 6,
      "category_name": "The Impact Metric Question",
      "target_focus": "Claimed 40% latency reduction",
      "question": "You claimed a 40% latency reduction. What specific APM tool or flame graph did you use, and did this reflect p99 tail latency or only the p50 median?",
      "evaluation_criteria": "Distinguishes between p50 and p99, database index flame graphs, and trace context propagation."
    },
    {
      "category_number": 7,
      "category_name": "The Collaboration Scenario",
      "target_focus": "Scaling solo project with 5 engineers",
      "question": "Imagine 4 other engineers join your repo tomorrow. How would you structure Git trunk branch rules, automated Alembic migration linting, and PR test suites to avoid schema locks?",
      "evaluation_criteria": "Mentions trunk-based development, ephemeral PR database preview environments, and alembic merge head resolution."
    }
  ]
}
```

---

### D. Candidate Feedback & Upskill Engine
#### `POST /generate-feedback`
Generates a structured report with strict rule-driven advice.

- **Content-Type:** `application/json`
- **Request Body:**
```json
{
  "candidate_name": "David Scholar",
  "academic_score": 92.0,
  "semantic_match_score": 42.0,
  "skill_velocity_score": 50.0,
  "verified_reality_score": 88.0,
  "final_score": 64.1,
  "passing_threshold": 70.0
}
```

- **Logic Rules Applied by Gemini 2.5 Flash:**
  - **Rule A (High Academics $\ge 70$, Low Coding $< 60$):** Advises to stop reading theory and start building real-world projects and pushing code to GitHub.
  - **Rule B (High Coding $\ge 70$, Low Academics $< 60$):** Praises practical skills, but cautions that they lack core computer science fundamentals (data structures, algorithms, system design).
  - **Rule C (Balanced / Other):** Targets the lowest sub-score with specific next steps.

**Sample Response `(200 OK)`:**
```json
{
  "candidate_name": "David Scholar",
  "passing_threshold": 70.0,
  "final_score": 64.1,
  "capability_report": {
    "is_capable": false,
    "strongest_area": "Academic excellence and disciplined theoretical study habits.",
    "weakest_area": "Low practical coding match against production requirements and lack of active repositories.",
    "actionable_advice": "You have good study habits and academic aptitude, but you must stop just reading theory and immediately start building real-world projects and pushing code to GitHub."
  }
}
```

---

## 3. The 55/25/20 Scoring Matrix & Math Formula

$$\text{Final Score} = (\text{Semantic Match} \times \mathbf{0.55}) + (\text{Skill Velocity} \times \mathbf{0.25}) + (\text{Verified Reality} \times \mathbf{0.20})$$

1. **Skill Semantic Match (55%):** Vector cosine similarity between candidate skills and the job description.
2. **Skill Velocity Score (25%):** $\sum \frac{\text{complexity}}{\text{months}}$, boosted by $+10\%$ if skills are verified on GitHub.
3. **Verified Reality Score (20%):** $\text{Academic Base} \times \text{Authenticity Factor} \times \text{GitHub Factor}$.
   - High fraud ($>60\%$) or chronological timeline anomalies severely crash this score.
   - GitHub username with zero matching repos reduces this factor to $0.35$.
4. **Total Skill Weight:** $55\% + 25\% = \mathbf{80\%}$ of candidate score is determined by practical ability and learning speed.

---

## 4. Recommended Frontend Screens & UI Architecture

### Screen 1: Candidate Intake & Proof-of-Work
- **Components:**
  - Multi-format file picker (`.pdf`, `.docx`, `.png`, `.mp4`, `.mov`).
  - Job Description text field.
  - GitHub username input field with prefix `@`.
  - "Run AI Evaluation" primary action button with upload progress indicator.

### Screen 2: Candidate Scorecard & Reality Audit
- **Components:**
  - **Hero Gauge:** `final_score` (0–100) with color states ($<60$ red, $60-75$ yellow, $>75$ green).
  - **Sub-score Bars / Cards:**
    - Semantic Coding Match (`55%` weight).
    - Skill Velocity (`25%` weight).
    - Verified Reality (`20%` weight).
  - **Fraud Index Gauge:** Alert badge if `fraud_index_score > 50%` (Forensic Timeline Warning).
  - **GitHub Verification Pill:** Badges displaying verified languages and analyzed repo count.
  - **Skill Timeline:** Chips showing skill name, complexity badge (1-5 stars), months to acquire, and GitHub verified badge.

### Screen 3: Capability Report & Actionable Upskill
- **Components:**
  - **Capability Banner:** `is_capable ? "QUALIFIED CANDIDATE" : "CAPABILITY GAP DETECTED"`.
  - **Card:** Strongest Area.
  - **Card:** Weakest Area.
  - **Actionable Advice Callout:** Highlighted coaching box with specific recommendations (Rule A or Rule B).

### Screen 4: 7-Archetype Mock Interview Flashcards
- **Components:**
  - Horizontal swipeable flashcard deck or accordion list for the 7 questions:
    1. The Skill Gap Question
    2. The Skill Velocity Question
    3. The Proof-of-Work / Fraud Verification Question
    4. The Semantic Translation Question
    5. The Career Trajectory (GPS) Question
    6. The Impact Metric Question
    7. The Collaboration Scenario
  - Each card displays: `category_name`, `target_focus`, `question`, and expandable `evaluation_criteria` for the interviewer.

---

## 5. React Native / Expo Frontend Code Snippet

```typescript
// services/atsApi.ts
const API_BASE_URL = 'http://localhost:8000'; // Replace with local IP for physical devices

export async function processCandidate(
  fileUri: string,
  fileName: string,
  fileMimeType: string,
  jobDescription: string,
  githubUsername?: string
) {
  const formData = new FormData();
  formData.append('file', {
    uri: fileUri,
    name: fileName,
    type: fileMimeType,
  } as any);
  formData.append('job_description', jobDescription);
  if (githubUsername) {
    formData.append('github_username', githubUsername);
  }

  const response = await fetch(`${API_BASE_URL}/process-candidate`, {
    method: 'POST',
    body: formData,
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to process candidate');
  }

  return response.json();
}

export async function generateMinusQuestions(candidateData: any, jobDescription: string) {
  const response = await fetch(`${API_BASE_URL}/generate-minus-questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      candidate_name: candidateData.candidate_name,
      experience_summary: candidateData.experience_summary,
      skill_timeline: candidateData.skill_timeline,
      fraud_index_score: candidateData.fraud_index_score,
      github_verification: candidateData.github_verification,
      job_description: jobDescription,
    }),
  });
  return response.json();
}

export async function generateFeedback(candidateData: any, threshold = 70.0) {
  const response = await fetch(`${API_BASE_URL}/generate-feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      candidate_name: candidateData.candidate_name,
      academic_score: candidateData.academic_score,
      semantic_match_score: candidateData.semantic_match_score,
      skill_velocity_score: candidateData.skill_velocity_score,
      verified_reality_score: candidateData.verified_reality_score,
      final_score: candidateData.final_score,
      passing_threshold: threshold,
    }),
  });
  return response.json();
}
```
