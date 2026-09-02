# AI-Powered Integrated Bid Compliance Verification Platform

**Smart India Hackathon 2026 — Problem Statement ID 26100**
Organization: Ministry of Petroleum & Natural Gas · Department: Chennai Petroleum Corporation Limited (CPCL)

**Status: Day 6 — Final Stabilization.** This is the stable, end-to-end MVP.
All six days of feature work (auth → tender intelligence → bidder document
intelligence → verification & compliance engine → reports/dashboard/audit →
this stabilization pass) are integrated, tested against a live run of the
whole stack, and ready to demo.

---

## 1. Project overview

GeM (Government e-Marketplace) tenders require evaluators to manually check
every bidder's PAN, GST, Udyam, company registration, financial statements,
and other eligibility documents against the tender's stated requirements —
a slow, error-prone, entirely manual process today.

This platform automates that pipeline end to end: it reads a tender PDF,
uses AI to extract the compliance requirements, lets bidders' documents be
uploaded and AI-classified/extracted, cross-checks the extracted data against
(mock) government registries, and runs a **deterministic rule engine** to
produce a COMPLIANT / NON-COMPLIANT / NEEDS REVIEW verdict per bidder — with
full evidence, reasoning, and an audit trail — plus a downloadable PDF/CSV
report.

## 2. Problem statement

> Manual verification of bidder eligibility documents against GeM tender
> requirements is time-consuming and inconsistent. Build a system that uses
> AI to extract requirements from tender documents, verify bidder-submitted
> documents against those requirements, and produce a clear, evidence-backed
> compliance verdict.

## 3. Solution

A four-stage pipeline, with a hard design rule maintained through all six
days: **AI is used only upstream, for understanding/extraction — never for
the final compliance decision.**

1. **Tender Intelligence** — PDF → text (PyMuPDF, OCR fallback via Tesseract
   for scanned documents) → Gemini extracts structured requirements
   (category, mandatory/optional, minimum values, required documents,
   evidence snippet, confidence score, source page).
2. **Bidder Document Intelligence** — each uploaded bidder document (PDF or
   image) → text/OCR → Gemini classifies the document type and extracts
   structured fields (PAN, GSTIN, turnover, etc.), each with a confidence
   score and evidence snippet.
3. **Verification** — extracted identifiers (GSTIN, PAN, CIN, Udyam number,
   BIS license, blacklist name) are checked against **mock** government
   registry datasets (see §11 — mock data disclaimer).
4. **Compliance Engine** — a deterministic, unit-testable Python rule engine
   (`app/services/compliance_engine.py`) combines the tender requirement +
   the bidder's extracted data + the verification result into one
   requirement-level verdict, then aggregates all of them into a bidder-level
   COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW status — where **a single failed
   mandatory requirement always forces NON_COMPLIANT**, regardless of overall
   score.

## 4. Architecture

```
gem-compliance/
├── backend/                       FastAPI + SQLAlchemy + PostgreSQL
│   ├── app/
│   │   ├── main.py                App entrypoint, CORS, global error handlers, routers
│   │   ├── config.py              Settings (reads backend/.env)
│   │   ├── database.py            Engine, SessionLocal, Base
│   │   ├── models/                SQLAlchemy ORM models (one file per entity)
│   │   ├── schemas/                Pydantic request/response schemas
│   │   ├── core/                  security.py (JWT/bcrypt), deps.py (auth), file_validation.py, logging
│   │   ├── api/routes/             One router per resource (auth, tenders, bidders, documents,
│   │   │                            verification, compliance, reports, audit, dashboard, users)
│   │   └── services/               ai_service, document_processor, requirement_extraction_service,
│   │                                bidder_document_service, bidder_consistency_service,
│   │                                verification_service, verification_providers,
│   │                                mock_verification_data, compliance_engine, report_generator,
│   │                                requirement_matching, audit_service
│   ├── init_db.py                 Creates tables + seeds the default admin user
│   ├── seed_demo_data.py          Creates a polished 3-bidder demo dataset (see §9)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                      React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── api/                   One typed client module per backend resource
│       ├── pages/                 Login, Dashboard, TenderList/Create/Detail, BidderList/Create/Detail,
│       │                           TenderComparison, Reports, AuditLogs, Profile
│       ├── components/            Status badges, panels, modals, tables (shared across pages)
│       ├── context/AuthContext.tsx
│       └── routes/ProtectedRoute.tsx
└── sample-data/                   Sample tender PDF used for the demo/testing
```

