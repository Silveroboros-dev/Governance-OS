"""
Evidence Renderer Service.

Renders evidence packs to HTML and PDF formats for audit consumption.
"""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.models import EvidencePack


# Default templates directory
DEFAULT_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class EvidenceRenderer:
    """
    Render evidence packs to HTML and PDF formats.

    HTML is the primary format - standalone with embedded CSS.
    PDF uses WeasyPrint (optional dependency).
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the renderer.

        Args:
            templates_dir: Path to templates directory (defaults to core/templates)
        """
        self.templates_dir = templates_dir or DEFAULT_TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"])
        )

    def render_html(self, evidence_pack: EvidencePack) -> str:
        """
        Render evidence pack as standalone HTML.

        Args:
            evidence_pack: EvidencePack model instance

        Returns:
            HTML string with embedded CSS
        """
        template = self.env.get_template("evidence_pack.html")
        context = self._prepare_context(evidence_pack)
        return template.render(**context)

    def render_pdf(self, evidence_pack: EvidencePack) -> bytes:
        """
        Render evidence pack as PDF.

        Requires WeasyPrint to be installed.

        Args:
            evidence_pack: EvidencePack model instance

        Returns:
            PDF bytes

        Raises:
            ImportError: If WeasyPrint is not installed
        """
        import os

        # Set SOURCE_DATE_EPOCH for deterministic PDF metadata
        original_epoch = os.environ.get("SOURCE_DATE_EPOCH")
        os.environ["SOURCE_DATE_EPOCH"] = "0"

        try:
            from weasyprint import HTML

            html_content = self.render_html(evidence_pack)
            return HTML(string=html_content).write_pdf()
        finally:
            if original_epoch is not None:
                os.environ["SOURCE_DATE_EPOCH"] = original_epoch
            elif "SOURCE_DATE_EPOCH" in os.environ:
                del os.environ["SOURCE_DATE_EPOCH"]

    def _prepare_context(self, pack: EvidencePack) -> dict:
        """
        Prepare template context from evidence pack.

        Sorts lists deterministically and resolves references.

        Args:
            pack: EvidencePack model instance

        Returns:
            Dictionary for template rendering
        """
        evidence = pack.evidence

        # Sort signals by observed_at for deterministic ordering
        signals = sorted(
            evidence.get("signals", []),
            key=lambda s: s.get("observed_at", "")
        )

        # Sort audit trail by occurred_at
        audit_trail = sorted(
            evidence.get("audit_trail", []),
            key=lambda e: e.get("occurred_at", "")
        )

        # Resolve chosen option to get label
        chosen_option = self._resolve_chosen_option(evidence)

        return {
            "pack_id": str(pack.id),
            "content_hash": pack.content_hash,
            "generated_at": pack.generated_at.isoformat() if pack.generated_at else "",
            "decision": evidence.get("decision", {}),
            "exception": evidence.get("exception", {}),
            "evaluation": evidence.get("evaluation", {}),
            "policy": evidence.get("policy", {}),
            "signals": signals,
            "audit_trail": audit_trail,
            "chosen_option": chosen_option,
            "metadata": evidence.get("metadata", {}),
        }

    def _resolve_chosen_option(self, evidence: dict) -> dict:
        """
        Resolve chosen_option_id to full option details.

        Args:
            evidence: Evidence dictionary

        Returns:
            Option dictionary with id, label, description
        """
        decision = evidence.get("decision", {})
        exception = evidence.get("exception", {})
        chosen_id = decision.get("chosen_option_id")

        if not chosen_id:
            return {"id": "", "label": "Unknown", "description": ""}

        for option in exception.get("options", []):
            if option.get("id") == chosen_id:
                return option

        # Fallback if option not found
        return {"id": chosen_id, "label": chosen_id, "description": ""}
