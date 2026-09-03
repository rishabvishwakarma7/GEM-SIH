# BidShield AI — GeM Bid Compliance Verification Platform

**Smart India Hackathon 2026 — Problem Statement ID 26100**  
**Organization:** Ministry of Petroleum & Natural Gas  
**Department:** Chennai Petroleum Corporation Limited (CPCL)  
**Team:** Supernova

---

## What It Does

GeM (Government e-Marketplace) tenders require procurement officers to manually check every bidder's PAN, GST, Udyam registration, company incorporation, financial statements, and other eligibility documents against the tender's stated requirements — a slow, error-prone, entirely manual process.

**BidShield AI automates this end-to-end:**

1. Upload a tender PDF → AI extracts all compliance requirements
2. Upload bidder documents → AI classifies and extracts structured fields
3. System checks identifiers against government registries
4. Deterministic rule engine produces COMPLIANT / NON-COMPLIANT / NEEDS REVIEW verdicts
5. Risk intelligence identifies suspicious documents and fraudulent patterns
6. Multi-level human review workflow routes high-risk cases to the right evaluator
7. Procurement officer makes the final decision — fully audited

**Hard architectural rule maintained throughout:** AI is used only for extraction and analysis — never for the final compliance decision. Every verdict comes from a deterministic Python rule engine.

---

## Architecture

