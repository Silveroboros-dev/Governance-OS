"""
Cache Manager - Manages context caches for all agents.

This manager:
1. Builds caches for each agent type + pack combination
2. Tracks cache metadata (names, expiry, version)
3. Handles automatic refresh when policies change
4. Provides cache lookup for agent calls

Cache Keys:
- intake_treasury: IntakeAgent for treasury pack
- intake_wealth: IntakeAgent for wealth pack
- narrative_treasury: NarrativeAgent for treasury pack
- narrative_wealth: NarrativeAgent for wealth pack
- policy_draft_treasury: PolicyDraftAgent for treasury pack
- policy_draft_wealth: PolicyDraftAgent for wealth pack
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .gemini_client import GeminiClient


@dataclass
class CacheConfig:
    """Configuration for a cache entry."""
    agent_type: str  # intake, narrative, policy_draft
    pack: str  # treasury, wealth
    display_name: str
    ttl_seconds: int = 3600  # 1 hour default
    version: str = "v1"


@dataclass
class CacheEntry:
    """Metadata for an active cache."""
    cache_name: str  # Full cache name from Gemini (e.g., "caches/abc123")
    config: CacheConfig
    created_at: datetime
    expires_at: datetime
    content_hash: str  # Hash of system prompt for change detection
    policy_version: Optional[str] = None  # For tracking policy changes


class CacheManager:
    """
    Manages Gemini context caches for Governance OS agents.

    Handles:
    - Building caches from prompts + vocabularies + policies
    - Tracking active caches
    - Automatic refresh on policy changes
    - Cache lookup for agent calls
    """

    # Agent types that use caching
    AGENT_TYPES = ["intake", "narrative", "policy_draft"]

    # Packs
    PACKS = ["treasury", "wealth"]

    def __init__(
        self,
        client: Optional[GeminiClient] = None,
        prompts_dir: Optional[Path] = None,
        cache_ttl_seconds: int = 3600,
    ):
        """
        Initialize the cache manager.

        Args:
            client: GeminiClient instance (created if not provided)
            prompts_dir: Path to prompts directory
            cache_ttl_seconds: Default TTL for caches
        """
        self._client = client
        self._prompts_dir = prompts_dir or Path(__file__).parent.parent / "prompts"
        self._cache_ttl = cache_ttl_seconds

        # Active caches: key -> CacheEntry
        self._caches: Dict[str, CacheEntry] = {}

        # Track policy versions for change detection
        self._policy_versions: Dict[str, str] = {}

    @property
    def client(self) -> GeminiClient:
        """Lazily initialize the Gemini client."""
        if self._client is None:
            self._client = GeminiClient()
        return self._client

    def get_cache_key(self, agent_type: str, pack: str) -> str:
        """Get the cache key for an agent/pack combination."""
        return f"{agent_type}_{pack}"

    def get_cache_name(self, agent_type: str, pack: str) -> Optional[str]:
        """
        Get the Gemini cache name for an agent/pack.

        Returns None if cache doesn't exist or is expired.
        """
        key = self.get_cache_key(agent_type, pack)
        entry = self._caches.get(key)

        if entry and entry.expires_at > datetime.utcnow():
            return entry.cache_name

        return None

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt file."""
        path = self._prompts_dir / filename
        if path.exists():
            return path.read_text()
        return ""

    def _build_system_prompt(self, agent_type: str, pack: str) -> str:
        """
        Build the full system prompt for an agent/pack.

        Combines:
        - Base system prompt
        - Pack-specific vocabulary
        - Active policies (for policy-aware caching)
        """
        parts = []

        # Base system prompt
        if agent_type == "intake":
            parts.append(self._load_prompt("intake_system.txt"))
            parts.append(self._load_prompt(f"intake_{pack}.txt"))
        elif agent_type == "narrative":
            parts.append(self._load_prompt("narrative_system.txt"))
        elif agent_type == "policy_draft":
            parts.append(self._load_prompt("policy_draft_system.txt"))
            parts.append(self._load_prompt(f"intake_{pack}.txt"))  # Needs vocabulary

        # Combine all parts
        return "\n\n".join(filter(None, parts))

    def _compute_content_hash(self, content: str) -> str:
        """Compute hash of content for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def build_cache(
        self,
        agent_type: str,
        pack: str,
        force_rebuild: bool = False,
    ) -> Optional[str]:
        """
        Build or retrieve a cache for an agent/pack.

        Args:
            agent_type: Agent type (intake, narrative, policy_draft)
            pack: Pack (treasury, wealth)
            force_rebuild: Force rebuild even if cache exists

        Returns:
            Cache name if successful, None otherwise
        """
        key = self.get_cache_key(agent_type, pack)

        # Check existing cache
        existing = self._caches.get(key)
        if existing and not force_rebuild:
            if existing.expires_at > datetime.utcnow():
                return existing.cache_name

        # Build system prompt
        system_prompt = self._build_system_prompt(agent_type, pack)
        if not system_prompt:
            return None

        content_hash = self._compute_content_hash(system_prompt)

        # Check if content changed (skip rebuild if same)
        if existing and existing.content_hash == content_hash and not force_rebuild:
            # Content unchanged, just check if cache still valid
            cache = self.client.get_cache(existing.cache_name)
            if cache:
                return existing.cache_name

        # Delete old cache if exists
        if existing:
            self.client.delete_cache(existing.cache_name)

        # Create new cache
        display_name = f"govos_{agent_type}_{pack}"
        try:
            cache_name = self.client.create_cache(
                display_name=display_name,
                system_instruction=system_prompt,
                ttl=f"{self._cache_ttl}s",
            )
        except Exception as e:
            print(f"Failed to create cache for {key}: {e}")
            return None

        # Store entry
        now = datetime.utcnow()
        self._caches[key] = CacheEntry(
            cache_name=cache_name,
            config=CacheConfig(
                agent_type=agent_type,
                pack=pack,
                display_name=display_name,
                ttl_seconds=self._cache_ttl,
            ),
            created_at=now,
            expires_at=now + timedelta(seconds=self._cache_ttl),
            content_hash=content_hash,
            policy_version=self._policy_versions.get(pack),
        )

        return cache_name

    def build_all_caches(self, force_rebuild: bool = False) -> Dict[str, str]:
        """
        Build caches for all agent/pack combinations.

        Returns:
            Dict mapping cache keys to cache names
        """
        results = {}

        for agent_type in self.AGENT_TYPES:
            for pack in self.PACKS:
                cache_name = self.build_cache(agent_type, pack, force_rebuild)
                if cache_name:
                    key = self.get_cache_key(agent_type, pack)
                    results[key] = cache_name

        return results

    def invalidate_pack(self, pack: str) -> List[str]:
        """
        Invalidate all caches for a pack.

        Call this when policies change for a pack.

        Args:
            pack: Pack to invalidate

        Returns:
            List of invalidated cache keys
        """
        invalidated = []

        for agent_type in self.AGENT_TYPES:
            key = self.get_cache_key(agent_type, pack)
            entry = self._caches.get(key)

            if entry:
                self.client.delete_cache(entry.cache_name)
                del self._caches[key]
                invalidated.append(key)

        return invalidated

    def on_policy_change(self, pack: str, new_version: str) -> Dict[str, str]:
        """
        Handle policy change - invalidate and rebuild caches.

        Call this when a policy is approved/updated.

        Args:
            pack: Pack that changed
            new_version: New policy version identifier

        Returns:
            Dict of rebuilt cache names
        """
        # Update version tracking
        self._policy_versions[pack] = new_version

        # Invalidate existing caches
        self.invalidate_pack(pack)

        # Rebuild caches for this pack
        results = {}
        for agent_type in self.AGENT_TYPES:
            cache_name = self.build_cache(agent_type, pack, force_rebuild=True)
            if cache_name:
                key = self.get_cache_key(agent_type, pack)
                results[key] = cache_name

        return results

    def get_system_prompt(self, agent_type: str, pack: str) -> str:
        """
        Get the system prompt for an agent/pack (for non-cached calls).

        Useful as fallback when cache is unavailable.
        """
        return self._build_system_prompt(agent_type, pack)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about active caches."""
        now = datetime.utcnow()
        active = 0
        expired = 0

        for entry in self._caches.values():
            if entry.expires_at > now:
                active += 1
            else:
                expired += 1

        return {
            "total_caches": len(self._caches),
            "active_caches": active,
            "expired_caches": expired,
            "cache_keys": list(self._caches.keys()),
        }

    def cleanup_expired(self) -> int:
        """
        Clean up expired caches.

        Returns:
            Number of caches cleaned up
        """
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self._caches.items()
            if entry.expires_at <= now
        ]

        for key in expired_keys:
            entry = self._caches[key]
            self.client.delete_cache(entry.cache_name)
            del self._caches[key]

        return len(expired_keys)


# Singleton instance for app-wide use
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def invalidate_on_policy_change(pack: str, version: str) -> Dict[str, str]:
    """
    Convenience function to invalidate caches on policy change.

    Call this from the approval queue handler when a policy is approved.
    """
    return get_cache_manager().on_policy_change(pack, version)
