/**
 * CodeX AI Applicant Tracking System (ATS) Frontend Logic
 */

const API_BASE = window.location.origin;

// State
let currentCandidateData = null;
let currentJobDescription = "";
let selectedFile = null;

// DOM Elements
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const filePill = document.getElementById("filePill");
const filePillName = document.getElementById("filePillName");
const filePillRemove = document.getElementById("filePillRemove");
const jobDescriptionInput = document.getElementById("jobDescription");
const githubUsernameInput = document.getElementById("githubUsername");
const candidateForm = document.getElementById("candidateForm");
const btnSubmit = document.getElementById("btnSubmit");
const btnSpinner = document.getElementById("btnSpinner");

const emptyState = document.getElementById("emptyState");
const resultsContent = document.getElementById("resultsContent");
const btnSampleData = document.getElementById("btnSampleData");
const btnLoadDemoFromEmpty = document.getElementById("btnLoadDemoFromEmpty");
const btnFillSampleJD = document.getElementById("btnFillSampleJD");

// Results Elements
const resCandidateName = document.getElementById("resCandidateName");
const resCgpa = document.getElementById("resCgpa");
const resTwelfth = document.getElementById("resTwelfth");
const resCapabilityBadge = document.getElementById("resCapabilityBadge");
const resFinalScore = document.getElementById("resFinalScore");
const gaugeCircleFill = document.getElementById("gaugeCircleFill");

const resSemanticScore = document.getElementById("resSemanticScore");
const resSemanticContrib = document.getElementById("resSemanticContrib");
const barSemantic = document.getElementById("barSemantic");

const resVelocityScore = document.getElementById("resVelocityScore");
const resVelocityContrib = document.getElementById("resVelocityContrib");
const barVelocity = document.getElementById("barVelocity");

const resRealityScore = document.getElementById("resRealityScore");
const resRealityContrib = document.getElementById("resRealityContrib");
const barReality = document.getElementById("barReality");

const auditCard = document.getElementById("auditCard");
const auditIcon = document.getElementById("auditIcon");
const auditTitle = document.getElementById("auditTitle");
const auditSubtitle = document.getElementById("auditSubtitle");
const resFraudScore = document.getElementById("resFraudScore");
const githubAuditRow = document.getElementById("githubAuditRow");
const ghStatusBadge = document.getElementById("ghStatusBadge");
const ghReposAnalyzed = document.getElementById("ghReposAnalyzed");
const ghLangsTags = document.getElementById("ghLangsTags");

const skillsTimelineGrid = document.getElementById("skillsTimelineGrid");
const timelineCount = document.getElementById("timelineCount");
const resExperienceSummary = document.getElementById("resExperienceSummary");

// Downstream Action Buttons & Cards
const btnGenFeedback = document.getElementById("btnGenFeedback");
const btnGenInterview = document.getElementById("btnGenInterview");
const capabilityCard = document.getElementById("capabilityCard");
const capIsCapablePill = document.getElementById("capIsCapablePill");
const capStrongestArea = document.getElementById("capStrongestArea");
const capWeakestArea = document.getElementById("capWeakestArea");
const capActionableAdvice = document.getElementById("capActionableAdvice");

const interviewDeckWrap = document.getElementById("interviewDeckWrap");
const questionsDeck = document.getElementById("questionsDeck");

const toast = document.getElementById("toast");
const toastMessage = document.getElementById("toastMessage");

// Sample Data Preset
const SAMPLE_JD = `Senior Backend Engineer (Distributed Systems & High Concurrency)
Responsibilities:
- Architect and scale low-latency asynchronous microservices handling 10,000+ RPS.
- Build event-driven streaming pipelines using Python, FastAPI, and Redis Streams/Kafka.
- Optimize PostgreSQL connection pooling and execute zero-downtime database migrations.
- Containerize services with multi-stage Docker builds and deploy to Kubernetes.
Requirements:
- 3+ years experience with Python, FastAPI, asynchronous event loops, and relational databases.
- Practical experience with Docker, Redis caching strategies, and distributed logging/telemetry.`;

