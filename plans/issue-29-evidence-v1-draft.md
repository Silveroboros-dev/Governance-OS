# Issue #29: Evidence Pack Export v2 (Print-Ready HTML/PDF)

## Goal
CFO/auditor readable output - one-click export without external tooling.

## Current State
- `EvidenceGenerator.export_pack()` only supports JSON format
- API endpoint `GET /evidence/{decision_id}/export?format=json` exists
- Evidence structure includes: decision, exception, evaluation, policy, signals, audit_trail

## Acceptance Criteria
- [ ] One-click export readable without tooling
- [ ] Includes: policy version, signals summary, decision rationale, timestamps
- [ ] Deterministic ordering

---

## Implementation Plan

### Phase 1: HTML Export (Primary Deliverable)

#### 1.1 Create HTML Template System
**File:** `core/templates/evidence_pack.html`

- Jinja2 template for audit-grade HTML output
- Professional styling (print-optimized CSS)
- Sections:
  1. **Header**: Pack ID, decision ID, generation timestamp, content hash
  2. **Executive Summary**: Decision title, severity, outcome
  3. **Policy Applied**: Name, version, valid_from/to, rule definition
  4. **Signals Summary**: Table with signal_type, source, reliability, timestamp
  5. **Exception Context**: What triggered the decision, options presented
  6. **Decision Record**: Chosen option, rationale, assumptions, decided_by, timestamp
  7. **Audit Trail**: Chronological event log
  8. **Integrity Footer**: Content hash for verification

#### 1.2 Add HTML Renderer Service
**File:** `core/services/evidence_renderer.py`

```python
class EvidenceRenderer:
    def render_html(self, evidence_pack: EvidencePack) -> str:
        """Render evidence pack as print-ready HTML."""

    def render_pdf(self, evidence_pack: EvidencePack) -> bytes:
        """Render evidence pack as PDF (uses weasyprint)."""
```

**Dependencies:**
- `jinja2` (already in FastAPI)
- `weasyprint` for PDF generation (optional, can defer)

#### 1.3 Update EvidenceGenerator
**File:** `core/services/evidence_generator.py`

Extend `export_pack()` to support new formats:
```python
def export_pack(self, evidence_pack_id: UUID, format: str = "json") -> bytes:
    if format == "json":
        # existing JSON export
    elif format == "html":
        renderer = EvidenceRenderer()
        return renderer.render_html(pack).encode('utf-8')
    elif format == "pdf":
        renderer = EvidenceRenderer()
        return renderer.render_pdf(pack)
```

#### 1.4 Update API Endpoint
**File:** `core/api/evidence.py`

- Add `format` enum: `json`, `html`, `pdf`
- Update media types and Content-Disposition headers
- Add `inline` query param for browser preview vs download

```python
@router.get("/{decision_id}/export")
def export_evidence_pack(
    decision_id: str,
    format: Literal["json", "html", "pdf"] = "html",
    inline: bool = False,  # True = view in browser, False = download
    db: Session = Depends(get_db)
)
```

---

### Phase 2: Deterministic Ordering

#### 2.1 Canonical Sort Order
Ensure all lists are sorted deterministically:
- **Signals**: by `observed_at` ascending
- **Audit trail**: by `occurred_at` ascending
- **Options**: by `option_id` (preserve original order)

#### 2.2 Template Formatting
- Timestamps: ISO 8601 format with timezone
- UUIDs: Full format (not shortened)
- Numbers: Locale-independent formatting

---

### Phase 3: PDF Generation (Optional Enhancement)

#### 3.1 WeasyPrint Integration
```bash
pip install weasyprint
```

#### 3.2 PDF-Specific Styling
- Page breaks at section boundaries
- Headers/footers with page numbers
- Print margins optimized for A4/Letter

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `core/templates/evidence_pack.html` | Create | Jinja2 template with print CSS |
| `core/services/evidence_renderer.py` | Create | HTML/PDF rendering service |
| `core/services/evidence_generator.py` | Modify | Add html/pdf format support |
| `core/api/evidence.py` | Modify | Update format options, media types |
| `core/requirements.txt` | Modify | Add weasyprint (for PDF) |
| `tests/core/test_evidence_export.py` | Create | Export format tests |

---

