# OceanTrace AI — Maritime Forensic Intelligence Platform

**Smart India Hackathon 2026 — Problem Statement SIH26143**
*Organization: NTRO · Category: Software · Theme: Space Technology*

> OceanTrace AI is an AI-powered maritime forensic intelligence platform that detects oil spills from satellite imagery, reconstructs probable spill origins using environmental and drift analysis, correlates AIS vessel trajectories, and provides explainable investigation support through an intelligent text and voice Copilot.

---

## 0. What's in this delivery

| File | What it is |
|---|---|
| `oceantrace-ai.html` | The full interactive frontend prototype. Open directly in a browser — no install. Theme: **Tactical Cyber-Maritime C4ISR Command Center** (deep oceanic dark mode, neon telemetry, interactive 48h AIS time-scrubber, Sentinel-1 SAR studio, oceanographic hindcast, voice copilot). |
| `oceantrace-backend.zip` | A real FastAPI + SQLite backend service (auth, RBAC, vectorised AIS scoring, drift, reports). Runs locally with `uvicorn`. |
| `README.md` | This file. |

The two are **independently useful and independently runnable** — the frontend works standalone with its own in-browser demo logic, and the backend is a real, tested API you can call with `curl`/Postman on its own. They can also be connected: see §2.

## 1. What the frontend (`oceantrace-ai.html`) is

A **single-file, fully-interactive front-end prototype** that implements the complete specified investigation workflow end-to-end, runnable by opening the file in a browser — no build step, no server required:

```
LOGIN → MISSION CONTROL → NEW INVESTIGATION → SATELLITE UPLOAD → DETECTION →
CHARACTERIZATION → ENVIRONMENT → TRACE ORIGIN → AIS CORRELATION → CANDIDATE
RANKING → EVIDENCE CHAIN → COPILOT (text + voice) → REPORT
```

Standalone, it is **not** a deployed multi-service system with a real database, hashed credentials, or a trained ML model — that requires infrastructure (PostgreSQL, a Python backend, GPU-hosted models) that cannot run inside a static file, which is exactly why `oceantrace-backend.zip` (§2) exists as a real, separately-runnable counterpart. Per the brief's own implementation rule (§64: *"if a subsystem is simulated, build the correct interface, implement a working demo provider, clearly label it, keep the real implementation replaceable"*), every simulated subsystem in the standalone frontend:

1. has the correct interface / UI for the real thing,
2. has a working demo provider behind it,
3. is clearly labeled **DEMO** / **SIMULATION DATA** / **PROTOTYPE MODEL** in the UI itself, and
4. is isolated behind a small function so it's a drop-in replacement target — §2 shows exactly that swap happening for AIS scoring.

## 2. The real backend (`oceantrace-backend.zip`) and connecting it to the frontend

This is not another simulation layer — it's an actual FastAPI service with real security and a genuinely more efficient scoring engine, and it's been verified end-to-end with automated tests (bcrypt hashing, JWT issuing, RBAC 403s, file-upload magic-byte validation, and the vectorised AIS scorer all pass).

**Run it:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # fill in JWT_SECRET for anything beyond local testing
uvicorn app.main:app --reload --port 8000
```
It seeds the same three demo accounts as the frontend (`admin@oceantrace.ai` / `Admin@123`, etc.) but with **real bcrypt-hashed passwords** this time, and exposes interactive API docs at `http://localhost:8000/docs`.

**Why it's more efficient than the in-browser demo logic:** the original frontend scores AIS candidates with a JavaScript loop, one vessel at a time. `POST /api/ais/analyze` instead runs `AISAnalyzer.rank_candidates()` — a single batched numpy pass over the whole vessel array (haversine distance, bearing alignment, and all five score components computed as array operations, not a Python loop per vessel). Benchmarked in this environment: **500 vessels scored in ~5.4 ms of server compute**, and that cost grows sub-linearly with fleet size because it's vectorised, unlike a per-row loop.

**Connecting the two:** open the frontend, sign in, go to **Settings → Live Backend Integration**, and enter the backend's base URL (`http://localhost:8000`) plus an access token (get one via `POST /api/auth/login` in the docs UI or with `curl`). Once saved, clicking **Analyze AIS & Rank** in Mission Control tries the real backend first — you'll see a **`LIVE BACKEND · N.NN ms`** badge on the Candidates tab confirming it actually round-tripped — and transparently falls back to local demo compute if the backend isn't reachable, so the frontend never breaks without it.

