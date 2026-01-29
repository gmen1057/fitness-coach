"""
Ollama local embedding provider.

Supports:
- nomic-embed-text (768 dims, recommended)
- mxbai-embed-large (1024 dims)
- Any other Ollama embedding model
"""
from contextlib import asynccontextmanager

import httpx

from ..protocols import EmbeddingProvider


class OllamaEmbedding(EmbeddingProvider):
    """
    Ollama local embedding provider.

    Connects to local Ollama server for free, private embeddings.
    Recommended model: nomic-embed-text (high quality, 768 dims)

    Usage:
        # Pull model first: ollama pull nomic-embed-text
        provider = OllamaEmbedding(model="nomic-embed-text")
        embedding = await provider.embed("Hello world")
    """

    # Common model dimensions
    # Note: Dimensions must match the actual model
    KNOWN_DIMENSIONS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
    }

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        dimensions: int | None = None,
        timeout: float = 60.0,
    ):
        """
        Initialize Ollama embedding provider.

        Args:
            base_url: Ollama server URL (default: localhost:11434)
            model: Model name (default: nomic-embed-text)
            dimensions: Override dimensions if not in KNOWN_DIMENSIONS
            timeout: Request timeout in seconds

        Note:
            If dimensions not provided and model not in KNOWN_DIMENSIONS,
            first embed call will fail with clear error message.
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

        # Determine dimensions
        if dimensions is not None:
            self._dimensions = dimensions
        elif model in self.KNOWN_DIMENSIONS:
            self._dimensions = self.KNOWN_DIMENSIONS[model]
        else:
            # Will be detected on first call
            self._dimensions = None

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
            raise

    @property
    def dimensions(self) -> int:
        """
        Return embedding vector dimensions.

        Raises:
            ValueError: If dimensions not known and no embed call made yet
        """
        if self._dimensions is None:
            raise ValueError(
                f"Dimensions unknown for model '{self._model}'. "
                "Provide dimensions explicitly or make an embed call first."
            )
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        """
        Generate embedding for single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        async with self._get_client() as client:
            response = await client.post(
                "/api/embeddings",
                json={
                    "model": self._model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            embedding = data.get("embedding", [])

            # Auto-detect dimensions on first call
            if self._dimensions is None:
                self._dimensions = len(embedding)

            return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Note: Ollama doesn't have native batch API, so this makes
        sequential requests. For large batches, consider using
        asyncio.gather() externally for parallelism.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = []
        async with self._get_client() as client:
            for text in texts:
                response = await client.post(
                    "/api/embeddings",
                    json={
                        "model": self._model,
                        "prompt": text,
                    },
                )
                response.raise_for_status()
                data = response.json()

                embedding = data.get("embedding", [])

                # Auto-detect dimensions on first call
                if self._dimensions is None:
                    self._dimensions = len(embedding)

                embeddings.append(embedding)

        return embeddings

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