## HTML Template Structure

```html
<!DOCTYPE html>
<html>
<head>
    <title>Evidence Pack - {{ decision.id }}</title>
    <style>
        /* Print-optimized CSS */
        @media print { ... }
    </style>
</head>
<body>
    <header>
        <h1>Governance OS - Evidence Pack</h1>
        <div class="metadata">
            Pack ID: {{ pack_id }}<br>
            Generated: {{ generated_at }}<br>
            Hash: {{ content_hash }}
        </div>
    </header>

    <section id="summary">
        <h2>Executive Summary</h2>
        <p><strong>Exception:</strong> {{ exception.title }}</p>
        <p><strong>Severity:</strong> {{ exception.severity }}</p>
        <p><strong>Decision:</strong> {{ decision.chosen_option_label }}</p>
    </section>

    <section id="policy">
        <h2>Policy Applied</h2>
        <table>
            <tr><td>Name</td><td>{{ policy.name }}</td></tr>
            <tr><td>Version</td><td>{{ policy.version.version_number }}</td></tr>
            <tr><td>Valid From</td><td>{{ policy.version.valid_from }}</td></tr>
        </table>
    </section>

    <section id="signals">
        <h2>Contributing Signals</h2>
        <table>
            <thead>
                <tr><th>Type</th><th>Source</th><th>Reliability</th><th>Observed</th></tr>
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

    <section id="exception">
        <h2>Exception Details</h2>
        <p><strong>Context:</strong></p>
        <pre>{{ exception.context | tojson(indent=2) }}</pre>
        <h3>Options Presented</h3>
        <ol>
            {% for option in exception.options %}
            <li>
                <strong>{{ option.label }}</strong>
                {% if option.id == decision.chosen_option_id %}✓ CHOSEN{% endif %}
                <p>{{ option.description }}</p>
            </li>
            {% endfor %}
        </ol>
    </section>

    <section id="decision">
        <h2>Decision Record</h2>
        <table>
            <tr><td>Chosen Option</td><td>{{ decision.chosen_option_id }}</td></tr>
            <tr><td>Rationale</td><td>{{ decision.rationale }}</td></tr>
            <tr><td>Assumptions</td><td>{{ decision.assumptions | join(', ') }}</td></tr>
            <tr><td>Decided By</td><td>{{ decision.decided_by }}</td></tr>
            <tr><td>Decided At</td><td>{{ decision.decided_at }}</td></tr>
        </table>
    </section>

    <section id="audit-trail">
        <h2>Audit Trail</h2>
        <table>
            <thead>
                <tr><th>Time</th><th>Event</th><th>Actor</th><th>Details</th></tr>
            </thead>
            <tbody>
                {% for event in audit_trail %}
                <tr>
                    <td>{{ event.occurred_at }}</td>
                    <td>{{ event.event_type }}</td>
                    <td>{{ event.actor }}</td>
                    <td>{{ event.event_data | tojson }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </section>

    <footer>
        <p>Content Hash (SHA256): <code>{{ content_hash }}</code></p>
        <p>This document is deterministically generated. Same inputs produce identical output.</p>
    </footer>
</body>
</html>
```

---

## Testing Strategy

### Unit Tests
1. HTML template renders without errors
2. All evidence fields present in output
3. Deterministic output (same input → same HTML)
4. Proper escaping of user content (XSS prevention)

### Integration Tests
1. API endpoint returns correct Content-Type
2. Download vs inline disposition works
3. PDF generation (if implemented)

### Manual Verification
1. Print preview in browser looks professional
2. PDF prints correctly on A4/Letter
3. All timestamps readable
4. Content hash verifiable

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| WeasyPrint system dependencies | Make PDF optional, HTML is primary |
| Large evidence packs slow to render | Add caching for rendered output |
| XSS in user-provided content | Use Jinja2 autoescape (default on) |
| Non-deterministic rendering | Sort all lists, use consistent formatting |

---

## Estimated Scope
- **HTML export**: ~200 lines (template + renderer)
- **API updates**: ~30 lines
- **Tests**: ~100 lines
- **PDF (optional)**: +50 lines + dependency

## Dependencies
- Jinja2 (already available via FastAPI)
- WeasyPrint (optional, for PDF only)
