"""
Evidence API Router.

Handles evidence pack retrieval and export.
"""

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
    format: str = "json",
    db: Session = Depends(get_db)
):
    """
    Export evidence pack for external consumption.

    Formats: json (Sprint 1), pdf (Sprint 2+)
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

    # Return as downloadable file
    media_type = "application/json" if format == "json" else "application/octet-stream"
    filename = f"evidence_pack_{decision_id}.{format}"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
