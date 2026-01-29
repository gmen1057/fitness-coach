"""
Embedding providers for vector similarity search.

Available providers:
- OpenAIEmbedding: OpenAI text-embedding-3 models
- OllamaEmbedding: Local Ollama embedding models
"""
from .openai import OpenAIEmbedding
from .ollama import OllamaEmbedding

__all__ = [
    "OpenAIEmbedding",
    "OllamaEmbedding",
]
