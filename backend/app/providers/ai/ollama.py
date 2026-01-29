"""
Ollama local LLM provider.

Supports:
- Any Ollama model (llama3.2, mistral, etc.)
- Streaming responses
- No function calling (basic chat only)
"""
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from ..protocols import AIProvider, CompletionChunk, Message


class OllamaProvider(AIProvider):
    """
    Ollama local LLM provider.

    Connects to local Ollama server for free, private AI inference.
    No function calling support - uses prompt-based tool handling.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: float = 120.0,
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama server URL (default: localhost:11434)
            model: Model name (default: llama3.2)
            timeout: Request timeout in seconds
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @asynccontextmanager
    async def _get_client(self):
        """Get or create HTTP client with proper cleanup."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
            )
        try:
            yield self._client
        except Exception:
            # Re-raise but don't close client on error
            raise

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_tools(self) -> bool:
        # Most Ollama models don't reliably support tools
        return False

    @property
    def supports_thinking(self) -> bool:
        return False

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> str:
        """Non-streaming chat completion."""
        ollama_messages = self._build_messages(messages, system)

        async with self._get_client() as client:
            response = await client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": ollama_messages,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        """
        Streaming chat completion.

        Note: Tools parameter is ignored for Ollama.
        Use prompt-based tool handling instead.
        """
        ollama_messages = self._build_messages(messages, system)

        async with self._get_client() as client:
            async with client.stream(
                "POST",
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": ollama_messages,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Extract content from message
                    content = data.get("message", {}).get("content")
                    if content:
                        yield CompletionChunk(type="text", content=content)

                    # Check if done
                    if data.get("done"):
                        yield CompletionChunk(type="done")
                        break

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_messages(
        self,
        messages: list[Message],
        system: str | None,
    ) -> list[dict]:
        """Build Ollama message format."""
        ollama_messages = []

        # Add system message
        if system:
            ollama_messages.append({"role": "system", "content": system})

        # Add conversation messages
        for msg in messages:
            ollama_messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        return ollama_messages
