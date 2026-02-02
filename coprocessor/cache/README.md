# Gemini 3 Context Caching

Enterprise-grade context caching for Governance OS agents using Google's Gemini 3 API.

## Why Context Caching?

Every agent call sends the same static content:
- System prompts (~2K tokens)
- Pack vocabularies (~1K tokens)
- Policy definitions (~500+ tokens)

**Without caching:** Pay full price for these tokens on every request.

**With caching:** Upload once, reuse across requests. Gemini 3 provides **90% cost reduction** on cached tokens.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CacheManager (Singleton)                 │
│  - Builds caches for each agent_type + pack combination     │
│  - Tracks expiry, content hashes, policy versions           │
│  - Auto-invalidates when policies change                    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
      │IntakeAgent  │ │NarrativeAgent│ │PolicyDraftAgent│
      └─────────────┘ └─────────────┘ └─────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    ┌─────────────────┐
                    │  GeminiClient   │
                    │ gemini-3-flash  │
                    └─────────────────┘
```

## Usage

### Basic Usage (Automatic)

Agents use caching by default:

```python
from coprocessor.agents.intake_agent import IntakeAgent

agent = IntakeAgent()  # use_cache=True by default
result = agent.extract_signals_sync(
    content="Document text...",
    pack="treasury",
    document_source="email/inbox/123",
)
# Cache is built automatically on first call
```

### Pre-warming Caches

For production, pre-warm caches at startup:

```python
from coprocessor.cache import get_cache_manager

manager = get_cache_manager()
manager.build_all_caches()  # Builds 6 caches (3 agents × 2 packs)
```

### Manual Cache Management

```python
from coprocessor.cache import get_cache_manager

manager = get_cache_manager()

# Build specific cache
manager.build_cache("intake", "treasury")

# Check cache status
stats = manager.get_cache_stats()
# {'total_caches': 6, 'active_caches': 6, 'expired_caches': 0, ...}

# Get cache name for direct API use
cache_name = manager.get_cache_name("intake", "treasury")
# "caches/abc123xyz"

# Force rebuild after prompt changes
manager.build_cache("intake", "treasury", force_rebuild=True)
```

### Policy Change Invalidation

Caches auto-invalidate when policies are approved:

```python
from coprocessor.cache import invalidate_on_policy_change

# Called automatically by approval API
# Invalidates all caches for the pack, then rebuilds
invalidate_on_policy_change("treasury", "v2.0")
```

## Cache Keys

Each cache is keyed by `{agent_type}_{pack}`:

| Cache Key | Contents |
|-----------|----------|
| `intake_treasury` | intake_system.txt + intake_treasury.txt |
| `intake_wealth` | intake_system.txt + intake_wealth.txt |
| `narrative_treasury` | narrative_system.txt |
| `narrative_wealth` | narrative_system.txt |
| `policy_draft_treasury` | policy_draft_system.txt + intake_treasury.txt |
| `policy_draft_wealth` | policy_draft_system.txt + intake_wealth.txt |

## Configuration

### Environment Variables

```bash
GOOGLE_API_KEY=your-api-key  # Required
```

### Cache TTL

Default TTL is 1 hour (3600 seconds). Customize at initialization:

```python
from coprocessor.cache import CacheManager

manager = CacheManager(cache_ttl_seconds=7200)  # 2 hours
```

## Cost Savings

| Scenario | Without Cache | With Cache | Savings |
|----------|---------------|------------|---------|
| 100 intake calls/day | ~3.5K tokens × 100 = 350K | 3.5K + (100 × 1K) = 103.5K | 70% |
| With Gemini 3 90% discount | - | Cached tokens at 10% | **90%** |

## Fallback Behavior

If caching fails, agents fall back to non-cached calls:

```python
agent = IntakeAgent(use_cache=True)  # Tries cache first
# If cache unavailable → falls back to regular API call
# No errors, just slightly higher cost/latency
```

Disable caching entirely:

```python
agent = IntakeAgent(use_cache=False)
```

## Testing

```bash
# Run cache module tests
pytest core/tests/test_gemini_cache.py -v

# Run agent integration tests
pytest core/tests/test_sprint3_agents.py -v
```

## Files

```
coprocessor/cache/
├── __init__.py          # Module exports
├── gemini_client.py     # Gemini 3 API wrapper
├── manager.py           # Cache lifecycle management
└── README.md            # This file
```
