# Fitness Coach Backend

Open-source AI fitness coach API with multi-provider support (Anthropic Claude, OpenAI GPT, Ollama).

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 14+
- One of:
  - Anthropic API key (recommended)
  - OpenAI API key
  - Ollama installed locally (free)

### 2. Installation

```bash
# Clone repository
git clone https://github.com/yourusername/fitness-coach.git
cd fitness-coach/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (choose one)
pip install -e ".[cloud]"    # Anthropic + OpenAI + pgvector
pip install -e ".[local]"    # Ollama only
pip install -e ".[all]"      # All providers
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimum required:**
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/fitness_coach

# Choose ONE provider:
FITNESS_GEMINI_API_KEY=AIzaSy...    # OR
ANTHROPIC_API_KEY=sk-ant-api03-xxx  # OR
OPENAI_API_KEY=sk-proj-xxx          # OR
OLLAMA_BASE_URL=http://localhost:11434
```

### 4. Database Setup

```bash
# Create database
createdb fitness_coach

# Run migrations
alembic upgrade head
```

### 5. Run Server

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Enable RAG (Semantic Memory)

RAG allows the AI coach to remember your workout history, preferences, and insights using semantic search.

### Option A: Ollama (Free, Local, No API Keys)

1. **Install Ollama**
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Pull embedding model**
   ```bash
   ollama pull nomic-embed-text
   ```

3. **Enable pgvector extension**
   ```bash
   sudo -u postgres psql fitness_coach -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

4. **Configure .env**
   ```env
   FITNESS_RAG_PROVIDER=pgvector
   FITNESS_EMBEDDING_PROVIDER=ollama
   FITNESS_OLLAMA_BASE_URL=http://localhost:11434
   ```

5. **Run migrations**
   ```bash
   alembic upgrade head
   ```

6. **Verify**
   ```bash
   curl http://localhost:8450/api/health/rag
   # Should return: {"status": "healthy", ...}
   ```

### Option B: OpenAI Embeddings (Paid, Cloud)

1. **Get API key** from https://platform.openai.com/api-keys

2. **Enable pgvector extension**
   ```bash
   sudo -u postgres psql fitness_coach -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

3. **Configure .env**
   ```env
   FITNESS_RAG_PROVIDER=pgvector
   FITNESS_EMBEDDING_PROVIDER=openai
   FITNESS_OPENAI_API_KEY=sk-your-key-here
   ```

4. **Run migrations & verify**
   ```bash
   alembic upgrade head
   curl http://localhost:8450/api/health/rag
   ```

### Troubleshooting

| Error | Solution |
|-------|----------|
| "pgvector extension not found" | Run: `CREATE EXTENSION IF NOT EXISTS vector;` |
| "Ollama connection refused" | Start Ollama: `ollama serve` |
| "OpenAI API key invalid" | Check FITNESS_OPENAI_API_KEY in .env |

## AI Provider Configuration

### Google Gemini (Recommended for speed and reasoning)

**Best for:** Production use, fast response time, cost-effective reasoning.

**Setup:**
1. Get API key: https://aistudio.google.com/
2. Configure:
```env
FITNESS_GEMINI_API_KEY=AIzaSy...
FITNESS_GEMINI_MODEL=gemini-2.5-flash
```

**Models:**
- `gemini-2.5-flash` - Fast, cheap, and capable of complex tool calls (Default)
- `gemini-2.5-pro` - High intelligence, recommended for complex workouts
- `gemini-1.5-pro` - Legacy reasoning model

**Cost estimate:** ~$0.005-0.02 per coaching session

---

### Anthropic Claude (Recommended)

**Best for:** Quality coaching, reasoning, safety

**Setup:**
1. Get API key: https://console.anthropic.com/
2. Configure:
```env
ANTHROPIC_API_KEY=sk-ant-api03-xxx
ANTHROPIC_MODEL=claude-sonnet-4-5
```

**Models:**
- `claude-opus-4-5` - Best quality ($5/$25 per 1M tokens)
- `claude-sonnet-4-5` - Balanced ($3/$15 per 1M tokens)
- `claude-haiku-4-5` - Fast & cheap ($1/$5 per 1M tokens)

**Cost estimate:** ~$0.01-0.05 per coaching session

---

### OpenAI GPT

