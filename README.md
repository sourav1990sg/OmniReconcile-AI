# OmniReconcile AI

## Enterprise Restaurant Financial Intelligence Platform

Transform restaurant POS and marketplace settlement data into audited financial reconciliation, executive analytics, and actionable business intelligence.

**Supports:** Petpooja POS • Swiggy • Zomato

OmniReconcile AI is an upload-driven web application that detects POS and settlement files, reconciles order-level payouts, optionally verifies commercial agreements, and surfaces audited analytics and business intelligence through an interactive dashboard. Financial KPIs are computed once on the backend (`AnalyticsReport`); the React UI displays, filters, and drills into those results without recalculating business values.

---

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.2.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen)](#current-status)

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Solution Overview](#solution-overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Application Workflow](#application-workflow)
- [Technology Stack](#technology-stack)
- [Folder Structure](#folder-structure)
- [Dashboard Overview](#dashboard-overview)
- [Business Intelligence](#business-intelligence)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [API Overview](#api-overview)
- [Current Status](#current-status)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## Problem Statement

Multi-outlet restaurants selling through Swiggy and Zomato receive settlement files whose commission, taxes, discounts, and payout lines rarely line up cleanly with POS order exports. Finance teams typically reconcile in spreadsheets: matching order IDs by hand, debating which date columns to trust, and rebuilding the same commission and GST checks every month.

That process is slow, error-prone, and opaque. Operators need a system that:

- Accepts real Petpooja, Swiggy, and Zomato files without brittle filename assumptions
- Matches and verifies payouts with a single audited calculation path
- Explains discrepancies with analytics and decision-oriented insights
- Exports filtered results for finance and operations review

---

## Solution Overview

OmniReconcile AI runs as a FastAPI backend (`omni-backend`) plus a React / TypeScript single-page frontend. Operators upload POS and settlement files into an in-memory session. Upload Intelligence classifies files by column content, validates them, and locks POS before settlement commit. The pipeline then reconciles orders, applies platform financial engines, optionally verifies commercial agreements, classifies business-rule statuses, and emits `AnalyticsReport` and `BusinessIntelligenceReport` payloads consumed by the Interactive Intelligence shell.

The product is **upload-driven**: production runtime does not depend on bundled restaurant Excel fixtures. Sessions are held in memory for the life of the API process.

---

## Key Features

### Upload Intelligence

- Column-based file detection (does not rely on filenames alone)
- Preview cards with status, findings, outlets, and date ranges
- Session lock after POS commit; settlement requires locked POS
- POS replace flow with explicit confirmation
- Coverage summary between POS and settlement periods

### Financial Reconciliation

- Reconciliation Engine V2 matching POS orders to settlement rows
- Business-rules classification of recon outcomes (statuses / exceptions)
- Order-level financial breakdown available in the Reconciliation workspace

### Settlement Verification

- Swiggy and Zomato settlement parsers into a canonical settlement model
- Platform Financial Engines (Sprint 6A) derive payout components from settlement columns
- Settlement ingestion gated by Upload Intelligence

### Commercial Agreement Verification

- Optional upload of agreement documents (PDF / DOCX / TXT)
- Agreement store snapshot and rule edit / approve APIs
- Coverage and verification layered on top of settlement results (does not replace financial engines)

### Analytics

- Backend `AnalyticsEngine` builds executive, financial, platform, outlet, chart, and KPI surfaces
- Trends and day buckets use reconciled row dates
- Single audited KPI source: `AnalyticsReport`

### Business Intelligence

- Deterministic `BusinessIntelligenceEngine` decision layer
- Insight, risk, opportunity, recommendation, and priority-action cards
- Consumes analytics context; does not redefine financial formulas

### Interactive Dashboard

- Global filter bar (period, outlet, platform, payment / agreement / settlement status, search)
- Cross-filtering across charts, scorecards, and tables
- KPI explainability dialogs (formula / source fields)
- Drill-down dialogs and drill-through into Reconciliation
- Session persistence for filters and active tab (`sessionStorage`)

### Executive Reporting

- Print-friendly executive report view (`window.print`)
- KPI strips and leaderboard-style outlet / platform surfaces on the Executive tab

### Exports

- Client-side CSV, Excel (`.xlsx`), and PDF reconciliation exports
- Intelligence shell exports the **current filtered** order view
- Chart series CSV download from interactive chart panels

### Data Quality

- Outlet normalization via `outlet_map.json` (RID / label → canonical outlet name)
- Display guard: unmapped outlets show as “Outlet Not Mapped” (never literal `"Unknown"`)

### Date Standardization

- Enterprise date parser (`backend/common/date_parser.py`) for ingest paths
- Explicit ISO and Indian `DD/MM/YYYY` / `DD-MM-YYYY` handling (no bare locale guessing)
- Correct May / June period ranges for slash vs ISO source formats

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     React SPA (Vite :8080)                      │
│  Upload UI · IntelligenceShell · Filters · Charts · Exports     │
│                         fetch /api/*                            │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Vite proxy → :8000
┌───────────────────────────────▼─────────────────────────────────┐
│                 FastAPI  OmniReconcile AI 2.2.0                 │
│  Upload Intelligence · Session · Pipeline · Dispute (Gemini)    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ POS Ingestion │     │ Settlement      │     │ Agreement       │
│ Petpooja      │     │ Swiggy / Zomato │     │ Engine (opt.)   │
└───────┬───────┘     └────────┬────────┘     └────────┬────────┘
        │                      │                       │
        └──────────┬───────────┴───────────┬───────────┘
                   ▼                       ▼
           ┌───────────────┐      ┌────────────────┐
           │ Reconciliation│─────▶│ Platform       │
           │ Engine V2     │      │ Financial Eng. │
           └───────┬───────┘      └────────┬───────┘
                   │                       │
                   ▼                       ▼
           ┌───────────────┐      ┌────────────────┐
           │ Business Rules│      │ AnalyticsEng.  │
           └───────┬───────┘      │ → AnalyticsReport
                   │              └────────┬───────┘
                   │                       ▼
                   │              ┌────────────────┐
                   └─────────────▶│ BI Engine      │
                                  │ → BI Report    │
                                  └────────────────┘
```

**Design rules enforced in code**

- React never recomputes financial KPIs; it projects and filters `AnalyticsReport` fields.
- `BusinessIntelligenceReport` is a decision layer only.
- Canonical ingest dates go through the shared enterprise date parser.

---

## Application Workflow

```
Upload POS (Petpooja)
        ↓
Upload Intelligence (detect / preview / validate)
        ↓
Commit POS → session lock
        ↓
Upload Settlement (Swiggy / Zomato)
        ↓
Optional Agreement upload
        ↓
Run Reconciliation
        ↓
Platform financial verification + Business Rules
        ↓
Optional Agreement verification
        ↓
AnalyticsReport
        ↓
BusinessIntelligenceReport
        ↓
Interactive Dashboard (Executive / Finance / Operations / Recon / Agreements)
        ↓
CSV · Excel · PDF · Print report
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI (`OmniReconcile AI` v2.2.0), Uvicorn |
| Backend language | Python 3 |
| Data processing | pandas, openpyxl |
| Documents | pypdf, python-docx |
| Optional AI assist | Google Generative AI (`gemini-1.5-flash`) for dispute email drafts |
| Frontend | React 19, TypeScript, Vite 8 |
| Routing / data | TanStack Router, TanStack Query, TanStack Start |
| UI | Tailwind CSS 4, Radix UI, Lucide icons |
| Charts | Recharts |
| Client exports | `xlsx`, jsPDF + jspdf-autotable |
| Session model | In-memory pipeline sessions (process lifetime) |

---

## Folder Structure

```
OmniReconcile AI/
├── backend/                    # Domain engines (importable Python package)
│   ├── upload_intelligence/    # Detect, preview, validate, session lock
│   ├── ingestion/              # POS upload service, loaders, validators
│   ├── parsers/                # Petpooja, Swiggy, Zomato parsers
│   ├── settlement/             # Settlement upload / ingest
│   ├── reconciliation/         # Reconciliation Engine V2
│   ├── platform_engines/       # Per-platform payout math
│   ├── agreement_engine/       # Commercial agreement parse / verify
│   ├── business_rules/         # Status / exception classification
│   ├── analytics/              # AnalyticsReport builder
│   ├── intelligence/           # BusinessIntelligenceReport builder
│   ├── data_quality/           # Outlet map + normalization
│   ├── common/                 # Enterprise date parser
│   └── pipeline/               # OmniPipeline orchestration + sessions
├── omni-backend/               # FastAPI entrypoint
│   ├── main.py                 # HTTP API routes
│   ├── ai_agent.py             # Dispute email generation
│   └── requirements.txt
├── frontend/                   # React SPA
│   ├── src/routes/             # App shell (upload + intelligence)
│   └── src/components/         # reconcile/ + intelligence/
├── pytest.ini
└── README.md
```

---

## Dashboard Overview

After a successful reconcile, the UI mounts `IntelligenceShell` when analytics are available.

| Tab | Purpose |
|-----|---------|
| **Executive** | Sales overview KPIs, platform/outlet scorecards, charts, leaderboard signals, BI cards when present |
| **Finance** | Gross order value, payout, commission, GST/TDS/TCS, deductions, recoverable, settlement coverage, finance charts |
| **Operations** | Order volume, outlet ranking/scorecards, platform mix charts, cancellation / pending context |
| **Reconciliation** | Filtered order table with sort, status column filter, sticky header, expandable financial breakdown |
| **Agreements** | Agreement coverage KPIs, commercial risk cards, agreement metadata and rule filters |

A global filter bar drives cross-tab selection (platform, outlet, payment status, settlement status, search, and related chips).

---

## Business Intelligence

```
Reconciled rows + financial fields
        ↓
AnalyticsEngine  →  AnalyticsReport   (ONLY KPI source)
        ↓
BusinessIntelligenceEngine  →  BusinessIntelligenceReport  (decision layer)
        ↓
React IntelligenceShell
  • Displays report fields
  • projectAnalyticsView selects platform / outlet / chart slices
  • filterDiscrepancyRows filters tables and exports
  • Does NOT recalculate commission, payout, recoverable, or coverage math
```

KPI cards expose explainability metadata (description, formula text, AnalyticsReport field paths) via dialog controls. Supporting metrics on BI cards expand to show evidence-oriented context from the BI payload.

---

## Screenshots

Screenshots will be added after the hackathon submission.

The current implementation includes:

- Executive Dashboard
- Finance Dashboard
- Operations Dashboard
- Reconciliation Workspace
- Agreement Verification


## Installation

### Prerequisites

- Python 3.10+ recommended
- Node.js 20+ and npm
- (Optional) `GOOGLE_API_KEY` or `GEMINI_API_KEY` for dispute email generation

### 1. Clone

```bash
git clone https://github.com/sourav1990sg/OmniReconcile-AI.git
cd OmniReconcile-AI
```
### 2. Backend

```bash
cd omni-backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API serves at [http://127.0.0.1:8000](http://127.0.0.1:8000). Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the app

Browse to [http://localhost:8080](http://localhost:8080). The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

---

## API Overview

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Service health and capability flags |
| `POST` | `/api/upload/analyze` | Detect / preview uploads (no commit) |
| `GET` | `/api/session/{session_id}` | Session lock, coverage, history, previews |
| `POST` | `/api/upload/pos` | Commit Petpooja POS files (locks session) |
| `POST` | `/api/upload/pos/replace` | Replace locked POS (`confirm=REPLACE`) |
| `POST` | `/api/upload/settlement` | Commit Swiggy / Zomato settlement files |
| `POST` | `/api/upload/agreement` | Upload commercial agreement document(s) |
| `GET` | `/api/agreement/{session_id}` | Agreement store snapshot |
| `PATCH` | `/api/agreement/{session_id}/{agreement_id}` | Edit / approve agreement rules |
| `POST` | `/api/reconcile/run` | Run full pipeline for a staged session |
| `POST` | `/api/reconcile` | One-shot reconcile (FormData POS + settlement + optional agreements) |
| `POST` | `/api/generate-dispute` | Generate a Gemini-assisted dispute email draft for one discrepancy row |

CORS is open for local development (`allow_origins=["*"]`). There is no authentication layer in the current API.

---

## Current Status

| Module | Capability flag | Status |
|--------|-----------------|--------|
| Pipeline / Reconciliation V2 | `pipeline: v2` | Complete |
| Upload Intelligence | `upload_intelligence: 5a` | Complete |
| Platform Financial Engines | `platform_financial: 6a` | Complete |
| Commercial Agreements | `commercial_agreement: 6b` | Complete |
| Analytics Engine | `analytics: 7a` | Complete |
| Business Intelligence Engine | `business_intelligence: 8` | Complete |
| Data Quality (outlets) | `data_quality: 9` | Complete |
| Interactive BI UI | `interactive_bi: 10a` | Complete |
| Enterprise Date Parser | `date_parser: 10a.1` | Complete |
| Dispute email assist | `/api/generate-dispute` | Complete (requires API key) |
| Auth / multi-tenant / durable DB | — | Not implemented |
| Server-side export APIs | — | Not implemented (client-side exports only) |

---

## Roadmap

Realistic next steps based on current architecture gaps:

- Persistent session / result storage (replace in-memory `_SESSIONS`)
- Authentication and role-based access for finance vs operations users
- Configurable outlet map administration UI
- Broader automated regression suite in CI
- Optional server-side scheduled export jobs
- Hardened production CORS and deployment packaging

---

## Contributing

1. Fork the repository and create a feature branch.
2. Keep financial calculation changes isolated to backend engines — do not reimplement KPIs in React.
3. Prefer extending `AnalyticsReport` / `BusinessIntelligenceReport` contracts over ad-hoc frontend math.
4. Run the API and SPA locally and verify upload → reconcile → dashboard before opening a PR.
5. Document API or schema changes in the PR description.

---

## License

This project is currently shared for educational and hackathon evaluation purposes.

A production open-source license will be added in a future release.


---

## 👨‍💻 Author

### Sourav Golui

Data Analyst | AI Automation Specialist | Enterprise Software Developer

Passionate about building enterprise applications that combine financial reconciliation, business intelligence, workflow automation and AI to solve real-world business problems.

- **GitHub:** https://github.com/sourav1990sg
- **LinkedIn:** https://www.linkedin.com/in/sourav-golui/

---

*OmniReconcile AI — upload-driven restaurant settlement reconciliation with audited analytics and interactive intelligence.*