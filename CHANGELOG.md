# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-29

### Added
- **AI Fitness Coach** - Multi-provider support (Claude, GPT, Ollama)
- **Workout Plans** - Create, edit, track workout programs
- **PWA Support** - Installable on mobile, offline capable
- **RAG Memory** - Semantic search for workout history (optional)
- **Graph Knowledge** - Exercise relationships and progressions (optional)
- **27 AI Tools** - Comprehensive fitness management capabilities
- **Parallel Execution** - Concurrent tool processing for speed
- **SSE Streaming** - Real-time AI responses

### Providers
- Anthropic Claude (Sonnet 4, Opus 4.5, Haiku)
- OpenAI GPT (GPT-4o, GPT-4-turbo)
- Ollama (local, free)

### Stack
- Backend: FastAPI + SQLAlchemy 2.0 + PostgreSQL
- Frontend: Next.js 16 + React 19 + Tailwind CSS
- AI: Provider abstraction layer with tool use
- RAG: pgvector + OpenAI/Ollama embeddings
- Graph: NetworkX (in-memory) or Neo4j

### Security
- Rate limiting enabled
- CORS configurable
- No hardcoded secrets
- Environment-based configuration
