"""
OpenAI embedding provider with batch support.

Supports:
- text-embedding-3-small (1536 dims, $0.02/1M tokens)
- text-embedding-3-large (3072 dims, $0.13/1M tokens)
- Batch processing for efficiency

Optional dependency - requires `pip install fitness-coach[openai]`
"""
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None  # type: ignore[misc,assignment]

from ..protocols import EmbeddingProvider


class OpenAIEmbedding(EmbeddingProvider):
    """
    OpenAI text-embedding-3 provider.

    Uses Ada-002 successor models with better performance and lower cost.
    Automatically handles batching for efficiency.
    """

    # Model dimensions mapping
    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,  # Legacy model
    }

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
    ):
        """
        Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key
            model: Model name (default: text-embedding-3-small)

        Raises:
            ImportError: If openai package is not installed
            ValueError: If model is not supported
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI not installed. Run: pip install fitness-coach[openai]"
            )

        if model not in self.DIMENSIONS:
            raise ValueError(
                f"Unsupported model: {model}. "
                f"Available: {list(self.DIMENSIONS.keys())}"
            )

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @property
    def dimensions(self) -> int:
        """Return embedding vector dimensions for current model."""
        return self.DIMENSIONS[self._model]

    async def embed(self, text: str) -> list[float]:
        """
        Generate embedding for single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        OpenAI API supports batching up to 2048 inputs per request.
        This method automatically handles large batches.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # OpenAI supports up to 2048 inputs per request
        batch_size = 2048
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            response = await self._client.embeddings.create(
                model=self._model,
                input=batch,
            )

            # Extract embeddings in correct order
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def close(self) -> None:
        """Close the OpenAI client."""
        await self._client.close()