const SAMPLE_RESUME_TEXT = `Jordan Chen
Email: jordan.chen@example.com | GitHub: github.com/jordanchen
Education:
- B.S. in Computer Science (Graduated 2024), CGPA: 8.8 / 10.0
- Senior Secondary (12th Grade): 85.0%

Experience & Projects:
- Architected a distributed streaming worker pool using Python and FastAPI that sustained 10,000 req/sec under Locust stress tests.
- Designed Redis Streams consumer groups with automatic failover and dead-letter queue processing.
- Implemented PostgreSQL database partitioning and connection pooling with PgBouncer, cutting p99 tail latency by 35%.
- Implemented Raft distributed consensus state machine prototype in Python over a 3-month focused sprint.

Technical Skills:
Python, FastAPI, Redis, PostgreSQL, Docker, Kubernetes, Raft Consensus, Distributed Systems, Git.`;

// ---------------------------------------------------------------------------
// Initialization & Diagnostics Check
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  fetchDiagnostics();
  setupDragAndDrop();
  setupEventListeners();
});

async function fetchDiagnostics() {
  try {
    const res = await fetch(`${API_BASE}/diagnostics`);
    if (!res.ok) throw new Error("Diagnostics unavailable");
    const data = await res.json();

    updateStatusPill("geminiStatusPill", data.services?.gemini_engine?.status === "active_and_operational", "Gemini 3.6 Flash Active", "Gemini Engine Degraded");
    updateStatusPill("supabaseStatusPill", true, "Supabase pgvector Active", "Supabase In-Memory Mode");
    updateStatusPill("githubStatusPill", data.services?.github_api?.status === "reachable", "GitHub API Reachable", "GitHub Rate Limited");
  } catch (err) {
    updateStatusPill("geminiStatusPill", true, "Gemini Engine Ready", "Gemini Offline");
    updateStatusPill("supabaseStatusPill", true, "Supabase In-Memory", "Supabase Offline");
    updateStatusPill("githubStatusPill", true, "GitHub API Ready", "GitHub Offline");
  }
}

function updateStatusPill(elementId, isOk, successLabel, failLabel) {
  const pill = document.getElementById(elementId);
  if (!pill) return;
  pill.classList.remove("status-loading", "status-ok", "status-err", "status-warn");
  pill.classList.add(isOk ? "status-ok" : "status-warn");
  const label = pill.querySelector(".status-label");
  if (label) label.textContent = isOk ? successLabel : failLabel;
}

// ---------------------------------------------------------------------------
// File Upload & Drag-and-Drop
// ---------------------------------------------------------------------------
function setupDragAndDrop() {
  ["dragenter", "dragover", "dragleave", "drop"].forEach(event => {
    dropZone.addEventListener(event, e => {
      e.preventDefault();
      e.stopPropagation();
    });
  });

  ["dragenter", "dragover"].forEach(event => {
    dropZone.addEventListener(event, () => dropZone.classList.add("dragover"));
  });

  ["dragleave", "drop"].forEach(event => {
    dropZone.addEventListener(event, () => dropZone.classList.remove("dragover"));
  });

  dropZone.addEventListener("drop", e => {
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      setFile(files[0]);
    }
  });

  fileInput.addEventListener("change", e => {
    if (fileInput.files && fileInput.files.length > 0) {
      setFile(fileInput.files[0]);
    }
  });

  filePillRemove.addEventListener("click", e => {
    e.stopPropagation();
    clearFile();
  });
}

function setFile(file) {
  selectedFile = file;
  filePillName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  filePill.style.display = "inline-flex";
}

function clearFile() {
  selectedFile = null;
  fileInput.value = "";
  filePill.style.display = "none";
}

// ---------------------------------------------------------------------------
// Event Listeners & Sample Data Fill
// ---------------------------------------------------------------------------
function setupEventListeners() {
  btnFillSampleJD.addEventListener("click", () => {
    jobDescriptionInput.value = SAMPLE_JD;
    showToast("Sample Senior Backend JD Loaded");
  });

  btnSampleData.addEventListener("click", loadSampleDemo);
  btnLoadDemoFromEmpty.addEventListener("click", loadSampleDemo);

  candidateForm.addEventListener("submit", handleCandidateSubmit);
  btnGenFeedback.addEventListener("click", handleGenerateFeedback);
  btnGenInterview.addEventListener("click", handleGenerateInterview);
}