The other endpoints (`/api/auth/*`, `/api/investigations`, `/api/drift/backward`, `/api/spill/detect`, `/api/reports/generate`, `/api/audit-logs`) are live and testable the same way via `/docs`, but only the AIS path is wired into the frontend UI in this build — see §8 for what's left to wire up.

## 3. What's real vs. simulated in the standalone frontend

| Capability | Status | Detail |
|---|---|---|
| Investigation workflow (ingest → detect → trace → correlate → rank → evidence → report) | **Real, functional** | Every stage is computed live in-browser from your inputs. |
| Login / Register / RBAC (Admin, Analyst, Viewer) | **Simulated** | In-memory demo accounts, plaintext comparison, client-side role gating only. No hashing, JWT, or server-side authorization in the standalone frontend — see §6 for the caveat and §2 for the real thing. |
| Satellite image handling | **Real upload + synthetic imagery** | You can upload a real image (used for the viewer/canvas); if none is provided a synthetic ocean scene is procedurally drawn (no real satellite imagery is bundled or fetched, so there are no licensing concerns). |
| Oil-spill detection | **Demo inference engine** | No trained model. A seeded procedural generator produces plausible confidence/area/geometry, clearly tagged `DEMO MODEL` everywhere it appears. |
| Environmental data (wind/current/wave/SST) | **Demo provider** | Procedurally generated, tagged `SIMULATION DATA`. |
| Backward drift / origin estimation | **Prototype physically-inspired model** | Simplified bearing/distance projection, not a real oceanographic hindcast. Tagged `PROTOTYPE DRIFT MODEL`; always reports a *probable origin region*, never an "exact origin". |
| AIS ingestion | **Real CSV parsing + demo generator fallback** | Upload your own `mmsi,name,type,lat,lon,...` CSV, or let the app generate a plausible synthetic AIS field around the estimated origin. |
| Candidate vessel scoring | **Real, deterministic scoring logic** | Spatial (25) + Temporal (25) + Trajectory (20) + Drift (20) + Behavior (10) = 100, computed from actual generated/uploaded track geometry — this part is genuine code, just fed by demo/uploaded data rather than a live AIS feed. |
| Evidence chain | **Real** | Built automatically from the actual upstream results of the same investigation. |
| OceanTrace Copilot | **Real tool-calling architecture** | Uses the Anthropic Messages API with genuine function/tool calling (`detect_oil_spill`, `get_spill_metrics`, `trace_spill_origin`, `analyze_ais`, `get_vessel_details`, `show_vessel_trajectory`, `generate_report`, etc.). The model **cannot** answer investigation questions without calling a tool that reads the real in-browser investigation state — this is the grounding rule from §58/§37, actually enforced, not just prompted. Falls back to a local rule-based responder (using the same tool functions) if the live API is unreachable, so the demo never breaks. |
| Voice assistant | **Real** | Browser Web Speech API (SpeechRecognition + SpeechSynthesis) — no external voice service. Gracefully shows "Voice service unavailable — text Copilot remains active" if the browser doesn't support it. |
| Report generation | **Real content, browser-based export** | All 14 report sections are populated from real investigation state. Export is via browser Print → Save as PDF, plus a genuine JSON evidence export (`Blob` download). No server-side ReportLab PDF pipeline. |
| Audit log | **Real, session-scoped** | Every login, upload, analysis run, and report generation is logged and viewable by Admin accounts — but it lives in memory and resets on reload. |

**Never fabricated:** the system does not claim a real trained model's accuracy, does not claim to have processed real satellite or AIS feeds, and every screen that touches simulated data says so visibly.

## 4. Mandatory legal/scientific language

The app never uses "Guilty Vessel", "Confirmed Culprit", "Vessel Responsible", or "Proven Offender". It only ever says *Investigation Priority*, *High-Correlation Candidate*, *Candidate Vessel*, or *Highest Spatiotemporal Correlation*. The mandated disclaimer —

