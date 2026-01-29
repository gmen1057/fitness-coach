"""
Embedding providers for vector similarity search.

Available providers:
- OpenAIEmbedding: OpenAI text-embedding-3 models
- OllamaEmbedding: Local Ollama embedding models
"""
from .ollama import OllamaEmbedding
from .openai import OpenAIEmbedding

__all__ = [
    "OpenAIEmbedding",
    "OllamaEmbedding",
]