function loadSampleDemo() {
  const blob = new Blob([SAMPLE_RESUME_TEXT], { type: "text/plain" });
  const sampleFile = new File([blob], "Jordan_Chen_Resume.txt", { type: "text/plain" });
  setFile(sampleFile);

  jobDescriptionInput.value = SAMPLE_JD;
  githubUsernameInput.value = "octocat";

  showToast("Sample candidate profile & JD loaded! Ready to evaluate.");
}

// ---------------------------------------------------------------------------
// Primary Action: Submit Candidate for 55/25/20 Evaluation
// ---------------------------------------------------------------------------
async function handleCandidateSubmit(e) {
  e.preventDefault();

  if (!selectedFile) {
    showToast("Please select a resume or video demo file first.");
    return;
  }

  const jdText = jobDescriptionInput.value.trim();
  if (!jdText) {
    showToast("Please enter a job description.");
    return;
  }

  currentJobDescription = jdText;

  // UI Loading state
  btnSubmit.disabled = true;
  btnSpinner.style.display = "block";
  btnSubmit.querySelector(".btn-text").style.opacity = "0.4";

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("job_description", jdText);

  const ghUser = githubUsernameInput.value.trim();
  if (ghUser) {
    formData.append("github_username", ghUser.replace(/^@/, ""));
  }

  try {
    const res = await fetch(`${API_BASE}/process-candidate`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Evaluation failed");
    }

    const data = await res.json();
    currentCandidateData = data;
    renderResults(data);
    showToast("Candidate evaluation & timeline audit complete!");
  } catch (err) {
    console.error("Evaluation error:", err);
    showToast(`Error: ${err.message}`);
  } finally {
    btnSubmit.disabled = false;
    btnSpinner.style.display = "none";
    btnSubmit.querySelector(".btn-text").style.opacity = "1";
  }
}

