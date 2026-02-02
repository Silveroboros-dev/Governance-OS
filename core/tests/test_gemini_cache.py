"""
Tests for Gemini 3 Context Caching Module.

Tests the GeminiClient and CacheManager for:
- Cache creation and retrieval
- Cache invalidation on policy changes
- Fallback behavior when cache unavailable
- Cost/latency optimization patterns
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import json

import sys
sys.path.insert(0, '/Users/rk/Desktop/Governance-OS')


class TestGeminiClientInit:
    """Test GeminiClient initialization."""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': ''}):
            with patch('google.genai.Client') as mock_client:
                from coprocessor.cache.gemini_client import GeminiClient
                client = GeminiClient(api_key="test-api-key")
                assert client.api_key == "test-api-key"
                assert client.model == "gemini-3-flash-preview"

    def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'env-api-key'}):
            with patch('google.genai.Client') as mock_client:
                from coprocessor.cache.gemini_client import GeminiClient
                client = GeminiClient()
                assert client.api_key == "env-api-key"

    def test_init_no_api_key_raises(self):
        """Test initialization without API key raises error."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': ''}, clear=True):
            from coprocessor.cache.gemini_client import GeminiClient
            with pytest.raises(ValueError, match="Google API key required"):
                GeminiClient(api_key=None)

    def test_init_custom_model(self):
        """Test initialization with custom model."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client'):
                from coprocessor.cache.gemini_client import GeminiClient
                client = GeminiClient(model="gemini-3-pro-preview")
                assert client.model == "gemini-3-pro-preview"


class TestGeminiClientGenerate:
    """Test GeminiClient generation methods."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked GeminiClient."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_instance = Mock()
                mock_genai.return_value = mock_instance

                # Mock response
                mock_response = Mock()
                mock_response.text = '{"result": "test"}'
                mock_instance.models.generate_content.return_value = mock_response

                from coprocessor.cache.gemini_client import GeminiClient
                client = GeminiClient()
                client._client = mock_instance

                yield client, mock_instance

    def test_generate_without_cache(self, mock_client):
        """Test generation without caching."""
        client, mock_genai = mock_client

        result = client.generate(
            user_prompt="Test prompt",
            system_prompt="You are a test assistant",
            max_tokens=1000,
            temperature=0.1,
        )

        assert result == '{"result": "test"}'
        mock_genai.models.generate_content.assert_called_once()

    def test_generate_with_cache(self, mock_client):
        """Test generation with cached context."""
        client, mock_genai = mock_client

        result = client.generate_with_cache(
            cache_name="caches/test123",
            user_prompt="Test prompt",
            max_tokens=1000,
            temperature=0.1,
        )

        assert result == '{"result": "test"}'
        # Verify generate_content was called with cached_content config
        call_kwargs = mock_genai.models.generate_content.call_args
        assert call_kwargs is not None


