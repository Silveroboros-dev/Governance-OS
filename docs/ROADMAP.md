# Governance OS Roadmap

## Completed Sprints

### Sprint 1: Deterministic Governance Kernel
- Policy versioning with temporal validity
- Signal ingestion with provenance
- Deterministic evaluator with input hashing
- Exception engine with fingerprint deduplication
- One-screen decision UI (symmetric options, no recommendations)
- Immutable decision log with rationale/assumptions
- Evidence pack generation and export (JSON, HTML, PDF)
- Treasury pack with sample policies

### Sprint 2: Packs + Replay + AI Thin-Slice
- Treasury + Wealth packs (8 signal types, 8 policies each)
- CSV ingestion with SHA256 provenance tracking
- Replay harness with isolated namespaces
- Replay comparison tools (before/after policy changes)
- Exception budgets + metrics
- MCP Server (read-only tools)
- NarrativeAgent v0 (grounded memos)
- Evals v0 (CI gate on hallucinations)

### Sprint 3: Agentic Coprocessor
- MCP write tools with approval gates
- IntakeAgent (unstructured → candidate signals)
- PolicyDraftAgent (natural language → policy drafts)
- Approval queue with human-in-the-loop
- Agent tracing viewer
- Expanded eval suites + CI gates

---

## Future Development

### Sprint 4: Live Signal Ingestion

**Goal:** Connect to real data sources for continuous signal flow.

#### Connectors Framework
- [ ] Connector base class with scheduling, retry, circuit breaker
- [ ] Connector registry and configuration
- [ ] Health monitoring dashboard

#### Market Data Connectors
- [ ] Bloomberg API connector (positions, prices, volatility)
- [ ] Reuters/Refinitiv connector
- [ ] Crypto exchange APIs (Coinbase, Binance)
- [ ] FX rate feeds

#### Internal System Connectors
- [ ] REST API polling connector (generic)
- [ ] Webhook receiver (push-based)
- [ ] Database connector (read from source DBs)
- [ ] File watcher (CSV/Excel drops)

#### Scheduling & Orchestration
- [ ] Cron-based evaluation scheduler
- [ ] Real-time evaluation on signal arrival
- [ ] Batch vs streaming mode configuration
- [ ] Rate limiting and backpressure

---

### Sprint 5: Notification & Escalation

**Goal:** Proactive alerting when exceptions require attention.

#### Notification Channels
- [ ] Email notifications (exception raised, SLA approaching)
- [ ] Slack/Teams integration
- [ ] SMS for critical exceptions
- [ ] Mobile push notifications

#### Escalation Engine
- [ ] SLA configuration per severity (e.g., critical = 2 hours)
- [ ] Auto-escalation when SLA breached
- [ ] Escalation paths (analyst → manager → director)
- [ ] On-call rotation integration (PagerDuty, OpsGenie)

#### Digest & Summary
- [ ] Daily exception digest email
- [ ] Weekly decision summary report
- [ ] Trend alerts (exception volume spike)

---

### Sprint 6: Multi-Tenancy & Access Control

**Goal:** Support multiple organizations and role-based permissions.

#### Organization Management
- [ ] Organization model (tenant isolation)
- [ ] Organization-scoped policies, signals, decisions
- [ ] Cross-org reporting for parent companies

#### Authentication & Authorization
- [ ] SSO integration (SAML, OIDC)
- [ ] Role-based access control (RBAC)
- [ ] Roles: Viewer, Analyst, Decider, Approver, Admin
- [ ] Audit log of permission changes

#### Pack Customization
- [ ] Per-org pack configuration
- [ ] Custom signal types and policies
- [ ] White-label UI theming

---

### Sprint 7: Advanced Analytics & Reporting

**Goal:** Insights from decision history and policy performance.

#### Decision Analytics
- [ ] Decision time distribution (time to resolve exceptions)
- [ ] Decision patterns by user, policy, severity
- [ ] Override analysis (how often, by whom, outcomes)

#### Policy Performance
- [ ] False positive rate per policy
- [ ] Policy precision/recall metrics
- [ ] Threshold optimization recommendations

#### Compliance Reporting
- [ ] Audit report generator (date range, filters)
- [ ] Regulatory export formats (SOX, Basel)
- [ ] Evidence pack bulk export

#### Dashboards
- [ ] Executive summary dashboard
- [ ] Operational metrics dashboard
- [ ] Policy tuning dashboard

---

### Sprint 8: Workflow Automation

**Goal:** Automate routine decisions while preserving human oversight.

#### Auto-Resolution Rules
- [ ] Configurable auto-resolve for low-severity exceptions
- [ ] Conditions: signal age, confidence, pattern matching
- [ ] Auto-resolve audit trail (clearly marked as automated)

#### Decision Templates
- [ ] Pre-filled rationale templates per exception type
- [ ] One-click decisions for routine cases
- [ ] Template usage analytics

#### Workflow Orchestration
- [ ] Multi-step approval workflows
- [ ] Parallel approval (e.g., Risk + Compliance)
- [ ] Conditional branching based on decision

---

### Sprint 9: External Integrations

**Goal:** Connect governance decisions to downstream systems.

#### Action Execution
- [ ] Decision → trigger downstream action (via webhook)
- [ ] Integration with order management systems
- [ ] Integration with risk systems (limits adjustment)

#### Document Generation
- [ ] Auto-generate board memos from evidence packs
- [ ] Regulatory filing drafts
- [ ] Client communication templates

#### Data Export
- [ ] Data warehouse integration (Snowflake, BigQuery)
- [ ] BI tool connectors (Tableau, PowerBI)
- [ ] API for custom integrations

---

### Sprint 10: Advanced AI Features

**Goal:** Expand AI assistance while maintaining safety boundaries.

#### Enhanced Intake
- [ ] Multi-document intake (batch processing)
- [ ] Image/chart extraction from PDFs
- [ ] Email thread analysis

#### Decision Support (NOT recommendations)
- [ ] Similar past decisions retrieval
- [ ] Outcome tracking (what happened after decision X?)
- [ ] Assumption validation against new data

#### Policy Assistance
- [ ] Policy conflict detection
- [ ] Coverage gap analysis
- [ ] Natural language policy queries

#### Eval Expansion
- [ ] Continuous eval monitoring in production
- [ ] Drift detection (model behavior changes)
- [ ] A/B testing for prompt improvements

---

## Architecture Principles (Non-Negotiable)

These principles apply to ALL future development:

1. **Deterministic Core** - Policy evaluation, exceptioning, and evidence must remain deterministic and replayable

2. **Human-in-the-Loop** - AI assists but never decides. All mutations require human approval

3. **No Recommendations** - Options presented symmetrically. No "AI suggests" or default selections

4. **Audit Everything** - Every state change produces an audit event. Evidence packs are immutable

5. **Uncertainty is Visible** - Confidence gaps, unknowns, and AI limitations are explicit in UI

6. **Fail Safe** - System failures result in human review, never auto-resolution

---

## Contributing

Contributions welcome! For non-trivial changes:

1. Open an issue first to discuss approach
2. Ensure changes maintain determinism (add replay tests)
3. AI features must have eval coverage
4. No recommendations in decision layer

---

*Last updated: January 2026*