```
gem-compliance/
├── backend/                        FastAPI + SQLAlchemy + PostgreSQL
│   ├── app/
│   │   ├── main.py                 App entrypoint, lifespan DB setup, routers
│   │   ├── config.py               Pydantic settings (reads .env)
│   │   ├── database.py             Engine, SessionLocal, Base
│   │   ├── models/                 SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── tender.py + TenderRequirement
│   │   │   ├── bidder.py + BidderDocument
│   │   │   ├── document.py         ExtractedDocumentData
│   │   │   ├── compliance.py       ComplianceResult
│   │   │   ├── verification.py     VerificationResult
│   │   │   ├── risk.py             DocumentRiskAnalysis, DuplicateDocumentMatch
│   │   │   ├── alert.py            Alert (smart alerts)
│   │   │   ├── review.py           ReviewCase, ReviewAction, FinalDecision
│   │   │   ├── notification.py
│   │   │   ├── audit.py
│   │   │   └── report.py
│   │   ├── schemas/                Pydantic request/response schemas
│   │   ├── core/                   security.py, deps.py, file_validation.py, logging
│   │   ├── api/routes/             One router per resource
│   │   │   ├── auth.py
│   │   │   ├── tenders.py
│   │   │   ├── bidders.py
│   │   │   ├── documents.py
│   │   │   ├── document_risk.py    Document risk + duplicate detection
│   │   │   ├── risk.py             Bidder risk, evidence chain, final decision
│   │   │   ├── alerts.py           Smart alert center
│   │   │   ├── reviews.py          Multi-level review workflow
│   │   │   ├── compliance.py
│   │   │   ├── verification.py
│   │   │   ├── reports.py
│   │   │   ├── audit.py
│   │   │   ├── dashboard.py
│   │   │   ├── notifications.py
│   │   │   └── users.py
│   │   └── services/
│   │       ├── ai_service.py                   Gemini LLM abstraction
│   │       ├── document_processor.py           PyMuPDF + Tesseract OCR
│   │       ├── requirement_extraction_service.py
│   │       ├── bidder_document_service.py      5-stage pipeline
│   │       ├── bidder_consistency_service.py   Cross-document identity check
│   │       ├── verification_service.py         Registry verification
│   │       ├── verification_providers.py       Mock providers (GST/PAN/MCA/Udyam/BIS)
│   │       ├── compliance_engine.py            Deterministic rule engine
│   │       ├── document_risk_service.py        PDF metadata + signal analysis
│   │       ├── duplicate_detection_service.py  SHA-256 + text similarity
│   │       ├── alert_service.py                Event-driven alert engine
│   │       ├── risk_intelligence_service.py    Deterministic risk scoring
│   │       ├── report_generator.py             ReportLab PDF + CSV
│   │       ├── notification_service.py         Email/SMS
│   │       └── audit_service.py
│   ├── init_db.py                  Creates tables + seeds admin user
│   ├── migrate_upgrade.py          Idempotent upgrade migration
│   ├── seed_demo_data.py           5-bidder demo dataset
│   ├── requirements.txt
│   ├── Procfile                    Render deployment
│   ├── render.yaml                 Render config
│   └── .env.example
├── frontend/                       React 18 + TypeScript + Vite + Tailwind CSS
│   └── src/
│       ├── api/                    Typed API clients
│       │   ├── client.ts           Axios instance (dev proxy / prod VITE_API_URL)
│       │   ├── auth.ts
│       │   ├── tenders.ts
│       │   ├── bidders.ts
│       │   ├── documents.ts
│       │   ├── compliance.ts
│       │   ├── risk.ts             Risk, evidence, final decision
│       │   ├── alerts.ts
│       │   ├── reviews.ts
│       │   ├── dashboard.ts
│       │   ├── reports.ts
│       │   ├── audit.ts
│       │   └── notifications.ts
│       ├── pages/
│       │   ├── Login.tsx
│       │   ├── Dashboard.tsx
│       │   ├── TenderList.tsx / TenderCreate.tsx / TenderDetail.tsx
│       │   ├── BidderList.tsx / BidderCreate.tsx / BidderDetail.tsx  ← upgraded
│       │   ├── TenderComparison.tsx  ← upgraded with intelligence columns
│       │   ├── Alerts.tsx            ← new: alert center
│       │   ├── ReviewQueue.tsx       ← new: review workflow
│       │   ├── Reports.tsx
│       │   ├── AuditLogs.tsx
│       │   ├── Profile.tsx
│       │   └── admin/
│       ├── components/
│       │   ├── RiskScoreCard.tsx     ← new: radial risk gauge
│       │   ├── WhyRiskyPanel.tsx     ← new: risk breakdown panel
│       │   ├── RiskTimeline.tsx      ← new: event timeline
│       │   ├── EvidenceTrailPanel.tsx ← new: evidence chain
│       │   ├── FinalDecisionPanel.tsx ← new: officer decision
│       │   ├── ComplianceDashboardPanel.tsx
│       │   ├── BidderConsistencyPanel.tsx
│       │   └── ui/                   Shared component library
│       ├── lib/
│       │   ├── risk.ts              Color/badge helpers
│       │   ├── errors.ts
│       │   ├── format.ts
│       │   └── roles.ts
│       └── context/AuthContext.tsx
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL 16+ |
| Auth | JWT (python-jose) + bcrypt |
| Document Processing | PyMuPDF (text layer), Tesseract OCR (scanned docs) |
| AI | Google Gemini (`google-genai`) — extraction only, never verdicts |
| Reports | ReportLab (PDF), csv (CSV) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Axios, Lucide icons |

---

## Features

### Core (Days 1–6)
- JWT auth with role-based access control (admin / evaluator / viewer)
- Tender PDF upload → AI requirement extraction with live status polling
- Bidder document upload → AI classification + structured field extraction
- Cross-document identity consistency check (company name / PAN / GSTIN)
- Mock government registry verification (GST, PAN, Udyam, MCA, BIS, blacklist)
- Deterministic compliance rule engine — one failed mandatory requirement forces NON_COMPLIANT regardless of score
- Bidder comparison ranked by compliance score
- PDF and CSV compliance reports
- Dashboard with live stats
- Global audit log

### Upgrade Features
- **Explainable Compliance** — every verdict has machine-readable reason codes and a full evidence chain (clause → requirement → document → extraction → verification → rule → verdict)
- **Risk Intelligence** — deterministic 0–100 risk score from 6 signal categories; AI provides narrative only, never changes the score
- **"Why Is This Bidder Risky?"** — collapsible breakdown panel with score contribution per factor
- **Document Risk Analysis** — PDF metadata anomalies, date inconsistencies, identifier mismatches, registry mismatches, type mismatches
- **Duplicate Document Detection** — SHA-256 exact match + bigram text similarity across all bidders in a tender
- **Smart Alert Center** — 13 event types, severity levels, read/dismiss, action-required flag
- **Multi-Level Review Workflow** — Evaluator → Senior Evaluator → Procurement Officer with escalation rules, review actions, and notes
- **Final Decision Panel** — Qualified / Disqualified / Clarification Required with mandatory officer remarks, versioned history, audit trail
- **Advanced Bidder Comparison** — 8 new intelligence columns: risk score, suspicious doc count, duplicate count, document completeness, identity consistency, review status

---

## Database Schema

### Original Tables
`users`, `tenders`, `tender_requirements`, `bidders`, `bidder_documents`, `extracted_document_data`, `verification_results`, `compliance_results`, `notifications`, `audit_logs`, `reports`

### Upgrade Tables (6 new)
| Table | Purpose |
|-------|---------|
| `document_risk_analyses` | Per-document suspicious signal score (0–100) |
| `duplicate_document_matches` | Pairwise similarity pairs |
| `alerts` | All system events (never deleted) |
| `review_cases` | One case per bidder in the review workflow |
| `review_actions` | Immutable log of every reviewer action |
| `final_decisions` | Officer qualification verdict (versioned) |

### Extended Columns
- `bidders` → `risk_score`, `risk_level`, `risk_factors`, `risk_summary`, `risk_analyzed_at`
- `bidder_documents` → `file_hash` (SHA-256), `document_fingerprint`
- `compliance_results` → `evidence_chain`, `risk_breakdown`

---

## API Endpoints (35+ total)

### Core
```
POST /api/auth/login
GET  /api/auth/me
GET  /api/tenders/
POST /api/tenders/
POST /api/tenders/{id}/upload
POST /api/tenders/{id}/process
GET  /api/bidders/
POST /api/bidders/
GET  /api/compliance/bidder/{id}
POST /api/compliance/bidder/{id}/evaluate
POST /api/compliance/tender/{id}/batch-evaluate
GET  /api/compliance/tender/{id}/comparison
GET  /api/reports/bidder/{id}/pdf
GET  /api/dashboard/stats
GET  /api/audit/
```

### Upgrade
```
GET  /api/bidders/{id}/risk
POST /api/bidders/{id}/risk/analyze
GET  /api/bidders/{id}/risk/timeline
GET  /api/bidders/{id}/evidence
POST /api/bidders/{id}/final-decision
GET  /api/bidders/{id}/final-decision
GET  /api/documents/{id}/risk
POST /api/documents/{id}/risk/analyze
GET  /api/documents/duplicates
POST /api/documents/{id}/duplicate-check
GET  /api/alerts/
GET  /api/alerts/unread
POST /api/alerts/{id}/read
POST /api/alerts/{id}/dismiss
GET  /api/reviews/
POST /api/reviews/
POST /api/reviews/{id}/assign
POST /api/reviews/{id}/action
POST /api/reviews/{id}/escalate
```

---

## Document Processing Pipeline

```
Stage 1: Text extraction (PyMuPDF / Tesseract OCR fallback)
Stage 2: AI classification + structured field extraction
Stage 3: Cross-document identity consistency analysis
Stage 4: Document risk analysis (6 signals → 0–100 score)   ← Upgrade
Stage 5: Duplicate detection + alert emission                ← Upgrade
```

---

## Demo Scenarios (seed_demo_data.py)

| Bidder | Verdict | Reason |
|--------|---------|--------|
| Compliant Traders Pvt Ltd | ✅ COMPLIANT | All docs clean, all registries verified, score 100% |
| Struggling Supplies LLP | ❌ NON_COMPLIANT | GST registration status = Cancelled (mandatory fail) |
| Reliable Engineering Works | 🟡 NEEDS_REVIEW | Turnover doc AI confidence = 0.38 (below threshold) |
| Shadow Tech Solutions Pvt Ltd | 🔴 HIGH_RISK | Company name mismatch + document type mismatch |
| Duplicate Doc Enterprises Ltd | 🟡 NEEDS_REVIEW + 🔁 DUPLICATE | Same turnover CA cert as Bidder 1 |

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 16+
- Tesseract OCR

### Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
pip install -r requirements.txt
```