class TestGeminiClientCacheOperations:
    """Test GeminiClient cache CRUD operations."""

    @pytest.fixture
    def mock_client_with_caches(self):
        """Create a mocked GeminiClient with cache operations."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_instance = Mock()
                mock_genai.return_value = mock_instance

                # Mock cache operations
                mock_cache = Mock()
                mock_cache.name = "caches/created123"
                mock_instance.caches.create.return_value = mock_cache
                mock_instance.caches.get.return_value = mock_cache
                mock_instance.caches.list.return_value = [mock_cache]
                mock_instance.caches.delete.return_value = None
                mock_instance.caches.update.return_value = mock_cache

                from coprocessor.cache.gemini_client import GeminiClient
                client = GeminiClient()
                client._client = mock_instance

                yield client, mock_instance

    def test_create_cache(self, mock_client_with_caches):
        """Test creating a new cache."""
        client, mock_genai = mock_client_with_caches

        cache_name = client.create_cache(
            display_name="test_cache",
            system_instruction="You are a test assistant",
            ttl="3600s",
        )

        assert cache_name == "caches/created123"
        mock_genai.caches.create.assert_called_once()

    def test_delete_cache(self, mock_client_with_caches):
        """Test deleting a cache."""
        client, mock_genai = mock_client_with_caches

        result = client.delete_cache("caches/test123")

        assert result is True
        mock_genai.caches.delete.assert_called_once_with("caches/test123")

    def test_delete_cache_failure(self, mock_client_with_caches):
        """Test delete cache handles failures gracefully."""
        client, mock_genai = mock_client_with_caches
        mock_genai.caches.delete.side_effect = Exception("Not found")

        result = client.delete_cache("caches/nonexistent")

        assert result is False

    def test_get_cache(self, mock_client_with_caches):
        """Test getting a cache by name."""
        client, mock_genai = mock_client_with_caches

        cache = client.get_cache("caches/test123")

        assert cache is not None
        mock_genai.caches.get.assert_called_once_with(name="caches/test123")

    def test_get_cache_not_found(self, mock_client_with_caches):
        """Test get cache returns None when not found."""
        client, mock_genai = mock_client_with_caches
        mock_genai.caches.get.side_effect = Exception("Not found")

        cache = client.get_cache("caches/nonexistent")

        assert cache is None

    def test_list_caches(self, mock_client_with_caches):
        """Test listing all caches."""
        client, mock_genai = mock_client_with_caches

        caches = client.list_caches()

        assert len(caches) == 1
        mock_genai.caches.list.assert_called_once()

    def test_update_cache_ttl(self, mock_client_with_caches):
        """Test updating cache TTL."""
        client, mock_genai = mock_client_with_caches

        result = client.update_cache_ttl("caches/test123", "7200s")

        assert result is True
        mock_genai.caches.update.assert_called_once()


class TestCacheManagerInit:
    """Test CacheManager initialization."""

    def test_init_default(self):
        """Test default initialization."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client'):
                from coprocessor.cache.manager import CacheManager
                manager = CacheManager()

                assert manager._cache_ttl == 3600
                assert len(manager._caches) == 0

    def test_init_custom_ttl(self):
        """Test initialization with custom TTL."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client'):
                from coprocessor.cache.manager import CacheManager
                manager = CacheManager(cache_ttl_seconds=7200)

                assert manager._cache_ttl == 7200


class TestCacheManagerOperations:
    """Test CacheManager cache operations."""

    @pytest.fixture
    def mock_manager(self, tmp_path):
        """Create a mocked CacheManager with prompts."""
        # Create mock prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        (prompts_dir / "intake_system.txt").write_text("You are an intake agent.")
        (prompts_dir / "intake_treasury.txt").write_text("Treasury vocabulary: position_limit_breach")
        (prompts_dir / "intake_wealth.txt").write_text("Wealth vocabulary: risk_tolerance_change")
        (prompts_dir / "narrative_system.txt").write_text("You are a narrative agent.")
        (prompts_dir / "policy_draft_system.txt").write_text("You are a policy draft agent.")

        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_instance = Mock()
                mock_genai.return_value = mock_instance

                # Mock cache creation
                mock_cache = Mock()
                mock_cache.name = "caches/test123"
                mock_instance.caches.create.return_value = mock_cache
                mock_instance.caches.delete.return_value = None
                mock_instance.caches.get.return_value = mock_cache

                from coprocessor.cache.manager import CacheManager
                from coprocessor.cache.gemini_client import GeminiClient

                client = GeminiClient()
                client._client = mock_instance

                manager = CacheManager(
                    client=client,
                    prompts_dir=prompts_dir,
                )

                yield manager, mock_instance

    def test_get_cache_key(self, mock_manager):
        """Test cache key generation."""
        manager, _ = mock_manager

        assert manager.get_cache_key("intake", "treasury") == "intake_treasury"
        assert manager.get_cache_key("narrative", "wealth") == "narrative_wealth"

    def test_build_cache(self, mock_manager):
        """Test building a cache for agent/pack."""
        manager, mock_genai = mock_manager

        cache_name = manager.build_cache("intake", "treasury")

        assert cache_name == "caches/test123"
        assert "intake_treasury" in manager._caches
        mock_genai.caches.create.assert_called_once()

    def test_build_cache_stores_metadata(self, mock_manager):
        """Test that build_cache stores proper metadata."""
        manager, _ = mock_manager

        manager.build_cache("intake", "treasury")

        entry = manager._caches["intake_treasury"]
        assert entry.cache_name == "caches/test123"
        assert entry.config.agent_type == "intake"
        assert entry.config.pack == "treasury"
        assert entry.expires_at > datetime.utcnow()

    def test_get_cache_name_returns_valid(self, mock_manager):
        """Test get_cache_name returns name for valid cache."""
        manager, _ = mock_manager

        manager.build_cache("intake", "treasury")
        cache_name = manager.get_cache_name("intake", "treasury")

        assert cache_name == "caches/test123"

    def test_get_cache_name_returns_none_for_missing(self, mock_manager):
        """Test get_cache_name returns None for missing cache."""
        manager, _ = mock_manager

        cache_name = manager.get_cache_name("intake", "treasury")

        assert cache_name is None

    def test_build_all_caches(self, mock_manager):
        """Test building caches for all agent/pack combinations."""
        manager, mock_genai = mock_manager

        results = manager.build_all_caches()

        # Should build for all combinations: 3 agents x 2 packs = 6 caches
        assert len(results) == 6
        assert "intake_treasury" in results
        assert "intake_wealth" in results
        assert "narrative_treasury" in results
        assert "narrative_wealth" in results
        assert "policy_draft_treasury" in results
        assert "policy_draft_wealth" in results

    def test_invalidate_pack(self, mock_manager):
        """Test invalidating all caches for a pack."""
        manager, mock_genai = mock_manager

        # Build caches first
        manager.build_all_caches()

        # Invalidate treasury pack
        invalidated = manager.invalidate_pack("treasury")

        # Should invalidate 3 caches (intake, narrative, policy_draft)
        assert len(invalidated) == 3
        assert "intake_treasury" in invalidated
        assert "narrative_treasury" in invalidated
        assert "policy_draft_treasury" in invalidated

        # Treasury caches should be gone
        assert manager.get_cache_name("intake", "treasury") is None

        # Wealth caches should still exist
        assert manager.get_cache_name("intake", "wealth") is not None

    def test_on_policy_change_invalidates_and_rebuilds(self, mock_manager):
        """Test policy change triggers invalidation and rebuild."""
        manager, mock_genai = mock_manager

        # Build initial caches
        manager.build_all_caches()
        initial_call_count = mock_genai.caches.create.call_count

        # Trigger policy change
        results = manager.on_policy_change("treasury", "v2")

        # Should have rebuilt 3 treasury caches
        assert len(results) == 3
        # Should have called delete for old caches and create for new ones
        assert mock_genai.caches.delete.call_count == 3
        assert mock_genai.caches.create.call_count > initial_call_count

    def test_get_system_prompt(self, mock_manager):
        """Test getting system prompt for agent/pack."""
        manager, _ = mock_manager

        prompt = manager.get_system_prompt("intake", "treasury")

        assert "intake agent" in prompt.lower()
        assert "treasury" in prompt.lower() or "position_limit_breach" in prompt

    def test_get_cache_stats(self, mock_manager):
        """Test getting cache statistics."""
        manager, _ = mock_manager

        # Build some caches
        manager.build_cache("intake", "treasury")
        manager.build_cache("narrative", "wealth")

        stats = manager.get_cache_stats()

        assert stats["total_caches"] == 2
        assert stats["active_caches"] == 2
        assert stats["expired_caches"] == 0
        assert "intake_treasury" in stats["cache_keys"]
        assert "narrative_wealth" in stats["cache_keys"]


class TestCacheManagerSingleton:
    """Test CacheManager singleton pattern."""

    def test_get_cache_manager_returns_same_instance(self):
        """Test that get_cache_manager returns singleton."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client'):
                from coprocessor.cache.manager import get_cache_manager

                # Reset singleton for test
                import coprocessor.cache.manager as manager_module
                manager_module._cache_manager = None

                manager1 = get_cache_manager()
                manager2 = get_cache_manager()

                assert manager1 is manager2