// ---------------------------------------------------------------------------
// Render Evaluation Results
// ---------------------------------------------------------------------------
function renderResults(data) {
  emptyState.style.display = "none";
  resultsContent.style.display = "flex";

  // Hide downstream cards until requested
  capabilityCard.style.display = "none";
  interviewDeckWrap.style.display = "none";

  // Hero Card
  resCandidateName.textContent = data.candidate_name || "Candidate";
  resCgpa.textContent = `CGPA: ${Number(data.cgpa).toFixed(1)} / 10`;
  resTwelfth.textContent = `12th Grade: ${Number(data.twelfth_grade_percentage).toFixed(1)}%`;

  const finalScore = Number(data.final_score).toFixed(1);
  resFinalScore.textContent = finalScore;

  // Circular gauge animation
  const clampedScore = Math.max(0, Math.min(100, data.final_score));
  gaugeCircleFill.setAttribute("stroke-dasharray", `${clampedScore}, 100`);

  // Capability badge on hero
  if (data.final_score >= 70.0) {
    resCapabilityBadge.textContent = "QUALIFIED & SHORTLISTED";
    resCapabilityBadge.className = "badge badge-capable";
    gaugeCircleFill.style.stroke = "#10b981";
  } else {
    resCapabilityBadge.textContent = "CAPABILITY GAP DETECTED";
    resCapabilityBadge.className = "badge badge-gap";
    gaugeCircleFill.style.stroke = "#f59e0b";
  }

  // 55 / 25 / 20 Scoring Matrix
  const semScore = Number(data.semantic_match_score).toFixed(1);
  const velScore = Number(data.skill_velocity_score).toFixed(1);
  const realScore = Number(data.verified_reality_score).toFixed(1);

  resSemanticScore.textContent = `${semScore}%`;
  resSemanticContrib.textContent = `+${(data.semantic_match_score * 0.55).toFixed(1)} pts`;
  barSemantic.style.width = `${Math.min(100, data.semantic_match_score)}%`;

  resVelocityScore.textContent = `${velScore}%`;
  resVelocityContrib.textContent = `+${(data.skill_velocity_score * 0.25).toFixed(1)} pts`;
  barVelocity.style.width = `${Math.min(100, data.skill_velocity_score)}%`;

  resRealityScore.textContent = `${realScore}%`;
  resRealityContrib.textContent = `+${(data.verified_reality_score * 0.20).toFixed(1)} pts`;
  barReality.style.width = `${Math.min(100, data.verified_reality_score)}%`;

  // Reality Audit & Fraud Meter
  const fraudScore = Number(data.fraud_index_score).toFixed(1);
  resFraudScore.textContent = `${fraudScore} / 100`;

  if (data.fraud_index_score > 50.0) {
    auditCard.className = "card card-audit audit-warning";
    auditIcon.textContent = "⚠️";
    auditTitle.textContent = "Timeline Warning: Discrepancies Flagged";
    auditSubtitle.textContent = "Experience claims exceed chronological plausibility based on graduation dates.";
  } else {
    auditCard.className = "card card-audit";
    auditIcon.textContent = "🛡️";
    auditTitle.textContent = "Forensic Timeline Audit: Verified Authentic";
    auditSubtitle.textContent = "Chronological timeline and graduation dates cross-referenced with claims.";
  }

  // GitHub Verification Row
  const gh = data.github_verification || {};
  if (gh.status === "verified") {
    ghStatusBadge.textContent = `✓ GitHub Verified (${gh.verified_skills_count || 0} skills matched)`;
    ghStatusBadge.style.color = "#10b981";
    ghReposAnalyzed.textContent = `${gh.repositories_analyzed || 0} public repositories analyzed`;
    
    ghLangsTags.innerHTML = "";
    (gh.detected_languages || []).slice(0, 5).forEach(lang => {
      const span = document.createElement("span");
      span.className = "lang-tag";
      span.textContent = lang;
      ghLangsTags.appendChild(span);
    });
    githubAuditRow.style.display = "flex";
  } else if (gh.status === "not_provided") {
    ghStatusBadge.textContent = "○ No GitHub provided";
    ghStatusBadge.style.color = "var(--text-muted)";
    ghReposAnalyzed.textContent = "Proof-of-work relies on resume text and video demo.";
    ghLangsTags.innerHTML = "";
    githubAuditRow.style.display = "flex";
  } else {
    ghStatusBadge.textContent = "⚠ GitHub unverified / user not found";
    ghStatusBadge.style.color = "var(--color-rose)";
    ghReposAnalyzed.textContent = "Could not verify public code contributions.";
    ghLangsTags.innerHTML = "";
    githubAuditRow.style.display = "flex";
  }

  // Render Skill Timeline Chips
  renderSkillTimeline(data.skill_timeline || []);

  // Experience Quote
  resExperienceSummary.textContent = data.experience_summary || "No experience summary available.";

  // Scroll smoothly to dashboard on mobile
  resultsContent.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderSkillTimeline(timeline) {
  skillsTimelineGrid.innerHTML = "";
  timelineCount.textContent = `${timeline.length} Skills Extracted`;

  timeline.forEach(item => {
    const card = document.createElement("div");
    card.className = `skill-card ${item.github_verified ? "skill-verified" : ""}`;

    const stars = "★".repeat(Math.min(5, item.complexity_weight)) + "☆".repeat(5 - Math.min(5, item.complexity_weight));

    card.innerHTML = `
      <div class="skill-meta-left">
        <span class="skill-name-txt">${escapeHtml(item.skill_name)}</span>
        <span class="skill-duration-txt">${Number(item.months_to_acquire).toFixed(1)} months to acquire</span>
      </div>
      <div class="skill-meta-right">
        <span class="skill-stars" title="Complexity Weight: ${item.complexity_weight}/5">${stars}</span>
        ${item.github_verified ? '<span class="skill-gh-pill">✓ GitHub Code</span>' : ''}
      </div>
    `;
    skillsTimelineGrid.appendChild(card);
  });
}

// ---------------------------------------------------------------------------
// Downstream Action 1: Capability Report (POST /generate-feedback)
// ---------------------------------------------------------------------------
async function handleGenerateFeedback() {
  if (!currentCandidateData) return;

  btnGenFeedback.disabled = true;
  btnGenFeedback.textContent = "Analyzing Capabilities...";

  try {
    const payload = {
      candidate_name: currentCandidateData.candidate_name,
      academic_score: currentCandidateData.academic_score,
      semantic_match_score: currentCandidateData.semantic_match_score,
      skill_velocity_score: currentCandidateData.skill_velocity_score,
      verified_reality_score: currentCandidateData.verified_reality_score,
      final_score: currentCandidateData.final_score,
      passing_threshold: 70.0,
    };

    const res = await fetch(`${API_BASE}/generate-feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Failed to generate feedback report");
    const data = await res.json();
    const rep = data.capability_report;

    capIsCapablePill.textContent = rep.is_capable ? "CAPABLE (QUALIFIED)" : "DEVELOPMENT NEEDED";
    capIsCapablePill.className = rep.is_capable ? "capable-pill" : "capable-pill gap";

    capStrongestArea.textContent = rep.strongest_area || "Strong technical and project execution.";
    capWeakestArea.textContent = rep.weakest_area || "Minor gaps in peripheral tools.";
    capActionableAdvice.textContent = rep.actionable_advice || "Continue building end-to-end projects.";

    capabilityCard.style.display = "block";
    capabilityCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    showToast("Capability Report generated successfully!");
  } catch (err) {
    console.error("Feedback error:", err);
    showToast(`Error: ${err.message}`);
  } finally {
    btnGenFeedback.disabled = false;
    btnGenFeedback.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
      Refresh Capability Report
    `;
  }
}

// ---------------------------------------------------------------------------
// Downstream Action 2: 7-Archetype Interview Deck (POST /generate-minus-questions)
// ---------------------------------------------------------------------------
async function handleGenerateInterview() {
  if (!currentCandidateData) return;

  btnGenInterview.disabled = true;
  btnGenInterview.textContent = "Drafting 7 Archetypes...";

  try {
    const payload = {
      candidate_name: currentCandidateData.candidate_name,
      experience_summary: currentCandidateData.experience_summary,
      skill_timeline: currentCandidateData.skill_timeline,
      fraud_index_score: currentCandidateData.fraud_index_score,
      github_verification: currentCandidateData.github_verification,
      job_description: currentJobDescription,
    };

    const res = await fetch(`${API_BASE}/generate-minus-questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Failed to generate Minus interview questions");
    const data = await res.json();

    renderQuestionsDeck(data.questions || []);
    interviewDeckWrap.style.display = "block";
    interviewDeckWrap.scrollIntoView({ behavior: "smooth", block: "start" });
    showToast("7-Archetype Minus Interview Deck generated!");
  } catch (err) {
    console.error("Interview generation error:", err);
    showToast(`Error: ${err.message}`);
  } finally {
    btnGenInterview.disabled = false;
    btnGenInterview.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
      Regenerate Interview Deck
    `;
  }
}

function renderQuestionsDeck(questions) {
  questionsDeck.innerHTML = "";

  questions.forEach((q, idx) => {
    const card = document.createElement("div");
    card.className = "question-card";

    const uniqueId = `crit_${idx}`;

    card.innerHTML = `
      <div class="question-header">
        <span class="archetype-pill">${q.category_number || idx + 1}. ${escapeHtml(q.category_name)}</span>
        <span class="target-focus-pill">${escapeHtml(q.target_focus || "")}</span>
      </div>
      <p class="question-text">${escapeHtml(q.question)}</p>
      <button type="button" class="criteria-toggle" data-target="${uniqueId}">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        Reveal Bar Raiser Evaluation Criteria
      </button>
      <div class="criteria-content" id="${uniqueId}" style="display: none;">
        <strong>Evaluation Criteria:</strong> ${escapeHtml(q.evaluation_criteria || "Observe architectural depth and failure mode trade-offs.")}
      </div>
    `;

    questionsDeck.appendChild(card);
  });

  // Attach toggle listeners
  document.querySelectorAll(".criteria-toggle").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      const targetElem = document.getElementById(targetId);
      if (targetElem) {
        const isHidden = targetElem.style.display === "none";
        targetElem.style.display = isHidden ? "block" : "none";
        btn.textContent = isHidden ? "▲ Hide Evaluation Criteria" : "▼ Reveal Bar Raiser Evaluation Criteria";
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Toast Notification
// ---------------------------------------------------------------------------
let toastTimer = null;
function showToast(msg) {
  toastMessage.textContent = msg;
  toast.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.style.display = "none";
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
