"""
OmniReconcile AI FastAPI entrypoint.

Integrates Sprint pipeline (POS → Settlement → Reconcile → Business Rules)
and Sprint 5A Upload Intelligence (analyze / session lock / replace).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ai_agent import generate_dispute_email

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pipeline import OmniPipeline, get_or_create_session  # noqa: E402
from backend.pipeline.orchestrator import get_agreement_service  # noqa: E402
from backend.upload_intelligence import UploadIntelligenceService  # noqa: E402
from backend.upload_intelligence.models import DatasetRole  # noqa: E402
from backend.upload_intelligence.session_manager import SessionLockedError  # noqa: E402

app = FastAPI(title="OmniReconcile AI", version="2.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_AS_OF = date(2026, 8, 1)
_intel = UploadIntelligenceService(reference_date=_AS_OF)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "pipeline": "v2",
        "upload_intelligence": "5a",
        "platform_financial": "6a",
        "commercial_agreement": "6b",
        "analytics": "7a",
        "business_intelligence": "8",
        "data_quality": "9",
        "interactive_bi": "10a",
        "date_parser": "10a.1",
    }


async def _read_uploads_async(files: list[UploadFile], *, allow_empty: bool = False) -> list[tuple[str, bytes]]:
    out: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        name = f.filename or "unknown"
        if not content and not allow_empty:
            raise HTTPException(status_code=400, detail=f"File '{name}' is empty.")
        out.append((name, content))
    return out


@app.post("/api/upload/analyze")
async def upload_analyze(
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    """
    Sprint 5A — column-based detection + preview (no commit).

    Never relies on filenames. UNKNOWN_FILE files are not parsed for ingest.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")
    data = await _read_uploads_async(files, allow_empty=True)
    try:
        result = _intel.analyze_dict(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"message": "Success", **result}