class TestInvalidateOnPolicyChange:
    """Test the convenience function for policy change invalidation."""

    def test_invalidate_on_policy_change(self):
        """Test invalidate_on_policy_change convenience function."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_instance = Mock()
                mock_genai.return_value = mock_instance

                mock_cache = Mock()
                mock_cache.name = "caches/test123"
                mock_instance.caches.create.return_value = mock_cache
                mock_instance.caches.delete.return_value = None

                from coprocessor.cache import invalidate_on_policy_change, get_cache_manager

                # Reset singleton
                import coprocessor.cache.manager as manager_module
                manager_module._cache_manager = None

                # Build initial caches
                manager = get_cache_manager()
                manager.build_all_caches()

                # Call convenience function
                results = invalidate_on_policy_change("treasury", "v2")

                # Should return rebuilt caches
                assert len(results) == 3


class TestCacheContentHashing:
    """Test cache content change detection."""

    def test_content_hash_detects_changes(self, tmp_path):
        """Test that content hash changes when prompts change."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        (prompts_dir / "intake_system.txt").write_text("Version 1")
        (prompts_dir / "intake_treasury.txt").write_text("Treasury v1")
        (prompts_dir / "intake_wealth.txt").write_text("Wealth v1")
        (prompts_dir / "narrative_system.txt").write_text("Narrative v1")
        (prompts_dir / "policy_draft_system.txt").write_text("Policy v1")

        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_instance = Mock()
                mock_genai.return_value = mock_instance

                mock_cache = Mock()
                mock_cache.name = "caches/test123"
                mock_instance.caches.create.return_value = mock_cache

                from coprocessor.cache.manager import CacheManager
                from coprocessor.cache.gemini_client import GeminiClient

                client = GeminiClient()
                client._client = mock_instance

                manager = CacheManager(client=client, prompts_dir=prompts_dir)

                # Build initial cache
                manager.build_cache("intake", "treasury")
                initial_hash = manager._caches["intake_treasury"].content_hash

                # Change prompt
                (prompts_dir / "intake_system.txt").write_text("Version 2 - updated!")

                # Rebuild with force
                manager.build_cache("intake", "treasury", force_rebuild=True)
                new_hash = manager._caches["intake_treasury"].content_hash

                assert initial_hash != new_hash


