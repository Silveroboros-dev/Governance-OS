# Pilot Demo Scripts

Step-by-step scripts for demonstrating Governance OS to stakeholders.

## Available Demos

| Demo | Duration | Audience | Focus |
|------|----------|----------|-------|
| [Treasury Demo](./TREASURY_DEMO.md) | 15-20 min | CFO, Treasury, Risk | Position limits, volatility, cash management |
| [Wealth Demo](./WEALTH_DEMO.md) | 15-20 min | Compliance, Advisors | Suitability, concentration, tax optimization |

## Quick Start

```bash
# Start system
docker compose up -d

# Seed Treasury demo
docker compose exec backend python -m core.scripts.seed_fixtures --pack=treasury --scenarios

# Seed Wealth demo
docker compose exec backend python -m core.scripts.seed_fixtures --pack=wealth --scenarios

# Open UI
open http://localhost:3000
```

## Demo Flow (Both Packs)

1. **Setup** - Start services, seed data
2. **Exception Timeline** - Show filtered exception list
3. **Decision UI** - Walk through one-screen decision interface
4. **Commit Decision** - Record judgment with rationale
5. **Trace View** - Show "why did we do this?" chain
6. **Evidence Export** - Download audit-grade evidence pack
7. **Stats/KPIs** - Show dashboard metrics

## Key Points to Emphasize

- **Deterministic:** Same inputs always produce same outputs
- **No Recommendations:** Options are symmetric, humans decide
- **Evidence Trail:** Every decision produces immutable evidence pack
- **One-Screen:** All context visible without scrolling
- **Uncertainty Visible:** Low-confidence signals are flagged

## Customizing Demos

### Add Custom Scenarios

Edit scenario files:
- `packs/treasury/fixtures/scenarios.json`
- `packs/wealth/fixtures/scenarios.json`

### Seed Specific Scenarios

```bash
# Seed only specific scenario
docker compose exec backend python -m core.scripts.seed_fixtures --pack=treasury --scenario=btc_position_breach_critical
```

### Skip Auto-Evaluation

```bash
# Seed data without triggering evaluations (manual control)
docker compose exec backend python -m core.scripts.seed_fixtures --pack=treasury --scenarios --no-evaluate
```

## Troubleshooting

See individual demo scripts for detailed troubleshooting. Common issues:

```bash
# Services not starting
docker compose logs backend

# Reset everything
docker compose down -v && docker compose up -d

# Re-seed data
docker compose exec backend python -m core.scripts.seed_fixtures --all
```