### Database

```bash
# Create user and database
psql -U postgres -c "CREATE USER gem_user WITH PASSWORD 'gem_password';"
psql -U postgres -c "CREATE DATABASE gem_compliance OWNER gem_user;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE gem_compliance TO gem_user;"
```

### Environment

```bash
cp .env.example .env
# Edit backend/.env — minimum required:
# DATABASE_URL=postgresql://gem_user:gem_password@localhost:5432/gem_compliance
# SECRET_KEY=any-long-random-string
# GEMINI_API_KEY=your-key-from-aistudio.google.com (optional for demo)
```

### Initialize and run

```bash
python init_db.py          # creates tables + admin user
python migrate_upgrade.py  # creates upgrade tables
python seed_demo_data.py   # loads 5-bidder demo dataset

python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

---

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `SECRET_KEY` | Yes | — | JWT signing key |
| `GEMINI_API_KEY` | No | — | Required for live AI extraction |
| `AI_MODEL` | No | `gemini-2.0-flash` | Gemini model name |
| `CORS_ORIGINS` | No | localhost:5173 | Comma-separated allowed origins |
| `UPLOAD_DIR` | No | `./uploads` | File storage directory |
| `MAX_UPLOAD_SIZE_MB` | No | `20` | Max upload size |
| `NOTIFICATIONS_ENABLED` | No | `False` | Enable SMTP email alerts |
| `SMTP_HOST` | No | — | SMTP server for email alerts |

---

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@cpcl.gem` | `Admin@123` |