@app.get("/api/session/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """Session snapshot: lock, coverage, history, previews."""
    try:
        session = _intel.sessions.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown session_id '{session_id}'") from exc
    return {"message": "Success", **_intel.sessions.snapshot(session)}


@app.post("/api/upload/pos")
async def upload_pos(
    pos_files: list[UploadFile] = File(...),
    session_id: str | None = Form(None),
    uploaded_by: str | None = Form(None),
) -> dict[str, Any]:
    """Step 1 — intelligence-gated Petpooja POS upload (locks session)."""
    if not pos_files:
        raise HTTPException(status_code=400, detail="At least one POS file is required.")
    data = await _read_uploads_async(pos_files, allow_empty=True)
    session = get_or_create_session(session_id)
    _intel.sessions.ensure_extended(session)

    try:
        _intel.sessions.assert_pos_writable(session, replace=False)
    except SessionLockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    accepted, previews, findings = _intel.partition_for_commit(data, role=DatasetRole.POS)
    if not accepted:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid Petpooja POS files to commit",
                "findings": [f.to_dict() for f in findings],
                "previews": [p.to_dict() for p in _intel.analyze(data).previews],
            },
        )

    try:
        summary = OmniPipeline(as_of=_AS_OF).ingest_pos(accepted)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not summary.get("total_orders"):
        raise HTTPException(
            status_code=400,
            detail="POS ingest produced 0 orders after intelligence filtering.",
        )

    _intel.sessions.commit_pos(
        session,
        files=accepted,
        summary=summary,
        previews=previews,
        uploaded_by=uploaded_by or "operator",
        replace=False,
    )
    return {
        "message": "Success",
        "session_id": session.session_id,
        "pos_summary": summary,
        "pos_locked": True,
        "previews": [p.to_dict() for p in previews],
        "findings": [f.to_dict() for f in findings],
        "coverage": session.coverage,
        "upload_history": session.upload_history,
    }


@app.post("/api/upload/pos/replace")
async def upload_pos_replace(
    pos_files: list[UploadFile] = File(...),
    session_id: str | None = Form(None),
    uploaded_by: str | None = Form(None),
    confirm: str = Form(...),
) -> dict[str, Any]:
    """
    Explicit POS replace — requires confirm=REPLACE.

    Old session is removed; a new session is created.
    """
    if confirm.strip().upper() != "REPLACE":
        raise HTTPException(
            status_code=400,
            detail="Confirmation required: form field confirm=REPLACE",
        )
    if not pos_files:
        raise HTTPException(status_code=400, detail="At least one POS file is required.")

    data = await _read_uploads_async(pos_files, allow_empty=True)
    session = _intel.sessions.replace_pos(session_id)

    accepted, previews, findings = _intel.partition_for_commit(data, role=DatasetRole.POS)
    if not accepted:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid Petpooja POS files to commit",
                "findings": [f.to_dict() for f in findings],
            },
        )

    try:
        summary = OmniPipeline(as_of=_AS_OF).ingest_pos(accepted)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not summary.get("total_orders"):
        raise HTTPException(status_code=400, detail="POS ingest produced 0 orders.")

    _intel.sessions.commit_pos(
        session,
        files=accepted,
        summary=summary,
        previews=previews,
        uploaded_by=uploaded_by or "operator",
        replace=True,
    )
    return {
        "message": "Success",
        "session_id": session.session_id,
        "replaced_session_id": session_id,
        "pos_summary": summary,
        "pos_locked": True,
        "previews": [p.to_dict() for p in previews],
        "findings": [f.to_dict() for f in findings],
        "coverage": session.coverage,
        "upload_history": session.upload_history,
    }


@app.post("/api/upload/settlement")
async def upload_settlement(
    agg_files: list[UploadFile] = File(...),
    session_id: str | None = Form(None),
    uploaded_by: str | None = Form(None),
) -> dict[str, Any]:
    """Step 2 — intelligence-gated settlement upload (never overwrites POS)."""
    if not agg_files:
        raise HTTPException(status_code=400, detail="At least one settlement file is required.")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for settlement upload.")

    data = await _read_uploads_async(agg_files, allow_empty=True)
    try:
        session = _intel.sessions.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown session_id '{session_id}'") from exc

    _intel.sessions.ensure_extended(session)
    if not session.pos_files or not session.pos_locked:
        raise HTTPException(status_code=400, detail="Upload and lock POS before settlement.")

    # Snapshot POS before settlement — must remain identical after commit
    pos_snapshot = list(session.pos_files)
    pos_summary_snapshot = dict(session.pos_summary or {})

    accepted, previews, findings = _intel.partition_for_commit(data, role=DatasetRole.SETTLEMENT)
    if not accepted:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid settlement files to commit",
                "findings": [f.to_dict() for f in findings],
                "previews": [p.to_dict() for p in _intel.analyze(data).previews],
            },
        )

    try:
        summary = OmniPipeline(as_of=_AS_OF).ingest_settlement(accepted)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not summary.get("total_orders"):
        raise HTTPException(
            status_code=400,
            detail="Settlement ingest produced 0 orders after intelligence filtering.",
        )

    _intel.sessions.commit_settlement(
        session,
        files=accepted,
        summary=summary,
        previews=previews,
        uploaded_by=uploaded_by or "operator",
    )

    # Hard guarantee: POS untouched
    if session.pos_files != pos_snapshot or session.pos_summary != pos_summary_snapshot:
        raise HTTPException(status_code=500, detail="Invariant violated: settlement overwrote POS.")

    return {
        "message": "Success",
        "session_id": session.session_id,
        "settlement_summary": summary,
        "pos_locked": True,
        "pos_summary": session.pos_summary,
        "previews": [p.to_dict() for p in previews],
        "findings": [f.to_dict() for f in findings],
        "coverage": session.coverage,
        "upload_history": session.upload_history,
    }


@app.post("/api/upload/agreement")
async def upload_agreement(
    agreement_files: list[UploadFile] = File(...),
    session_id: str | None = Form(None),
) -> dict[str, Any]:
    """
    Sprint 6B — optional commercial agreement upload (PDF/DOCX/TXT).

    Independent of Upload Intelligence. Does not affect POS/settlement.
    """
    if not agreement_files:
        raise HTTPException(status_code=400, detail="At least one agreement file is required.")
    session = get_or_create_session(session_id)
    data = await _read_uploads_async(agreement_files, allow_empty=False)
    service = get_agreement_service(session)
    results = []
    for name, content in data:
        results.append(service.ingest_file(name, content, as_of=_AS_OF))
    session.agreement_summary = session.agreement_store.to_dict()
    return {
        "message": "Success",
        "session_id": session.session_id,
        "ingested": results,
        "agreement_summary": session.agreement_summary,
    }


@app.get("/api/agreement/{session_id}")
async def get_agreement(session_id: str) -> dict[str, Any]:
    session = _SESSIONS_GET(session_id)
    return {"message": "Success", "agreement_summary": session.agreement_store.to_dict()}


@app.patch("/api/agreement/{session_id}/{agreement_id}")
async def patch_agreement(
    session_id: str,
    agreement_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Edit / approve commercial rules (manual UNKNOWN fill-in)."""
    session = _SESSIONS_GET(session_id)
    service = get_agreement_service(session)
    try:
        if payload.get("approve") is True:
            result = service.approve(agreement_id, as_of=_AS_OF)
        else:
            overrides = payload.get("rules") or payload
            result = service.update_rules(agreement_id, overrides, as_of=_AS_OF)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown agreement_id '{agreement_id}'") from exc
    session.agreement_summary = session.agreement_store.to_dict()
    result["agreement_summary"] = session.agreement_summary
    result["session_id"] = session.session_id
    return result


@app.post("/api/reconcile/run")
async def reconcile_run(session_id: str = Form(...)) -> dict[str, Any]:
    """Step 3 — run full pipeline for a staged session."""
    session = _SESSIONS_GET(session_id)
    if not session.pos_files:
        raise HTTPException(status_code=400, detail="Upload POS files first.")
    if not session.settlement_files:
        raise HTTPException(status_code=400, detail="Upload settlement files first.")
    try:
        result = OmniPipeline(as_of=_AS_OF).run(
            session.pos_files,
            session.settlement_files,
            agreement_store=session.agreement_store,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    result["coverage"] = getattr(session, "coverage", None)
    result["session_id"] = session.session_id
    result["agreement_summary"] = session.agreement_store.to_dict()
    return result


def _SESSIONS_GET(session_id: str):
    from backend.pipeline.orchestrator import _SESSIONS

    if session_id not in _SESSIONS:
        raise HTTPException(status_code=404, detail=f"Unknown session_id '{session_id}'")
    return _SESSIONS[session_id]


@app.post("/api/reconcile")
async def reconcile(
    pos_files: list[UploadFile] = File(...),
    agg_files: list[UploadFile] = File(...),
    agreement_files: list[UploadFile] = File(default=[]),
    session_id: str | None = Form(None),
) -> dict[str, Any]:
    """
    One-shot reconcile (backward compatible FormData keys).

    Intelligence filters each side before the existing pipeline runs.
    Optional agreement_files enable Sprint 6B commercial verification.
    """
    if not pos_files:
        raise HTTPException(status_code=400, detail="At least one POS file is required.")
    if not agg_files:
        raise HTTPException(status_code=400, detail="At least one aggregator file is required.")

    pos_raw = await _read_uploads_async(pos_files, allow_empty=True)
    agg_raw = await _read_uploads_async(agg_files, allow_empty=True)

    pos_data, pos_previews, pos_findings = _intel.partition_for_commit(pos_raw, role=DatasetRole.POS)
    agg_data, agg_previews, agg_findings = _intel.partition_for_commit(
        agg_raw, role=DatasetRole.SETTLEMENT
    )
    if not pos_data:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid POS files after intelligence filtering",
                "findings": [f.to_dict() for f in pos_findings],
            },
        )
    if not agg_data:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid settlement files after intelligence filtering",
                "findings": [f.to_dict() for f in agg_findings],
            },
        )

    agreement_store = None
    if session_id:
        try:
            agreement_store = _SESSIONS_GET(session_id).agreement_store
        except HTTPException:
            agreement_store = get_or_create_session(session_id).agreement_store
    if agreement_files:
        session = get_or_create_session(session_id)
        service = get_agreement_service(session)
        for name, content in await _read_uploads_async(agreement_files, allow_empty=False):
            service.ingest_file(name, content, as_of=_AS_OF)
        agreement_store = session.agreement_store

    try:
        result = OmniPipeline(as_of=_AS_OF).run(
            pos_data,
            agg_data,
            agreement_store=agreement_store,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    result["previews"] = {
        "pos": [p.to_dict() for p in pos_previews],
        "settlement": [p.to_dict() for p in agg_previews],
    }
    return result


@app.post("/api/generate-dispute")
async def create_dispute(payload: dict[str, Any]) -> dict[str, str]:
    """Generate a drafted dispute email for a single flagged order row."""
    if not payload:
        raise HTTPException(status_code=400, detail="Request body must be a flagged order row.")
    try:
        email = generate_dispute_email(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"email": email}