**Best for:** Broad availability, structured outputs

**Setup:**
1. Get API key: https://platform.openai.com/
2. Configure:
```env
OPENAI_API_KEY=sk-proj-xxx
OPENAI_MODEL=gpt-4o-mini
```

**Models:**
- `gpt-4.1` - Code-focused, 1M context ($2/$8 per 1M tokens)
- `gpt-5.2` - Complex reasoning ($1.75/$14 per 1M tokens)
- `gpt-4o-mini` - Affordable ($0.15/$0.60 per 1M tokens)

**Cost estimate:** ~$0.005-0.02 per coaching session

---

### Ollama (Free, Self-Hosted)

**Best for:** Privacy, cost control, offline use

**Setup:**
1. Install Ollama: https://ollama.com/download
2. Pull a model:
```bash
ollama pull llama3.3     # 8B params, 5GB
ollama pull qwen2.5      # 7B params, 4.7GB
ollama pull deepseek-r1  # 7B params, reasoning
```

3. Configure:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.3
```

**Requirements:**
- RAM: 8GB+ (16GB recommended)
- Storage: 5-10GB per model
- GPU: Optional but 10x faster

**Cost:** Free (electricity + hardware)

---

### Multi-Provider Fallback

Configure multiple providers for automatic fallback:

```env
# Priority: Anthropic → OpenAI → Ollama
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-proj-xxx
OLLAMA_BASE_URL=http://localhost:11434
```

If Anthropic fails, tries OpenAI. If OpenAI fails, tries Ollama.

## Docker Deployment

### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Manual Docker Build

```bash
# Build image
docker build -t fitness-coach:latest .

# Run container
docker run -d \
  --name fitness-coach \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db/fitness \
  -e ANTHROPIC_API_KEY=sk-ant-xxx \
  fitness-coach:latest
```

## API Overview

### Authentication

Single-user mode (default): No auth required, uses `DEFAULT_USER_ID` from `.env`

Multi-user mode: Add `X-User-ID` header with UUID

### Core Endpoints

#### Workout Plans

```bash
# List plans
GET /api/fitness/plans

# Get plan details
GET /api/fitness/plans/{plan_id}

# Get current workout
GET /api/fitness/plans/{plan_id}/current

# Create plan
POST /api/fitness/plans
{
  "name": "Beginner Full Body",
  "goal": "Build strength",
  "weeks_count": 8
}
```

#### Workout Logging

```bash
# Complete workout day
POST /api/fitness/workouts/complete-day
{
  "plan_id": "uuid",
  "week_number": 1,
  "day_number": 1
}

# Get statistics
GET /api/fitness/workouts/stats
```

#### AI Chat

```bash
# Streaming chat (SSE)
POST /api/fitness/chat
Content-Type: application/json
Accept: text/event-stream
{
  "message": "Create me a 4-week beginner workout plan",
  "stream": true
}

# Non-streaming
POST /api/fitness/chat/simple
{
  "message": "Show my progress this week"
}

# Chat history
GET /api/fitness/chat/history?limit=50
```

#### Training Programs

```bash
# List available programs
GET /api/fitness/programs

# Get program details
GET /api/fitness/programs/{program_id}
```

### Event Stream Format

Chat endpoint returns Server-Sent Events:

```
event: content
data: {"content": "I'll create a plan for you..."}

event: tool_start
data: {"tool": "create_workout_plan", "input": {...}}

event: tool_result
data: {"result": {...}}

event: content
data: {"content": "Done! Your plan is ready."}

event: done
data: {"status": "completed"}
```

## Available AI Tools

The coach has access to these tools:

| Tool | Description |
|------|-------------|
| `get_workout_plans` | List user's workout plans |
| `get_current_workout` | Get today's scheduled workout |
| `get_workout_stats` | Get progress statistics |
| `complete_workout_day` | Mark workout day as completed |
| `skip_workout_day` | Skip workout with reason |
| `add_exercise_note` | Add notes to specific exercise |
| `create_workout_plan` | Create new structured workout plan |
| `edit_workout_plan` | Modify existing plan |
| `get_programs` | List training programs library |
| `create_program` | Create reusable program template |

## Development

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_chat.py -v
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy app/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

### Adding New AI Provider

1. Create provider class in `app/services/providers/`:
```python
from .base import BaseProvider

