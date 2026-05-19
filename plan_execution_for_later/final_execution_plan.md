# 🚀 Final Execution Plan: AI Resume Analysis Pipeline

Based on your confirmations, here is the tailored, phase-wise execution plan for the AI Resume Analysis feature.

## 📋 Key Confirmed Details
1. **API Key:** Added to `.env`
2. **File Formats:** PDF and DOCX both supported
3. **Database:** PostgreSQL (Database name: `ATS`)
4. **Broker:** Memurai (Valkey/Redis alternative on Windows)
5. **Scale:** 10,000+ candidates (requires batching and strong background task management)
6. **Efficiency:** Skip files that have already been scanned/analyzed.

---

## 🏗️ Phase 1: Infrastructure & Configuration (✅ Partially Completed)
**Goal:** Setup backend to handle async tasks and use the new PostgreSQL database.

* **1.1 Database Migration:** 
  * Apply migrations to the newly connected PostgreSQL `ATS` database.
  * *Command:* `python manage.py makemigrations` and `python manage.py migrate`
* **1.2 Celery App Setup:**
  * Create `core/celery.py` to initialize Celery.
  * Update `core/__init__.py` to ensure Celery loads on Django startup.
* **1.3 Memurai Connection Test:**
  * Ensure Celery can connect to `redis://localhost:6379/0` (Memurai default).
  * Run a dummy task to confirm the worker is functional.

---

## 🗄️ Phase 2: Data Models for Tracking & Deduplication
**Goal:** Modify the database schema to track analysis status and prevent re-scanning.

* **2.1 Candidate Model Update:**
  * Add `resume_text` (TextField) to `Candidate` to cache parsed text.
  * Add a `resume_hash` (CharField) to detect if a file was updated or changed. If the hash hasn't changed and text exists, **skip parsing**.
* **2.2 Application Model Update:**
  * Add boolean `ai_analysis_done` (default=False).
  * Add all scoring fields (`ai_match_score`, `ai_skills_score`, etc.) to store LLM JSON response.
* **2.3 Batch Task Tracker Model:**
  * Create `JobAnalysisTask` to track overall progress for jobs with 10k+ candidates (fields: `total`, `processed`, `status`).

---

## 📄 Phase 3: Text Extraction Engine (PDF & DOCX)
**Goal:** Robust parsing of resumes locally before sending to AI.

* **3.1 Install Parsers:** `pip install PyPDF2 python-docx`
* **3.2 Implement `resume_parser.py`:**
  * Detect file extension (.pdf or .docx).
  * Extract text and clean up whitespace/special characters.
* **3.3 Implement Caching/Deduplication Logic:**
  * Before parsing, check if `candidate.resume_text` is already populated.
  * Only parse if text is empty or if the file has been replaced with a new one.

---

## 🧠 Phase 4: AI Analysis Integration (OpenRouter / Namotron)
**Goal:** Feed parsed text and Job Description to the LLM for scoring.

* **4.1 Implement `ai_analyzer.py`:**
  * Construct system prompt for strict JSON output.
  * Pass Job Description and candidate `resume_text`.
  * Truncate text intelligently to avoid exceeding the LLM token limit.
* **4.2 Handle Rate Limits:**
  * Given the 10K+ scale, we must implement retry logic and backoff for OpenRouter API limits.

---

## ⚙️ Phase 5: Celery Task Orchestration (High Scale)
**Goal:** Manage 10,000+ candidate background processing smoothly.

* **5.1 Single Candidate Task (`analyze_single_application`):**
  * Fetch application -> Extract text (if needed) -> Call LLM -> Update application record.
  * *Condition:* If `ai_analysis_done == True`, immediately return (Skipping already scanned!).
* **5.2 Master Dispatch Task (`analyze_job_candidates`):**
  * Identify all applications for a job where `ai_analysis_done == False`.
  * Dispatch individual tasks to Celery. Update `JobAnalysisTask` tracker.
  * **Scale Consideration:** Use `apply_async` with small countdowns or Celery Chunks to avoid slamming the broker all at once for 10k users.

---

## 🖥️ Phase 6: UI & AI Insights Dashboard
**Goal:** Display progress and final rankings to the user cleanly.

* **6.1 Job Board Header Updates:**
  * Add buttons for "Total Analyzed", "Pending Profiles", and "🚀 Start AI Analysis".
* **6.2 Progress Polling:**
  * Implement frontend JavaScript to poll `/jobs/<id>/analysis-status/` every 3-5 seconds.
  * Show a dynamic progress bar for the active `JobAnalysisTask`.
* **6.3 Final Insights Rendering:**
  * Sort candidates by `ai_match_score`.
  * Display strengths, gaps, and recommendations gracefully on the AI Insights view.

---
**Ready to execute!** You can direct me to start with Phase 1 (Database Migrations & Celery Setup) whenever you're ready.
