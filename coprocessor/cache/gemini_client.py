"""
Gemini 3 Client with Context Caching Support.

This client wraps the Google GenAI SDK (google-genai) and provides
context caching for agent calls using Gemini 3 models.

Gemini 3 provides:
- 90% cost reduction on cached tokens
- 1M token context window
- Thinking Mode for transparent reasoning (Hack D)

Usage:
    from google import genai

    client = GeminiClient()

    # With caching (recommended for agents)
    response = client.generate_with_cache(
        cache_name="caches/abc123",
        user_prompt="Extract signals from...",
    )

    # Without caching (for one-off calls)
    response = client.generate(
        system_prompt="You are...",
        user_prompt="...",
    )

    # With thinking mode (returns reasoning chain)
    response = client.generate_with_thinking(
        user_prompt="Extract signals from...",
        system_prompt="You are...",
        thinking_budget=8192,
    )
"""

import os
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types


@dataclass
class ThinkingResponse:
    """Response from a thinking-enabled generation."""
    text: str
    thoughts: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class GeminiClient:
    """
    Gemini 3 API client with integrated context caching.

    Provides:
    - Automatic cache management for system prompts + vocabularies
    - Cache refresh on policy changes
    - JSON response mode for structured outputs
    """

    # Gemini 3 models
    GEMINI_3_FLASH = "gemini-3-flash-preview"
    GEMINI_3_PRO = "gemini-3-pro-preview"

    # Minimum tokens for caching (Flash=1024, Pro=4096)
    MIN_CACHE_TOKENS = {
        GEMINI_3_FLASH: 1024,
        GEMINI_3_PRO: 4096,
    }

    # Default cache TTL (1 hour)
    DEFAULT_CACHE_TTL = "3600s"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = GEMINI_3_FLASH,
    ):
        """
        Initialize the Gemini 3 client.

        Args:
            api_key: Google AI API key (defaults to GOOGLE_API_KEY env var)
            model: Model to use (gemini-3-flash-preview or gemini-3-pro-preview)
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY env var or pass api_key."
            )

        self.model = model

        # Initialize the client
        # Note: google-genai uses GOOGLE_API_KEY env var automatically,
        # but we can also pass it explicitly
        if self.api_key != os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = self.api_key

        self._client = genai.Client()

    def generate(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.1,
    ) -> str:
        """
        Generate a response without caching.

        Args:
            user_prompt: The user's prompt/question
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (lower = more deterministic)

        Returns:
            Generated text response (JSON string for structured outputs)
        """
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
            response_mime_type="application/json",
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )

        return response.text

    def generate_with_cache(
        self,
        cache_name: str,
        user_prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.1,
    ) -> str:
        """
        Generate a response using cached context.

        This is the primary method for agent calls. Uses the cached
        system prompt + vocabulary for 90% cost savings.

        Args:
            cache_name: Full cache name (e.g., "caches/abc123xyz")
            user_prompt: The user's prompt/question
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Generated text response (JSON string)
        """
        config = types.GenerateContentConfig(
            cached_content=cache_name,
            max_output_tokens=max_tokens,
            temperature=temperature,
            response_mime_type="application/json",
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )

        return response.text

    def create_cache(
        self,
        display_name: str,
        system_instruction: str,
        contents: Optional[List[Any]] = None,
        ttl: str = DEFAULT_CACHE_TTL,
    ) -> str:
        """
        Create a new cached context.

        Args:
            display_name: Human-readable name (e.g., "govos_intake_treasury")
            system_instruction: The system prompt to cache
            contents: Optional additional content (files, etc.)
            ttl: Time-to-live (default 1 hour, format: "3600s")

        Returns:
            Cache name (e.g., "caches/abc123xyz")
        """
        cache_config = types.CreateCachedContentConfig(
            display_name=display_name,
            system_instruction=system_instruction,
            contents=contents or [],
            ttl=ttl,
        )

        cache = self._client.caches.create(
            model=self.model,
            config=cache_config,
        )

        return cache.name

    def delete_cache(self, cache_name: str) -> bool:
        """
        Delete a cached context.

        Args:
            cache_name: Full cache name to delete

        Returns:
            True if deleted successfully
        """
        try:
            self._client.caches.delete(cache_name)
            return True
        except Exception:
            return False

    def get_cache(self, cache_name: str) -> Optional[Any]:
        """
        Get a cache by name.

        Args:
            cache_name: Full cache name

        Returns:
            Cache object or None if not found
        """
        try:
            return self._client.caches.get(name=cache_name)
        except Exception:
            return None

    def list_caches(self) -> List[Any]:
        """List all cached contexts."""
        return list(self._client.caches.list())

    def update_cache_ttl(self, cache_name: str, ttl: str) -> bool:
        """
        Update cache TTL.

        Args:
            cache_name: Full cache name
            ttl: New TTL (e.g., "7200s" for 2 hours)

        Returns:
            True if updated successfully
        """
        try:
            self._client.caches.update(
                name=cache_name,
                config=types.UpdateCachedContentConfig(ttl=ttl),
            )
            return True
        except Exception:
            return False

    def get_usage_metadata(self, response: Any) -> Dict[str, Any]:
        """
        Extract usage metadata from a response.

        Shows cached vs non-cached token usage for cost analysis.
        """
        if hasattr(response, 'usage_metadata'):
            meta = response.usage_metadata
            return {
                "prompt_tokens": getattr(meta, 'prompt_token_count', 0),
                "cached_tokens": getattr(meta, 'cached_content_token_count', 0),
                "output_tokens": getattr(meta, 'candidates_token_count', 0),
            }
        return {}

    def generate_with_thinking(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        thinking_budget: int = 8192,
    ) -> ThinkingResponse:
        """
        Generate a response with Thinking Mode enabled.

        Gemini 3's Thinking Mode shows the model's reasoning process,
        providing audit-grade transparency for signal extraction.

        Args:
            user_prompt: The user's prompt/question
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            thinking_budget: Token budget for thinking (default 8192)

        Returns:
            ThinkingResponse with text, thoughts, and usage metadata
        """
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=thinking_budget,
            ),
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )

        # Extract thoughts and text from response parts
        thoughts = None
        text_parts = []

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'thought') and part.thought:
                    thoughts = part.text
                elif hasattr(part, 'text') and part.text:
                    # Collect ALL text parts (not just the last one)
                    text_parts.append(part.text)

        # Concatenate all text parts
        text = "".join(text_parts)

        return ThinkingResponse(
            text=text,
            thoughts=thoughts,
            usage=self.get_usage_metadata(response),
        )

    def generate_with_cache_and_thinking(
        self,
        cache_name: str,
        user_prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        thinking_budget: int = 8192,
    ) -> ThinkingResponse:
        """
        Generate with both caching AND thinking mode.

        Combines 50-60% cost savings from caching with transparent reasoning.

        Args:
            cache_name: Full cache name (e.g., "caches/abc123xyz")
            user_prompt: The user's prompt/question
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            thinking_budget: Token budget for thinking (default 8192)

        Returns:
            ThinkingResponse with text, thoughts, and usage metadata
        """
        config = types.GenerateContentConfig(
            cached_content=cache_name,
            max_output_tokens=max_tokens,
            temperature=temperature,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=thinking_budget,
            ),
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )

        # Extract thoughts and text from response parts
        thoughts = None
        text_parts = []

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'thought') and part.thought:
                    thoughts = part.text
                elif hasattr(part, 'text') and part.text:
                    # Collect ALL text parts (not just the last one)
                    text_parts.append(part.text)

        # Concatenate all text parts
        text = "".join(text_parts)

        return ThinkingResponse(
            text=text,
            thoughts=thoughts,
            usage=self.get_usage_metadata(response),
        )