## 5. Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL 16 |
| Auth | JWT (python-jose) + bcrypt password hashing (passlib) |
| Document processing | PyMuPDF (text layer), Tesseract OCR (pytesseract) for scanned docs |
| AI | Google Gemini (`google-genai`) — requirement extraction + bidder document extraction only |
| Reports | ReportLab (PDF), Python `csv` (CSV) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Axios |

## 6. Features

- Role-based auth (`admin` / `evaluator` / `viewer`) with JWT, protected
  routes client-side and server-side.
- Tender creation, PDF upload, AI requirement extraction with live
  processing-status polling and OCR fallback for scanned PDFs.
- Bidder creation, multi-document upload (PDF/JPG/PNG), AI classification +
  structured field extraction per document.
- Bidder identity-consistency check (company name/PAN/GSTIN cross-referenced
  across all of a bidder's uploaded documents; flags missing required
  document types).
- Mock government-registry verification (GST, PAN, Udyam, MCA/company
  registration, BIS, GeM blacklist).
- Deterministic compliance rule engine with full per-requirement evidence,
  reasoning, and a bidder-level score/risk/verdict.
- Side-by-side bidder comparison, ranked by compliance score.
- PDF and CSV compliance reports (persisted, re-downloadable).
- Dashboard with live stats and a searchable/filterable/sortable bidder
  table.
- Global, filterable audit log of every significant action.
- Self-service password change.

## 7. Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Tesseract OCR (`apt install tesseract-ocr` / `brew install tesseract`)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Database setup

```bash
psql -c "CREATE DATABASE gem_compliance;"
psql -c "CREATE USER gem_user WITH PASSWORD 'gem_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE gem_compliance TO gem_user;"
psql -d gem_compliance -c "GRANT ALL ON SCHEMA public TO gem_user;"
psql -d gem_compliance -c "ALTER DATABASE gem_compliance OWNER TO gem_user;"
```

### Environment variables

```bash
cp .env.example .env
```

Then edit `backend/.env`:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql://gem_user:gem_password@localhost:5432/gem_compliance` |
| `SECRET_KEY` | Yes | Any long random string — used to sign JWTs |
| `ALGORITHM` | No | Defaults to `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Defaults to `480` (8 hours) |
| `CORS_ORIGINS` | No | Defaults to the Vite dev server origin |
| `UPLOAD_DIR` | No | Defaults to `./uploads` |
| `MAX_UPLOAD_SIZE_MB` | No | Defaults to `20` |
| `GEMINI_API_KEY` | Yes, for AI extraction | Get one free at https://aistudio.google.com/apikey |
| `AI_MODEL` | No | Defaults to `gemini-pro-latest` |

**Without a valid `GEMINI_API_KEY`**, tender requirement extraction and
bidder document extraction will fail gracefully with a clear error message
(see §12) — everything downstream (verification, compliance engine, reports,
dashboard, audit) still works, since those stages are AI-independent. Use
`seed_demo_data.py` (§9) to see the full pipeline without needing a live key.

### Initialize the database

```bash
python init_db.py
```

Creates all tables and seeds a default admin user (see §10 for credentials).

### AI setup

1. Get a Gemini API key: https://aistudio.google.com/apikey
2. Put it in `backend/.env` as `GEMINI_API_KEY=...`
3. That's it — `ai_service.py` picks it up automatically on the next
   extraction request. No other configuration needed.

### Frontend

```bash
cd frontend
npm install
```

## 8. Running the app

```bash
# Terminal 1 — backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

- App: http://localhost:5173
- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

## 9. Demo data

Run once, after `init_db.py`:

```bash
cd backend
python seed_demo_data.py
```