---

## Deployment

### Backend → Render
- **Root Directory:** `backend`
- **Language:** Python 3
- **Build Command:** `pip install -r requirements.txt && python migrate_upgrade.py && python init_db.py`
- **Start Command:** `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables:** `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `ENVIRONMENT=production`

### Frontend → Vercel
- **Root Directory:** `frontend`
- **Framework:** Vite
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Environment Variables:** `VITE_API_URL=https://your-backend.onrender.com`

---

## Key Design Principles

1. **AI extracts, rules decide** — Gemini is used upstream for understanding documents. Every compliance verdict is made by deterministic Python code in `compliance_engine.py`. AI cannot override or change a verdict.

2. **One failed mandatory requirement always wins** — regardless of overall score. Mirrors how procurement evaluators actually think.

3. **Confidence-gated trust** — extraction confidence below 0.6 automatically downgrades a result to NEEDS_REVIEW rather than trusting it silently.

4. **Mock-first, real-later** — all government registry lookups use mock data. The `VerificationProvider` abstract class means adding a real API (GSTN/MCA21/Udyam) requires writing one new class, not changing anything else.

5. **Full audit trail** — every action (document upload, verification run, compliance evaluation, risk analysis, review action, final decision) generates an immutable `AuditLog` entry.

6. **Alerts are never deleted** — dismissed alerts remain in the database for audit purposes.

7. **Final decisions are versioned** — editing a decision creates a new version row rather than overwriting history.

---

## Mock Verification Disclaimer

No code in this project calls any real government API. Every registry lookup reads from `mock_verification_data.py`. Every `VerificationResult` row carries `is_mock=True` and every generated report includes a disclaimer footer stating the verification data is simulated.

---

## Limitations

- Mock verification only — no real GSTN / Udyam / MCA21 / BIS / GeM blacklist API integrated
- AI extraction requires a Gemini API key; `seed_demo_data.py` bypasses this for demos
- File storage is local disk, not object storage
- No rate limiting on the API
- Single-tenant (CPCL/GeM branding only)

---

## GitHub Repository

https://github.com/rishabvishwakarma7/GEM-SIH
