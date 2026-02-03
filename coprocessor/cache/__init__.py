"""
Context Caching Module for Gemini 3 API.

This module provides enterprise-grade context caching for the Governance OS
coprocessor layer using Google's Gemini 3 API.

Benefits:
- 90% cost reduction on cached tokens (Gemini 3)
- 40-50% latency reduction
- Automatic refresh when policies change

Usage:
    from coprocessor.cache import GeminiClient, CacheManager

    client = GeminiClient()
    cache_manager = CacheManager(client)

    # Build caches for all packs
    cache_manager.build_all_caches()

    # Use in agents
    response = client.generate_with_cache(
        cache_name=cache_manager.get_cache_name("intake", "treasury"),
        user_prompt="Extract signals from..."
    )
"""

from .gemini_client import GeminiClient, ThinkingResponse
from .manager import CacheManager, CacheConfig, get_cache_manager, invalidate_on_policy_change

__all__ = [
    "GeminiClient",
    "ThinkingResponse",
    "CacheManager",
    "CacheConfig",
    "get_cache_manager",
    "invalidate_on_policy_change",
]
