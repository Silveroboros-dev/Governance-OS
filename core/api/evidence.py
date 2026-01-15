"""
Evidence API Router.

Handles evidence pack retrieval and export.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from uuid import UUID

from core.database import get_db
from core.models import EvidencePack
from core.services import EvidenceGenerator
from core.schemas.evidence import EvidencePackResponse

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{decision_id}", response_model=EvidencePackResponse)
def get_evidence_pack(
    decision_id: str,
    db: Session = Depends(get_db)
):
    """
    Get evidence pack for a decision.

    If not generated yet, generates it on demand.
    """
    try:
        dec_uuid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    # Look for existing evidence pack
    pack = (
        db.query(EvidencePack)
        .filter(EvidencePack.decision_id == dec_uuid)
        .first()
    )

    if not pack:
        # Generate on demand
        from core.models import Decision
        decision = db.query(Decision).filter(Decision.id == dec_uuid).first()

        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        generator = EvidenceGenerator(db)
        pack = generator.generate_pack(decision)

    return pack


@router.get("/{decision_id}/export")
def export_evidence_pack(
    decision_id: str,
    format: Literal["json", "html", "pdf"] = "json",
    inline: bool = False,
    db: Session = Depends(get_db)
):
    """
    Export evidence pack for external consumption.

    Args:
        decision_id: UUID of the decision
        format: Export format - json, html, or pdf
        inline: If true, display in browser; if false, trigger download

    Formats:
        - json: Raw JSON data
        - html: Standalone HTML with embedded CSS (print-ready)
        - pdf: PDF document (requires WeasyPrint)
    """
    try:
        dec_uuid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    # Get evidence pack
    pack = (
        db.query(EvidencePack)
        .filter(EvidencePack.decision_id == dec_uuid)
        .first()
    )

    if not pack:
        raise HTTPException(status_code=404, detail="Evidence pack not found")

    # Export
    generator = EvidenceGenerator(db)
    try:
        content = generator.export_pack(pack.id, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        # WeasyPrint not available for PDF (or Jinja2 issue)
        if "weasyprint" in str(e).lower():
            raise HTTPException(
                status_code=501,
                detail="PDF export unavailable. WeasyPrint not installed. Use format=html instead."
            )
        # Re-raise other import errors for debugging
        raise HTTPException(
            status_code=500,
            detail=f"Import error: {str(e)}"
        )

    # Media types by format
    media_types = {
        "json": "application/json",
        "html": "text/html; charset=utf-8",
        "pdf": "application/pdf",
    }

    # Content disposition: inline (view in browser) or attachment (download)
    disposition = "inline" if inline else "attachment"
    filename = f"evidence_pack_{decision_id[:8]}.{format}"

    return Response(
        content=content,
        media_type=media_types[format],
        headers={
            "Content-Disposition": f"{disposition}; filename={filename}"
        }
    )