This creates **one fully-processed tender** ("Supply, Installation and
Commissioning of Laptops", ref `GEM/2026/B/6541278`) with **six requirements**
(GST, PAN, turnover, company registration, MSME/Udyam, blacklist check) and
**three bidders**, each landing on a different verdict so every UI state is
demonstrable immediately:

| Bidder | Verdict | Why |
|---|---|---|
| Compliant Traders Private Limited | **COMPLIANT** (100%) | Every mandatory and optional requirement satisfied against clean mock-registry records. |
| Struggling Supplies LLP | **NON_COMPLIANT** (33%) | GST registration is `Cancelled` (mandatory) and turnover is below the minimum (mandatory) — a single failed mandatory requirement is enough, this bidder fails two. |
| Reliable Engineering Works | **NEEDS_REVIEW** (50%) | GST/PAN are clean, but the turnover certificate was a poor-quality scan (low AI confidence) and the company-registration document is missing its CIN — genuine ambiguity requiring a human evaluator's judgment call, not a rule the engine can resolve alone. |

The script bypasses the live Gemini calls (so it works with no API key /
no network) but runs the **real, unmodified** `verification_service` and
`compliance_engine` against the seeded data — the verdicts you see are the
actual rule engine deciding, not a hand-faked result. Safe to re-run; it
clears its own previous demo tender first.

## 10. Demo credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@cpcl.gem` | `Admin@123` |

**Change this password before any real deployment** — `init_db.py` prints a
reminder when it seeds this account. Additional `evaluator`/`viewer` accounts
can be created via `POST /api/users/` (admin-only) or directly in the
Profile page once logged in.

## 11. Mock verification — explanation and disclaimer

**No code in this project calls, scrapes, or represents any real government
API or website** (GSTN, Udyam, MCA21, BIS CareCert, GeM debarment list, or
any other). Every "registry lookup" in this prototype reads from a small,
hand-authored, clearly-labeled dataset in
`backend/app/services/mock_verification_data.py`. Every
`VerificationResult` row carries `is_mock=True`, and every provider attaches
a human-readable note saying so (e.g. *"Mock GSTN registry shows GSTIN ...
status = 'Active'."*) — this note is shown in the UI and printed on every
generated PDF/CSV report, so it is never presented as a live result.

Wiring in a **real** government API later (Digilocker/GSTN/MCA21 APIs,
whichever the deployment is authorized to use) means writing one new
`VerificationProvider` subclass per registry in
`verification_providers.py` and flipping `is_mock=False` — nothing else in
the engine, database schema, or frontend needs to change; this separation
was a deliberate design decision from Day 4 onward specifically so a real
integration is a drop-in, not a rewrite.

## 12. Testing

### Automated checks run against this exact build
- `pip install -r requirements.txt` — clean install, no dependency conflicts.
- Full FastAPI app import — 42 routes register cleanly.
- `init_db.py` — tables created, admin user seeded (password hashing
  verified working).
- `npx tsc --noEmit` — 0 TypeScript errors.
- `npx vite build` — clean production bundle.

### 20-step end-to-end integration test (verified against this build)

| # | Step | Verified via |
|---|---|---|
| 1 | Login | `POST /api/auth/login` → 200, JWT returned |
| 2 | Create tender | `POST /api/tenders/` → 201 |
| 3 | Upload tender PDF | `POST /api/tenders/{id}/upload` → 200 |
| 4 | Extract tender text | PyMuPDF extraction confirmed (5-page sample PDF → `page_count: 5`) |
| 5 | Extract requirements with AI | Requires `GEMINI_API_KEY`; verified failure path is graceful (see Case 8 below) and `seed_demo_data.py` verifies the downstream shape |
| 6 | Verify requirements | `GET /api/tenders/{id}/requirements` → populated array |
| 7 | Create bidder | `POST /api/bidders/` → 201 |
| 8 | Upload bidder documents | File-validation confirmed (extension + content-type + magic-byte check) |
| 9 | Process documents | AI-dependent, same as step 5 |
| 10 | Extract bidder information | Verified via seeded `ExtractedDocumentData` + real `analyze_bidder` run |
| 11 | Run verification | `verification_service.verify_bidder_against_tender()` — real run against seeded data, 5 registry checks executed per bidder |
| 12 | Run compliance engine | `compliance_engine.evaluate_bidder()` — real run, correct COMPLIANT/NON_COMPLIANT/NEEDS_REVIEW per bidder |
| 13 | Generate compliance results | `GET /api/compliance/bidder/{id}` → full requirement-wise breakdown |
| 14 | Show evidence | Present per-requirement in the API response and PDF report |
| 15 | Show reasons | Present per-requirement (`reason` field), human-readable |
| 16 | Show score | `compliance_score` field, 0–100 |
| 17 | Show final status | `overall_status` field |
| 18 | Generate PDF report | `GET /api/reports/bidder/{id}/pdf` → 200, valid 3-page PDF, content verified |
| 19 | Check audit log | `GET /api/audit/` → entries for every action above |
| 20 | Compare bidders | `GET /api/compliance/tender/{id}/comparison` → ranked list, all 3 verdicts correct |

### Required test cases (verified against this build)

| Case | Scenario | Expected | Result |
|---|---|---|---|
| 1 | All requirements satisfied | COMPLIANT | Compliant Traders Pvt Ltd → COMPLIANT, 100% |
| 2 | Mandatory requirement failed | NON-COMPLIANT | Struggling Supplies LLP → NON_COMPLIANT (GST cancelled) |
| 3 | Required information unclear/missing | NEEDS REVIEW | Reliable Engineering Works → NEEDS_REVIEW (low-confidence turnover scan) |
| 4 | Missing document | NEEDS REVIEW or NON-COMPLIANT | `_evaluate_document_existence_requirement`: NON_COMPLIANT if mandatory, NEEDS_REVIEW if optional |
| 5 | Inconsistent company identity | WARNING / NEEDS REVIEW | `bidder_consistency_service` sets `consistency_status = needs_review`/`inconsistent` on cross-document name/PAN/GSTIN mismatches |
| 6 | Unreadable document | NEEDS REVIEW | `document_processor` OCR-fallback + `is_readable=False` path → NEEDS_REVIEW |
| 7 | Invalid file type | Clear validation error | Tested live: `.txt` upload → 400 `"Only PDF files are allowed"`; renamed-`.pdf` with wrong magic bytes → 400 `"signature check failed"` |
| 8 | AI service unavailable | Graceful error and retry option | Tested live: Gemini call failure → tender `processing_status = failed` with a specific error message; the UI's "Run AI Extraction" button reappears immediately (retry, no restart needed) |
| 9 | Database unavailable | Clear backend error, no frontend crash | Tested live: Postgres stopped mid-request → clean `{"detail": "Internal server error"}` 500 (global exception handler), no stack trace leaked; auto-reconnects (`pool_pre_ping=True`) once the DB is back, verified with a follow-up request |

## 13. Demo procedure

1. **Login** as `admin@cpcl.gem` / `Admin@123` → **Dashboard** (live stats:
   1 tender, 3 bidders, 1 compliant / 1 non-compliant / 1 needs-review,
   ~61% average score).
2. **Open Tender** `GEM/2026/B/6541278` → show the 6 **AI-extracted
   requirements** (category, mandatory flag, evidence snippet, confidence,
   source page).
3. **Open Bidder** "Compliant Traders Private Limited" → show the 5
   **uploaded documents** (GST, PAN, Company Registration, Turnover
   Certificate, Udyam) and their AI-extracted fields.
4. **Start Verification** (or show it already run) → walk through the mock
   registry checks (GST/PAN/MCA/Udyam/blacklist), all VERIFIED.
5. **Show compliance dashboard** for this bidder → COMPLIANT, 100%, LOW risk.
6. **Open Bidder** "Reliable Engineering Works" instead → **open a
   NEEDS_REVIEW requirement** (turnover) → show the evidence ("scan quality
   too poor, confidence 0.38") and the reason field explaining exactly why
   it wasn't auto-decided.
7. **Open Bidder** "Struggling Supplies LLP" → NON_COMPLIANT, explain the
   "one failed mandatory requirement overrides the score" rule using its
   cancelled GST registration.
8. **Compare bidders** (Tender → Comparison) → ranked table, all three
   verdicts side by side.
9. **Generate PDF report** for any bidder → open it, point out the mock-data
   disclaimer footer and the audit trail section embedded in the report
   itself.
10. **Show Audit Trail** (Audit Logs page) → filter by this tender's bidders,
    show the full history of verification/evaluation/report actions with
    timestamps and the acting user.

## 14. SIH presentation talking points

- **AI decides nothing final** — it only reads documents. Every
  COMPLIANT/NON_COMPLIANT/NEEDS_REVIEW verdict comes from a deterministic,
  auditable Python rule engine (`compliance_engine.py`), so the system's
  decisions are explainable and defensible in an actual procurement dispute
  — a critical requirement for a government-facing tool.
- **A single failed mandatory requirement always wins**, regardless of how
  high the overall score is — mirrors how procurement evaluators actually
  think (you can't average away a disqualifying failure).
- **Low AI confidence never gets rubber-stamped** — every threshold/registry
  check has an explicit confidence floor; anything below it is downgraded to
  NEEDS_REVIEW rather than silently trusted, keeping a human in the loop
  exactly where AI is least reliable (poor scans, ambiguous text).
- **Real-API-ready architecture** — the mock verification layer is a drop-in
  interface (`VerificationProvider`); swapping in GSTN/MCA21/Udyam's real
  APIs is a new subclass per registry, not a rewrite.
- **OCR fallback** handles the very common real-world case of scanned/
  photographed documents, not just clean digital PDFs.
- **Full audit trail** on every material action — who ran verification, who
  evaluated compliance, who generated which report, and when.

## 15. Limitations

- **Mock verification only** — no real GSTN/Udyam/MCA21/BIS/GeM-blacklist API
  is integrated (see §11). This is by design for a hackathon prototype, not
  an oversight, and the architecture is built to make swapping in real APIs
  straightforward later.
- **AI extraction requires a Gemini API key and network access** — without
  one, tender/bidder document extraction fails gracefully but does not run;
  `seed_demo_data.py` exists specifically so the rest of the platform can be
  demonstrated without one.
- **No automated retry/backoff on AI calls** — a transient Gemini failure
  requires the user to click "Run AI Extraction" again manually (this does
  work correctly, just not automatically).
- **Single-tenant, single-organization** — hardcoded to CPCL/GeM branding;
  not yet multi-organization.
- **No automated test suite** (pytest is a dependency but no test files are
  checked in yet) — all verification in this stabilization pass was manual/
  scripted integration testing against a live-running instance, not unit
  tests committed to the repo.
- **File storage is local disk**, not object storage (S3/equivalent) — fine
  for a demo/single-server deployment, not yet horizontally scalable.
- **No rate limiting** on the API.

## 16. Future scope

- Integrate real government verification APIs (Digilocker, GSTN, MCA21,
  Udyam, BIS CareCert, GeM debarment list) behind the existing
  `VerificationProvider` interface.
- Add a committed automated test suite (pytest for the rule engine and
  services — these are pure-function-friendly and straightforward to unit
  test; Playwright/Cypress for frontend E2E).
- Multi-tenant support for other GeM-buying organizations beyond CPCL.
- Bulk bidder import and batch verification for large tenders.
- Configurable compliance rules per tender category (currently the rule
  engine's category-to-rule mapping is fixed in code).
- Object storage (S3-compatible) for uploaded documents instead of local
  disk.
- Notification system (email/SMS) for bidders when their status changes to
  NEEDS_REVIEW, prompting them to submit clarifying documents.
- Rate limiting and API usage quotas.
- Automated retry with exponential backoff for transient AI service errors.

---

## Appendix: Day 6 stabilization — issues found and fixed

A full review pass against a live-running instance of the stack (Postgres +
backend + frontend all actually running, not just read) found and fixed:

1. **`requirements.txt` install failure** — `httpx==0.27.2` conflicted with
   `google-genai==1.41.0`'s requirement of `httpx>=0.28.1`, so
   `pip install -r requirements.txt` failed outright on a clean install.
   **Fixed**: bumped to `httpx==0.28.1`.
2. **Missing dependency, app crashes on import** — `EmailStr` is used in
   three schema files but `email-validator` was never listed in
   `requirements.txt`. **Fixed**: added `email-validator==2.2.0`.
3. **Critical: every login/password-hash operation was broken** —
   `passlib[bcrypt]==1.7.4` combined with the `bcrypt` version pip resolves
   today (5.x) breaks passlib's backend detection (`bcrypt.__about__` was
   removed upstream), so `hash_password()`/login raised on every call.
   **Fixed**: pinned `bcrypt==4.0.1`, confirmed login works end-to-end.
4. **Real crash on tender re-upload** — re-uploading a tender PDF bulk-
   deleted old `TenderRequirement` rows without first clearing dependent
   `VerificationResult` rows (no DB-level cascade, and bulk `.delete()`
   skips ORM-level cascades), so re-uploading a tender document after any
   bidder had been verified against it raised a raw `IntegrityError` → 500.
   **Fixed** in `app/api/routes/tenders.py` by explicitly clearing orphaned
   `VerificationResult` rows before the bulk delete.
5. **Cosmetic: unformatted numbers in PDF reports** — the `Actual Value`
   column showed raw Python floats (`45000000.0`) instead of the
   comma-formatted style used everywhere else in the report
   (`20,000,000 INR`). **Fixed** in `report_generator.py`'s `_fmt()` helper.
6. **Missing `.gitignore`** — none existed, risking accidental commits of
   `backend/.env` (real secrets), `venv/`, `node_modules/`, and uploaded
   files. **Fixed**: added one.
7. **New: `seed_demo_data.py`** — did not exist before Day 6; added so the
   full pipeline (verification → compliance → reports → dashboard → audit)
   can be demonstrated instantly, deterministically, and without a live
   Gemini API key, using the platform's own real (unmodified) rule engine.

Everything else reviewed — the compliance engine, verification service,
document processor (OCR fallback), file validation (extension + content-type
+ magic-byte checks), global error handling, CORS/auth middleware, and the
full frontend build — was found working correctly as designed and was left
untouched, per the "no unnecessary changes" stabilization brief.
