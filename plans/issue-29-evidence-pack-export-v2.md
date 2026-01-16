# feat: Evidence Pack Export v2 (Print-Ready HTML/PDF)

**Issue:** #29
**Type:** Enhancement
**Priority:** P1
**Pack:** Backend + UI

## Overview

Implement CFO/auditor-readable export formats for evidence packs. Currently, evidence packs can only be exported as JSON, requiring technical tools to read. This feature adds HTML and PDF export formats that are immediately readable without any tooling, suitable for board presentations, audit reviews, and compliance documentation.

## Problem Statement / Motivation

**Current State:**
- Evidence packs export only as JSON via `GET /evidence/{decision_id}/export?format=json`
- JSON requires technical knowledge or tools to read
- CFOs, auditors, and compliance officers cannot easily consume evidence packs
- No print-friendly output for physical documentation needs

**User Impact:**
- CFOs cannot quickly review governance decisions for board meetings
- External auditors require internal staff to interpret JSON exports
- Compliance teams cannot produce audit-ready documentation
- Legal discovery requests require manual formatting of evidence

**Business Value:**
- Enables self-service audit documentation
- Reduces time spent formatting evidence for stakeholders
- Meets PCAOB AS 1215 documentation requirements (effective Dec 2025)
- Supports 7-year retention requirements with readable archives

## Proposed Solution

Add HTML and PDF export formats using Jinja2 templates and WeasyPrint:

1. **HTML Export** (Primary) - Standalone HTML with embedded CSS, viewable in any browser
2. **PDF Export** (Optional) - Print-ready PDF via WeasyPrint, page-numbered with headers/footers
3. **Deterministic Output** - Same evidence pack always produces identical HTML/PDF

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer                                │
│  GET /evidence/{decision_id}/export?format=html|pdf|json    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 EvidenceGenerator                            │
│  export_pack(id, format) → delegates to EvidenceRenderer    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 EvidenceRenderer (NEW)                       │
│  render_html(pack) → Jinja2 template → HTML string          │
│  render_pdf(pack)  → HTML → WeasyPrint → PDF bytes          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Templates + Stylesheets                         │
│  core/templates/evidence_pack.html                          │
│  core/templates/styles/print.css                            │
└─────────────────────────────────────────────────────────────┘
```

## Technical Considerations

### Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Jinja2 | Template rendering | Already included via FastAPI |
| WeasyPrint | HTML→PDF conversion | Optional; requires system libs (Pango, Cairo) |
| markupsafe | XSS prevention | Already included via Jinja2 |

### Determinism Requirements

Evidence packs must produce **identical output** for identical inputs:

1. **Sorting:** All lists sorted deterministically (signals by `observed_at`, audit trail by `occurred_at`)
2. **Timestamps:** ISO 8601 format with timezone (`2026-01-15T14:30:00Z`)
3. **PDF Metadata:** Use `SOURCE_DATE_EPOCH=0` for reproducible PDF timestamps
4. **Content Hash:** Include in footer for integrity verification

### Security Considerations

1. **XSS Prevention:** Jinja2 autoescape enabled; user content (rationale, assumptions) auto-escaped
2. **CSP Header:** Inline HTML includes restrictive Content-Security-Policy meta tag
3. **No Scripts:** Export contains no JavaScript; pure HTML+CSS
4. **Auth Required:** Export endpoint requires same auth as evidence pack viewing

### Performance Considerations

- **Caching:** Consider caching rendered HTML by `content_hash` (future enhancement)
- **Timeout:** Large evidence packs (100+ signals) may need async generation
- **PDF Fallback:** If WeasyPrint unavailable, return 501 with HTML alternative suggestion

## Acceptance Criteria

### Functional Requirements

- [ ] `GET /evidence/{id}/export?format=html` returns standalone HTML document
- [ ] `GET /evidence/{id}/export?format=pdf` returns PDF document (if WeasyPrint available)
- [ ] HTML is readable without external CSS/JS (all styles embedded)
- [ ] PDF includes page numbers, headers, footers
- [ ] Export includes all required content:
  - [ ] Policy version (name, version number, valid_from/to)
  - [ ] Signals summary (type, source, reliability, timestamp, key payload fields)
  - [ ] Decision rationale and assumptions
  - [ ] All timestamps in human-readable format
  - [ ] Content hash for integrity verification
- [ ] Deterministic ordering: signals by `observed_at`, audit trail by `occurred_at`
- [ ] `?inline=true` displays in browser instead of downloading

### Non-Functional Requirements

- [ ] Same evidence pack produces byte-identical HTML on repeated exports
- [ ] PDF generation completes within 10 seconds for typical packs
- [ ] HTML size under 500KB for typical evidence packs
- [ ] Accessible: semantic HTML, proper heading hierarchy, table headers

### Quality Gates

- [ ] Unit tests for template rendering with various data states
- [ ] Determinism test: export twice, compare output hashes
- [ ] XSS test: special characters in rationale properly escaped
- [ ] Null field handling: graceful display when optional fields are null
- [ ] API tests for correct Content-Type and Content-Disposition headers

## Implementation Plan

### Phase 1: HTML Export (Core Deliverable)

**Files to create:**

| File | Purpose |
|------|---------|
| `core/templates/evidence_pack.html` | Jinja2 template with embedded print CSS |
| `core/templates/styles/evidence_pack.css` | Extracted styles (imported into template) |
| `core/services/evidence_renderer.py` | EvidenceRenderer class |
| `tests/core/test_evidence_export.py` | Export tests |

**Files to modify:**

| File | Changes |
|------|---------|
| `core/services/evidence_generator.py:197-230` | Add html/pdf format handling in `export_pack()` |
| `core/api/evidence.py:55-98` | Add format enum, inline param, update media types |
| `core/services/__init__.py` | Export EvidenceRenderer |

#### 1.1 Create EvidenceRenderer Service

```python
# core/services/evidence_renderer.py

