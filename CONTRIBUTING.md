# Contributing to Fitness Coach AI

Thank you for your interest in contributing. This guide covers how to report issues, suggest features, and submit code changes.

## Reporting Bugs

1. **Search existing issues** to avoid duplicates
2. **Use the bug report template** when creating a new issue
3. **Include:**
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (OS, Python/Node version, AI provider)
   - Relevant logs or error messages

## Suggesting Features

1. **Check the roadmap** in the main README
2. **Open a feature request issue** with:
   - Clear description of the feature
   - Use case and motivation
   - Proposed implementation (optional)

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Docker (optional, for containerized development)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[all,dev]"
cp .env.example .env
# Configure your .env file
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# With coverage
pytest --cov=app --cov-report=html

# Frontend linting
cd frontend
npm run lint
```

## Code Style

### Python (Backend)

We use **ruff** for linting and formatting:

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

Configuration is in `pyproject.toml`.

### TypeScript (Frontend)

We use **ESLint** for linting:

```bash
npm run lint
```

Configuration is in `.eslintrc.json`.

### General Guidelines

- Write clear, descriptive commit messages
- Add docstrings to public functions
- Include type hints (Python) and TypeScript types
- Keep functions focused and small
- Write tests for new functionality

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the code style guidelines
4. **Test** your changes locally
5. **Commit** with a descriptive message:
   ```bash
   git commit -m "feat: add workout reminder notifications"
   ```
6. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** with:
   - Clear title and description
   - Reference to related issues
   - Screenshots for UI changes

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## Adding New AI Providers

To add support for a new AI provider:

1. **Create provider class** in `backend/app/providers/ai/`:

```python
# backend/app/providers/ai/my_provider.py
from ..protocols import AIProvider

class MyProvider(AIProvider):
    async def chat(self, messages: list, tools: list | None = None):
        # Implementation
        pass

    async def chat_stream(self, messages: list, tools: list | None = None):
        # Streaming implementation
        pass
```

2. **Register provider** in `backend/app/providers/ai/__init__.py`

3. **Add configuration** to `backend/app/config.py`:

```python
MY_PROVIDER_API_KEY: str | None = None
MY_PROVIDER_MODEL: str = "default-model"
```

4. **Update factory** in `backend/app/providers/factory.py`

5. **Add environment variables** to `.env.example`:

```env
MY_PROVIDER_API_KEY=
MY_PROVIDER_MODEL=default-model
```

6. **Update requirements** if new dependencies are needed:
   - Add to `requirements/cloud.txt` or create `requirements/my_provider.txt`
   - Update `pyproject.toml` optional dependencies

7. **Add tests** in `backend/tests/providers/`

8. **Update documentation** in `backend/README.md`

## Questions?

- Open a [GitHub Discussion](https://github.com/yourusername/fitness-coach/discussions)
- Check existing issues and documentation

Thank you for contributing.
