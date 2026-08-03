"""Façade service: parse → extract → validate → store."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any, Mapping

from backend.agreement_engine.extractor import AgreementExtractor
from backend.agreement_engine.models import Agreement, AgreementStatus, AgreementStore
from backend.agreement_engine.parser import AgreementParser
from backend.agreement_engine.validator import AgreementValidator


class AgreementService:
    """Independent commercial agreement upload & configuration service."""

    def __init__(self, store: AgreementStore | None = None) -> None:
        self.store = store or AgreementStore()
        self._parser = AgreementParser()
        self._extractor = AgreementExtractor()
        self._validator = AgreementValidator()

    def ingest_file(
        self,
        filename: str,
        content: bytes,
        *,
        version: str | None = None,
        as_of: date | None = None,
    ) -> dict[str, Any]:
        parsed = self._parser.parse(filename, content)
        rules = self._extractor.extract(parsed)
        agreement = Agreement(
            version=version or str(len(self.store.agreements) + 1),
            source_filename=filename,
            source_bytes_sha1=hashlib.sha1(content).hexdigest(),
            rules=rules,
            status=AgreementStatus.PENDING_REVIEW,
            extraction_notes=list(parsed.notes or []),
        )
        if not parsed.text.strip():
            agreement.extraction_notes.append(
                "No text extracted — all terms UNKNOWN; configure manually."
            )
        findings = self._validator.validate(agreement, as_of=as_of)
        self.store.put(agreement, make_active=True)
        return {
            "message": "Success",
            "parse_method": parsed.method,
            "ocr_used": parsed.ocr_used,
            "page_count": parsed.page_count,
            "findings": findings,
            "agreement": agreement.to_dict(),
            "store": self.store.to_dict(),
        }

    def update_rules(
        self,
        agreement_id: str,
        overrides: Mapping[str, Any],
        *,
        as_of: date | None = None,
    ) -> dict[str, Any]:
        agreement = self.store.agreements.get(agreement_id)
        if agreement is None:
            raise KeyError(agreement_id)
        self._validator.apply_manual_overrides(agreement, overrides)
        findings = self._validator.validate(agreement, as_of=as_of)
        return {
            "message": "Success",
            "findings": findings,
            "agreement": agreement.to_dict(),
        }

    def approve(self, agreement_id: str, *, as_of: date | None = None) -> dict[str, Any]:
        agreement = self.store.agreements.get(agreement_id)
        if agreement is None:
            raise KeyError(agreement_id)
        agreement.approved = True
        findings = self._validator.validate(agreement, as_of=as_of)
        return {"message": "Success", "findings": findings, "agreement": agreement.to_dict()}