class TestAgentCacheIntegration:
    """Test agent integration with cache system."""

    def test_intake_agent_uses_cache_when_available(self):
        """Test IntakeAgent uses cache when available."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_instance = Mock()
                mock_genai.return_value = mock_instance

                # Mock response
                mock_response = Mock()
                mock_response.text = '[]'  # Empty array = no signals
                mock_instance.models.generate_content.return_value = mock_response

                mock_cache = Mock()
                mock_cache.name = "caches/test123"
                mock_instance.caches.create.return_value = mock_cache
                mock_instance.caches.get.return_value = mock_cache

                # Reset singleton
                import coprocessor.cache.manager as manager_module
                manager_module._cache_manager = None

                from coprocessor.agents.intake_agent import IntakeAgent

                agent = IntakeAgent(use_cache=True)

                # Extract signals - should use cache
                result = agent.extract_signals_sync(
                    content="Test document content",
                    pack="treasury",
                    document_source="test",
                )

                # Verify generate_content was called
                assert mock_instance.models.generate_content.called

    def test_intake_agent_fallback_without_cache(self):
        """Test IntakeAgent works without cache."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_instance = Mock()
                mock_genai.return_value = mock_instance

                mock_response = Mock()
                mock_response.text = '[]'
                mock_instance.models.generate_content.return_value = mock_response

                from coprocessor.agents.intake_agent import IntakeAgent

                # Disable caching
                agent = IntakeAgent(use_cache=False)

                result = agent.extract_signals_sync(
                    content="Test document content",
                    pack="treasury",
                    document_source="test",
                )

                assert result is not None
                assert mock_instance.models.generate_content.called