class MyProvider(BaseProvider):
    async def chat_stream(self, messages, tools):
        # Implementation
```

2. Register in `app/services/ai_router.py`:
```python
from .providers.my_provider import MyProvider

providers = [
    AnthropicProvider(),
    OpenAIProvider(),
    MyProvider(),  # Add here
]
```

3. Add settings to `app/config.py`
4. Update `.env.example` with configuration

## Architecture

```
app/
├── main.py                  # FastAPI application
├── config.py                # Settings management
├── db.py                    # Database session
├── api/
│   └── fitness/             # Fitness endpoints
│       ├── chat.py          # AI chat (SSE)
│       ├── plans.py         # Workout plans CRUD
│       ├── workouts.py      # Workout logging
│       └── programs.py      # Training programs
├── models/
│   └── fitness/             # SQLAlchemy models
│       └── workout_plan.py  # WorkoutPlan, PlanWeek, PlanDay, DayExercise
├── services/
│   ├── ai_router.py         # Multi-provider routing
│   ├── fitness_agent.py     # AI coaching logic
│   ├── mcp_tools.py         # Tool definitions
│   ├── plan_navigator.py    # Plan context builder
│   └── providers/           # AI provider implementations
│       ├── base.py
│       ├── anthropic_provider.py
│       ├── openai_provider.py
│       └── ollama_provider.py
└── schemas/                 # Pydantic models
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | No | - | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-5` | Claude model name |
| `OPENAI_API_KEY` | No | - | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | GPT model name |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llama3.3` | Ollama model name |
| `USE_SEMANTIC_MEMORY` | No | `false` | Enable pgvector memory |
| `RATE_LIMIT_ENABLED` | No | `true` | Enable rate limiting |
| `CORS_ORIGINS` | No | `*` | Allowed CORS origins |
| `DEFAULT_USER_ID` | No | Auto-generated | Default user UUID |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |

See `.env.example` for complete reference.

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
systemctl status postgresql

# Check connection string
psql "postgresql://user:pass@localhost/fitness_coach"

# Check asyncpg installed
pip install asyncpg
```

### Anthropic API Error

```bash
# Verify API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'

# Check model name is correct (claude-sonnet-4-5, not claude-sonnet-4-5-20250929)
```

### OpenAI API Error

```bash
# Verify API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check model availability
# Note: gpt-5.x may require waitlist access
```

### Ollama Connection Failed

```bash
# Check Ollama is running
ollama list

# Test API
curl http://localhost:11434/api/tags

# Pull model if missing
ollama pull llama3.3
```

### Import Errors

```bash
# Reinstall with correct extras
pip install -e ".[cloud]"  # For Anthropic/OpenAI
pip install -e ".[all]"    # For all providers

# Check installed packages
pip list | grep -E "anthropic|openai|ollama"
```

## Performance Tuning

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_workout_plan_user_active ON workout_plans(user_id, is_active);
CREATE INDEX idx_plan_day_status ON plan_days(status, date);
CREATE INDEX idx_chat_messages_user ON chat_messages(user_id, created_at DESC);
```

### Connection Pooling

```env
# Increase pool size for high traffic
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/fitness?pool_size=20&max_overflow=10
```

### Response Caching

Enable HTTP caching for static endpoints:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

# In main.py
FastAPICache.init(RedisBackend(redis), prefix="fitness-cache")
```

## Security Considerations

1. **API Keys**: Never commit `.env` to git
2. **CORS**: Restrict origins in production
3. **Rate Limiting**: Enable to prevent abuse
4. **SQL Injection**: Use SQLAlchemy parameters (automatic)
5. **Input Validation**: Pydantic schemas validate all inputs

## License

MIT License - see LICENSE file for details.

## Contributing

See CONTRIBUTING.md for guidelines.

## Support

- GitHub Issues: https://github.com/yourusername/fitness-coach/issues
- Documentation: https://github.com/yourusername/fitness-coach/wiki
- Discord: https://discord.gg/fitness-coach

## Roadmap

- [ ] Nutrition tracking
- [ ] Exercise video library
- [ ] Mobile app (React Native)
- [ ] Workout analytics dashboard
- [ ] Social features (share workouts)
- [ ] Integration with fitness trackers