class EvidenceRenderer:
    """Render evidence packs to HTML and PDF formats."""

    def __init__(self, templates_dir: Path = None):
        self.env = Environment(
            loader=FileSystemLoader(templates_dir or DEFAULT_TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def render_html(self, evidence_pack: EvidencePack) -> str:
        """Render evidence pack as standalone HTML."""
        template = self.env.get_template("evidence_pack.html")
        context = self._prepare_context(evidence_pack)
        return template.render(**context)

    def render_pdf(self, evidence_pack: EvidencePack) -> bytes:
        """Render evidence pack as PDF using WeasyPrint."""
        html_content = self.render_html(evidence_pack)
        return HTML(string=html_content).write_pdf()

    def _prepare_context(self, pack: EvidencePack) -> dict:
        """Prepare template context with resolved references."""
        evidence = pack.evidence
        return {
            "pack_id": str(pack.id),
            "content_hash": pack.content_hash,
            "generated_at": pack.generated_at.isoformat(),
            "decision": evidence["decision"],
            "exception": evidence["exception"],
            "evaluation": evidence["evaluation"],
            "policy": evidence["policy"],
            "signals": sorted(evidence["signals"], key=lambda s: s["observed_at"]),
            "audit_trail": sorted(evidence["audit_trail"], key=lambda e: e["occurred_at"]),
            "chosen_option": self._resolve_chosen_option(evidence),
        }

    def _resolve_chosen_option(self, evidence: dict) -> dict:
        """Resolve chosen_option_id to full option details."""
        chosen_id = evidence["decision"]["chosen_option_id"]
        for option in evidence["exception"]["options"]:
            if option["id"] == chosen_id:
                return option
        return {"id": chosen_id, "label": chosen_id, "description": ""}
```

#### 1.2 Create HTML Template

```html
<!-- core/templates/evidence_pack.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
    <title>Evidence Pack - {{ pack_id[:8] }}</title>
    <style>
        /* Print-optimized CSS embedded here */
        @page {
            size: A4;
            margin: 20mm 15mm 25mm 15mm;
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
            }
        }
        /* ... full stylesheet ... */
    </style>
</head>
<body>
    <header class="pack-header">
        <h1>Governance OS - Evidence Pack</h1>
        <dl class="metadata">
            <dt>Pack ID</dt><dd class="pack-id">{{ pack_id }}</dd>
            <dt>Generated</dt><dd class="timestamp">{{ generated_at }}</dd>
            <dt>Content Hash</dt><dd><code>{{ content_hash }}</code></dd>
        </dl>
    </header>

    <section id="summary">
        <h2>Executive Summary</h2>
        <p><strong>Exception:</strong> {{ exception.title }}</p>
        <p><strong>Severity:</strong> {{ exception.severity }}</p>
        <p><strong>Decision:</strong> {{ chosen_option.label }}</p>
        <p><strong>Decided By:</strong> {{ decision.decided_by }}</p>
        <p><strong>Decided At:</strong> {{ decision.decided_at }}</p>
    </section>

    <section id="policy">
        <h2>Policy Applied</h2>
        <table>
            <tr><th>Name</th><td>{{ policy.name }}</td></tr>
            <tr><th>Version</th><td>{{ policy.version.version_number }}</td></tr>
            <tr><th>Valid From</th><td>{{ policy.version.valid_from }}</td></tr>
            {% if policy.version.valid_to %}
            <tr><th>Valid To</th><td>{{ policy.version.valid_to }}</td></tr>
            {% endif %}
        </table>
    </section>

    <section id="signals">
        <h2>Contributing Signals ({{ signals|length }})</h2>
        <table>
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Source</th>
                    <th>Reliability</th>
                    <th>Observed At</th>
                </tr>
            </thead>
            <tbody>
                {% for signal in signals %}
                <tr>
                    <td>{{ signal.signal_type }}</td>
                    <td>{{ signal.source }}</td>
                    <td>{{ signal.reliability }}</td>
                    <td>{{ signal.observed_at }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </section>

    <section id="decision">
        <h2>Decision Record</h2>
        <h3>Options Presented</h3>
        <ol>
            {% for option in exception.options %}
            <li class="{% if option.id == decision.chosen_option_id %}chosen{% endif %}">
                <strong>{{ option.label }}</strong>
                {% if option.id == decision.chosen_option_id %}<span class="badge">CHOSEN</span>{% endif %}
                <p>{{ option.description }}</p>
            </li>
            {% endfor %}
        </ol>

        <h3>Rationale</h3>
        <blockquote>{{ decision.rationale or "No rationale provided" }}</blockquote>

        {% if decision.assumptions %}
        <h3>Assumptions</h3>
        <p>{{ decision.assumptions }}</p>
        {% endif %}
    </section>

    <section id="audit-trail" class="page-break">
        <h2>Audit Trail</h2>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Event</th>
                    <th>Actor</th>
                </tr>
            </thead>
            <tbody>
                {% for event in audit_trail %}
                <tr>
                    <td>{{ event.occurred_at }}</td>
                    <td>{{ event.event_type }}</td>
                    <td>{{ event.actor }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </section>

    <footer>
        <p><strong>Integrity Verification:</strong> SHA-256 <code>{{ content_hash }}</code></p>
        <p>This document is deterministically generated. Same inputs produce identical output.</p>
    </footer>
</body>
</html>
```

#### 1.3 Update API Endpoint

```python
# core/api/evidence.py - modifications

from typing import Literal

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
        format: Export format (json, html, pdf)
        inline: If true, display in browser; if false, trigger download
    """
    # ... existing pack retrieval ...

    generator = EvidenceGenerator(db)
    try:
        content = generator.export_pack(pack.id, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError:
        # WeasyPrint not available
        raise HTTPException(
            status_code=501,
            detail="PDF export unavailable. Use format=html instead."
        )

    # Media types and disposition
    media_types = {
        "json": "application/json",
        "html": "text/html; charset=utf-8",
        "pdf": "application/pdf",
    }

    disposition = "inline" if inline else "attachment"
    filename = f"evidence_pack_{decision_id[:8]}.{format}"

    return Response(
        content=content,
        media_type=media_types[format],
        headers={
            "Content-Disposition": f"{disposition}; filename={filename}"
        }
    )
```

### Phase 2: PDF Export (Enhancement)

Add WeasyPrint integration for PDF generation:

```python
# In evidence_renderer.py

def render_pdf(self, evidence_pack: EvidencePack) -> bytes:
    """Render evidence pack as PDF."""
    import os

    # Set SOURCE_DATE_EPOCH for deterministic PDF metadata
    original_epoch = os.environ.get('SOURCE_DATE_EPOCH')
    os.environ['SOURCE_DATE_EPOCH'] = '0'

    try:
        from weasyprint import HTML, CSS

        html_content = self.render_html(evidence_pack)
        return HTML(string=html_content).write_pdf()
    finally:
        if original_epoch is not None:
            os.environ['SOURCE_DATE_EPOCH'] = original_epoch
        elif 'SOURCE_DATE_EPOCH' in os.environ:
            del os.environ['SOURCE_DATE_EPOCH']
```

### Phase 3: UI Integration

Update frontend to support format selection:

```typescript
// ui/app/decisions/[id]/page.tsx - modifications

const [exportFormat, setExportFormat] = useState<'html' | 'pdf' | 'json'>('html')

const handleExport = async () => {
  const blob = await api.evidence.export(params.id, exportFormat)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `evidence_pack_${params.id.slice(0, 8)}.${exportFormat}`
  a.click()
  URL.revokeObjectURL(url)
}

// Add format selector dropdown next to export button
<Select value={exportFormat} onValueChange={setExportFormat}>
  <SelectItem value="html">HTML (Recommended)</SelectItem>
  <SelectItem value="pdf">PDF</SelectItem>
  <SelectItem value="json">JSON</SelectItem>
</Select>
```

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Export completion rate | >99% | API success rate for export endpoint |
| Export time (HTML) | <2s | P95 response time |
| Export time (PDF) | <10s | P95 response time |
| Determinism | 100% | Same pack → same hash on re-export |

## Dependencies & Risks

### Dependencies

- **WeasyPrint system libraries** (for PDF only): Pango, Cairo, GDK-PixBuf
  - Mitigation: PDF is optional; HTML export works without these
  - Docker image may need additional packages

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| WeasyPrint not installed | PDF unavailable | Return 501 with HTML alternative |
| Large evidence packs | Slow generation | Add pagination for signals >50 |
| XSS in user content | Security vulnerability | Jinja2 autoescape; verify in tests |
| Non-deterministic PDF | Audit integrity | SOURCE_DATE_EPOCH + determinism tests |

## Testing Strategy

### Unit Tests

```python
# tests/core/test_evidence_export.py

class TestEvidenceRenderer:
    def test_render_html_includes_all_sections(self, sample_evidence_pack):
        """HTML contains all required sections."""
        renderer = EvidenceRenderer()
        html = renderer.render_html(sample_evidence_pack)

        assert "Executive Summary" in html
        assert "Policy Applied" in html
        assert "Contributing Signals" in html
        assert "Decision Record" in html
        assert "Audit Trail" in html
        assert sample_evidence_pack.content_hash in html

    def test_render_html_deterministic(self, sample_evidence_pack):
        """Same pack produces identical HTML."""
        renderer = EvidenceRenderer()
        html1 = renderer.render_html(sample_evidence_pack)
        html2 = renderer.render_html(sample_evidence_pack)
        assert html1 == html2

    def test_render_html_escapes_xss(self, db_session):
        """User content is properly escaped."""
        # Create pack with XSS attempt in rationale
        pack = create_pack_with_rationale(db_session, "<script>alert('xss')</script>")
        renderer = EvidenceRenderer()
        html = renderer.render_html(pack)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_html_handles_null_fields(self, sample_evidence_pack):
        """Template handles null optional fields gracefully."""
        sample_evidence_pack.evidence["decision"]["assumptions"] = None
        renderer = EvidenceRenderer()
        html = renderer.render_html(sample_evidence_pack)

        assert "Assumptions" not in html  # Section hidden when null

    def test_signals_sorted_by_observed_at(self, sample_evidence_pack):
        """Signals appear in chronological order."""
        renderer = EvidenceRenderer()
        html = renderer.render_html(sample_evidence_pack)

        # Verify order in rendered HTML
        signal_positions = [html.find(s["signal_type"]) for s in
                          sorted(sample_evidence_pack.evidence["signals"],
                                key=lambda x: x["observed_at"])]
        assert signal_positions == sorted(signal_positions)


class TestExportAPI:
    def test_export_html_returns_correct_content_type(self, client, sample_decision):
        response = client.get(f"/evidence/{sample_decision.id}/export?format=html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_export_inline_sets_correct_disposition(self, client, sample_decision):
        response = client.get(f"/evidence/{sample_decision.id}/export?format=html&inline=true")
        assert "inline" in response.headers["content-disposition"]

    def test_export_download_sets_attachment_disposition(self, client, sample_decision):
        response = client.get(f"/evidence/{sample_decision.id}/export?format=html")
        assert "attachment" in response.headers["content-disposition"]

    def test_export_invalid_format_returns_422(self, client, sample_decision):
        response = client.get(f"/evidence/{sample_decision.id}/export?format=xlsx")
        assert response.status_code == 422
```

## File Summary

| File | Action | Lines (est.) |
|------|--------|--------------|
| `core/templates/evidence_pack.html` | Create | ~200 |
| `core/services/evidence_renderer.py` | Create | ~100 |
| `core/services/evidence_generator.py` | Modify | +30 |
| `core/api/evidence.py` | Modify | +20 |
| `core/services/__init__.py` | Modify | +1 |
| `tests/core/test_evidence_export.py` | Create | ~150 |
| `ui/app/decisions/[id]/page.tsx` | Modify | +20 |
| `ui/lib/api.ts` | Modify | +5 |

**Total new code:** ~500 lines

## References

### Internal References
- Evidence generator: `core/services/evidence_generator.py:197-230`
- Current export API: `core/api/evidence.py:55-98`
- Evidence pack model: `core/models/evidence.py:1-54`
- Content hashing: `core/domain/fingerprinting.py:1-151`
- UI export handler: `ui/app/decisions/[id]/page.tsx:68-81`

### External References
- [WeasyPrint Documentation](https://doc.courtbouillon.org/weasyprint/stable/)
- [Jinja2 Templates](https://jinja.palletsprojects.com/en/stable/)
- [CSS Paged Media](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Paged_media)
- [PCAOB AS 1215 Audit Documentation](https://pcaobus.org/oversight/standards/auditing-standards/details/as-1215--audit-documentation-(effective-on-12-15-2025))
- [Reproducible Builds - SOURCE_DATE_EPOCH](https://reproducible-builds.org/docs/timestamps/)

### Related Work
- Issue #29: This issue
- Existing plan draft: `plans/issue-29-evidence-export-v2.md`