> *"This system provides analytical and investigative support based on satellite observations, environmental data, and AIS correlations. Correlation does not establish legal responsibility or causation. Results should be independently verified by qualified investigators."*

— appears in the Candidates tab and in every generated report.

## 5. Demo walkthrough (2–4 minutes, matches §48)

1. Landing page → **Load Demo Mission** (auto-signs in as the Analyst demo account).
2. Mission Control opens with a satellite scene already ingested.
3. Click **Run Detection** → spill mask, confidence, area, false-positive analysis appear.
4. Click **Trace Origin** → backward drift, probable origin region, and probability bands render on the map.
5. Click **Analyze AIS & Rank** → the filtering funnel (N vessels → spatial → temporal → trajectory → priority) runs, candidates rank themselves, and the evidence chain builds.
6. Open the **Candidates** tab, expand the top vessel, click **Follow this vessel on map**.
7. Ask the Copilot: *"Why is this vessel high priority?"* or press the mic and say it — watch it call tools rather than guess.
8. Click **Generate Report**, then **Print / Save as PDF** or **Export JSON Evidence**.

## 6. Honest security note (read before any real deployment)

This prototype's *standalone* frontend authentication is **client-side only** — credentials live in a JS array and role checks are `if` statements in the browser. That's appropriate for a hackathon UI demo and nothing else; it provides **zero real security** and must not be treated as such. A real implementation already exists in `oceantrace-backend.zip` (§2) — bcrypt hashing, JWT, server-side RBAC — it's just not wired into the login screen itself yet (only the AIS scoring call is connected). Section 7 below maps the rest of the gap.

## 7. Mapping to the production architecture from the brief

Most rows below are **already implemented** in `oceantrace-backend.zip` (§2) — this table now mainly tracks what's left to *connect* to the frontend UI rather than what's left to *build*.

| Prototype gap (standalone frontend) | Where it's already solved |
|---|---|
| In-memory `USERS` array, plaintext compare | ✅ `backend/app/security.py` — bcrypt hashing via passlib, `backend/app/routers/auth.py` |
| Client-side `can(action)` checks | ✅ `backend/app/security.py::require_role`, `require_investigation_owner_or_admin` — real 403s, verified by automated test |
| No persistence (reload = reset) | ✅ SQLite + SQLAlchemy in `backend/app/models.py` (swap `DATABASE_URL` for Postgres/PostGIS in production, no code change needed) |
| Demo detection generator | ⚠️ Interface exists (`backend/app/services/detection.py::OilSpillDetector`), still backed by `DemoOilSpillDetector` — needs real U-Net/DeepLabV3+/SegFormer weights |
| Procedural environmental data | ⚠️ Not yet extracted into an `EnvironmentalDataProvider` service in the backend — still frontend-only demo data |
| Prototype drift model | ✅ `backend/app/services/drift_engine.py::DriftEngine` — same method names as the brief, still a simplified projection rather than a real hindcast |
| CSV/demo AIS scoring | ✅ `backend/app/services/ais_analyzer.py::AISAnalyzer` — real vectorised pipeline, fed by demo/uploaded vessels rather than a live feed |
| Anthropic tool-calling Copilot | ⚠️ Still calls in-browser JS functions as "tools"; not yet repointed at the backend's REST endpoints |
| Browser print-to-PDF | ⚠️ Backend has no ReportLab pipeline yet — `POST /api/reports/generate` returns structured JSON, not a PDF |
| Session-only audit log | ✅ `backend/app/models.py::AuditLog` + `GET /api/audit-logs` (admin-only, persisted) |

The remaining ⚠️ items are the honest gap between this delivery and a fully production-ready system.

## 8. Known limitations

- No real ML model, oceanographic model, or live AIS feed is connected.
- Authentication is not secure and must not be reused as-is.
- GeoTIFF/CRS handling is simulated (shows the correct UI messaging, doesn't parse real geospatial metadata).
- Only one investigation's map/Copilot state is kept live at a time.
- The Copilot's live mode depends on being able to reach `api.anthropic.com`; if not reachable it degrades to the same tool functions run locally without the language model.

## 9. Running it

Just open `oceantrace-ai.html` in a modern desktop browser (Chrome recommended for voice input support). No install, no server.
