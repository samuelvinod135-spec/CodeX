# Next-Gen AI Applicant Tracking System (ATS) Backend

An intelligent, multimodal Applicant Tracking System (ATS) backend powered by **FastAPI**, **Google Gemini**, and **Supabase (pgvector)**. 

Evaluates resumes and video demonstrations, computes a 55/25/20 Skill-Dominant scoring matrix, performs asynchronous GitHub code verification, and dynamically generates 7 strict archetypes of mock technical interview questions.

---

## Features

- **Multimodal Ingestion (`POST /process-candidate`):** Accepts `.pdf`, `.docx`, `.txt`, `.png`, and video demos (`.mp4`, `.mov`, `.webm`).
- **Strict Forensic Timeline Auditing:** Detects keyword stuffing and chronological timeline anomalies.
- **Asynchronous GitHub Verification:** Cross-references claimed skills against candidate's public repositories.
- **Semantic Matching Engine:** Vector embeddings comparing candidate profile against job descriptions via Cosine Similarity.
- **Skill-Dominant 55/25/20 Scoring Matrix:**
  - **55%** Core Skill / Semantic Coding Match
  - **25%** Skill Velocity (learning speed & complexity)
  - **20%** Verified Reality (academics & proof-of-work)
- **7-Archetype Mock Interview Generator (`POST /generate-minus-questions`):**
  1. The Skill Gap Question
  2. The Skill Velocity Question
  3. The Proof-of-Work / Fraud Verification Question
  4. The Semantic Translation Question
  5. The Career Trajectory (GPS) Question
  6. The Impact Metric Question
  7. The Collaboration Scenario
- **Candidate Feedback & Upskill Engine (`POST /generate-feedback`):** Actionable coaching enforcing Rule A (High Academics / Low Coding) and Rule B (High Coding / Low Academics).
- **Diagnostics API (`GET /diagnostics`):** Real-time latency and connectivity checks for Gemini, Supabase, and GitHub.

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and provide your credentials:
```bash
cp .env.example .env
```

```ini
# .env
GEMINI_API_KEY=your_gemini_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key_here
```

### 3. Run Live Diagnostics
Verify all services before launching:
```bash
python3 check_engines.py
```

### 4. Start the Backend Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 5. Run Automated Tests
```bash
python3 test_app.py
```

---

## Frontend Integration

See [`FRONTEND_INTEGRATION_BRIEF.md`](./FRONTEND_INTEGRATION_BRIEF.md) for full endpoint contracts, TypeScript interfaces, and UI architecture guidelines for React Native / Expo.
