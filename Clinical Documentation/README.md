# 🏥 ClinDoc AI — Clinical Documentation Validation System

> **Agentic AI-Based Clinical Documentation Validation** built with Python, FastAPI, SQLite, HTML, CSS, and JavaScript. Powered by **IBM Bob** for development assistance and **IBM Granite** (watsonx.ai) for AI explanations.

---

## 📋 Table of Contents
1. [What This System Does](#what-this-system-does)
2. [Project Structure](#project-structure)
3. [Quick Start (3 Steps)](#quick-start-3-steps)
4. [Features](#features)
5. [IBM Granite Integration](#ibm-granite-integration)
6. [API Reference](#api-reference)
7. [How Validation Works](#how-validation-works)
8. [Student Guide](#student-guide)

---

## 🎯 What This System Does

This is a **hospital clinical documentation system** that:
- Stores clinical documents (discharge summaries, prescriptions, lab reports, etc.)
- **Automatically validates** them using AI (IBM Granite) or rule-based logic
- Detects issues like: **missing fields**, **ICD-10 code mismatches**, **drug interactions**, **incomplete notes**
- Gives every document a **quality score (0–100)**
- Shows everything on a **professional hospital dashboard** with charts and tables

---

## 📁 Project Structure

```
Clinical Documentation/
├── app/
│   ├── main.py                  ← FastAPI app entry point
│   ├── models/
│   │   └── database.py          ← SQLite tables (Patient, Doctor, Document, Issue)
│   ├── routers/
│   │   └── api.py               ← All REST API endpoints
│   ├── services/
│   │   ├── ai_validator.py      ← IBM Granite + rule-based validation
│   │   └── seeder.py            ← Synthetic data generator
│   ├── static/
│   │   ├── css/style.css        ← Dashboard styles
│   │   └── js/utils.js          ← Shared JS helpers
│   └── templates/
│       ├── _sidebar.html        ← Navigation sidebar (reused in all pages)
│       ├── index.html           ← Dashboard page (charts + stats)
│       ├── documents.html       ← Documents list with search/filter
│       ├── patients.html        ← Patient registry
│       ├── issues.html          ← Validation issues tracker
│       └── new_document.html    ← 3-step document creation wizard
├── run.py                       ← One-command launcher
├── requirements.txt             ← Python dependencies
└── env.example                  ← Environment variables template
```

---

## ⚡ Quick Start (3 Steps)

### Prerequisites
- Python 3.10 or newer
- Internet connection (for pip packages and Chart.js CDN)

### Step 1 — Clone / Download the project
```bash
# If using git:
git clone <your-repo-url>
cd "Clinical Documentation"

# Or just navigate to the project folder:
cd "c:\Clinical Documentation"
```

### Step 2 — Run the launcher
```bash
python run.py
```
This automatically:
- Installs all Python dependencies
- Creates the SQLite database
- Seeds 60 patients, 16 doctors, 120 documents, and validation issues
- Starts the web server

### Step 3 — Open your browser
```
http://127.0.0.1:8000
```

> **That's it!** The full dashboard loads with synthetic hospital data.

---

## 🌟 Features

| Feature | Description |
|---|---|
| **Dashboard** | Live stats cards, 4 interactive charts (status, scores, departments, severity) |
| **Document Management** | Search, filter, paginate, view details, delete documents |
| **AI Validation** | One-click AI analysis per document — scores 0–100 + issue detection |
| **Validation Issues** | Track, filter, and resolve flagged issues per document |
| **Patient Registry** | Searchable patient list with demographics |
| **3-Step Document Wizard** | Guided form with auto-fill ICD codes, pre-submission checks |
| **Toast Notifications** | Success/error feedback on every action |
| **Responsive Design** | Professional hospital UI, works on tablet/desktop |

---

## 🤖 IBM Granite Integration

The system supports **IBM Granite 3 8B Instruct** via watsonx.ai for enriched AI explanations.

### Enable IBM Granite
1. Create an IBM Cloud account at [ibm.com/cloud](https://www.ibm.com/cloud)
2. Create a watsonx.ai project at [dataplatform.cloud.ibm.com](https://dataplatform.cloud.ibm.com)
3. Generate an API key from IBM Cloud IAM
4. Copy `env.example` to `.env` and fill in your credentials:

```env
IBM_GRANITE_API_KEY=your_real_api_key
IBM_PROJECT_ID=your_project_id
IBM_GRANITE_URL=https://us-south.ml.cloud.ibm.com
IBM_GRANITE_MODEL_ID=ibm/granite-3-8b-instruct
```

### Without IBM Granite (Default)
The system **fully works** without any API key using the built-in rule-based validator:
- Checks for missing required fields
- Validates ICD-10 code alignment with diagnosis
- Detects drug interactions (12 common pairs)
- Checks for required document sections (Assessment, Plan)
- Verifies medication dosage presence

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/stats` | Dashboard aggregate statistics |
| GET | `/api/documents` | List documents (supports: page, search, status, department, doc_type) |
| GET | `/api/documents/{id}` | Get single document with issues |
| POST | `/api/documents` | Create new document |
| POST | `/api/documents/{id}/validate` | Run AI validation on document |
| PATCH | `/api/documents/{id}` | Update document fields |
| DELETE | `/api/documents/{id}` | Delete document |
| GET | `/api/patients` | List all patients (supports: search) |
| GET | `/api/doctors` | List all doctors |
| GET | `/api/issues` | List validation issues (supports: resolved, severity) |
| PATCH | `/api/issues/{id}/resolve` | Mark issue as resolved |

**Interactive API docs:** http://127.0.0.1:8000/docs

---

## 🔍 How Validation Works

```
Document submitted
        ↓
Rule-Based Engine runs first (always):
  ├─ Check: All required fields present?
  ├─ Check: ICD-10 code matches diagnosis?
  ├─ Check: Drug interactions in medications?
  ├─ Check: Assessment + Plan sections in notes?
  └─ Check: Dosages specified for medications?
        ↓
IBM Granite (if API key configured):
  └─ Sends document summary to watsonx.ai
     Gets 2-3 sentence clinical quality assessment
        ↓
Score calculated (0–100):
  - Start at 100
  - Deduct: missing field (-15), ICD mismatch (-20),
            drug interaction (-25), incomplete note (-10)
        ↓
Status assigned:
  - Score ≥ 75 + no critical issues → "validated" ✅
  - Score ≥ 50 → "review" 🔵
  - Score < 50 → "rejected" ❌
        ↓
Issues saved to database
Results shown in dashboard
```

---

## 📚 Student Guide

### Understanding the Code

**`app/models/database.py`** — The database layer
- Uses **SQLAlchemy** (Python's most popular database library)
- Defines 4 tables: `patients`, `doctors`, `clinical_documents`, `validation_issues`
- Uses **SQLite** (a single file database — no server needed!)

**`app/services/ai_validator.py`** — The brain
- `validate_document()` is the main function
- `_rule_based_validate()` checks the document using simple Python logic
- `_call_granite()` calls IBM's Granite AI model via REST API

**`app/routers/api.py`** — The REST API
- Each `@router.get/post/patch/delete` defines one API endpoint
- Uses **Pydantic** models to validate incoming JSON data
- Returns JSON that the frontend JavaScript reads

**`app/templates/*.html`** — The web pages
- Each page uses **Jinja2** templating (server renders HTML)
- JavaScript calls the API endpoints using `fetch()`
- Charts are drawn using **Chart.js** (loaded from CDN)

### Key Learning Concepts
| Concept | Where to See It |
|---|---|
| Async Python | All `async def` functions in `api.py` |
| REST API design | `app/routers/api.py` |
| SQLite + ORM | `app/models/database.py` |
| AI API call | `ai_validator.py` → `_call_granite()` |
| Dynamic HTML | Any template's `<script>` block |
| CSS Variables | `style.css` `:root { }` section |

---

## 🛠 Manual Setup (Alternative to run.py)

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy env.example .env          # Windows
# cp env.example .env          # Mac/Linux

# Start server
uvicorn app.main:app --reload --port 8000
```

---

## 🏷 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI |
| Database | SQLite + SQLAlchemy (async) |
| AI Engine | IBM Granite 3 8B (watsonx.ai) + Rule-based fallback |
| Frontend | HTML5, CSS3 (custom design), Vanilla JavaScript |
| Charts | Chart.js 4 |
| Dev Tool | IBM Bob (AI coding assistant) |

---

*Built with ❤️ using IBM Bob and IBM Granite for educational purposes.*
