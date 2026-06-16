# 🏋️ Fitness Coach — AI-Тренер

[English](README.md) | **Русский**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)

Открытый AI фитнес-тренер с поддержкой нескольких провайдеров. Создавайте персонализированные программы тренировок, отслеживайте прогресс и получайте интеллектуальное сопровождение через разговорный интерфейс.

## Возможности

- **Multi-Provider AI**: Выбирайте Google Gemini, Anthropic Claude, OpenAI GPT или self-hosted Ollama
- **27 MCP-инструментов**: Комплексное управление тренировками с параллельным выполнением
- **Графовая база знаний**: Связи упражнений, альтернативы и прогрессии
- **Разговорный коучинг**: Естественный чат с поддержкой рассуждений (Extended Thinking) и вызова инструментов
- **Умное создание планов**: Эффективное создание полного плана одним вызовом инструмента
- **Управление тренировками**: Создавайте, отслеживайте и адаптируйте программы тренировок
- **Отслеживание прогресса**: Статистика, серии и метрики завершения
- **Оффлайн-поддержка**: PWA с кэшированием через service worker
- **Система памяти**: Опциональный RAG для персонализированного долгосрочного контекста
- **Docker Ready**: Готовое к production контейнеризованное развёртывание

![Главный экран](docs/screenshots/home.png)

<details>
<summary>Больше скриншотов</summary>

![AI Чат](docs/screenshots/chat.png)
![Планы тренировок](docs/screenshots/plans.png)

</details>

## Быстрый старт

### 1. Клонирование

```bash
git clone https://github.com/yourusername/fitness-coach.git
cd fitness-coach
```

### 2. Настройка

```bash
cp docker/.env.example docker/.env
# Отредактируйте docker/.env, укажите API-ключ (Anthropic, OpenAI или Ollama)
```

### 3. Запуск

```bash
cd docker && docker compose up -d
```

Откройте http://localhost:8000/docs для документации API.

## Архитектура

```
fitness-coach/
├── backend/                 # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/fitness/     # REST endpoints (plans, workouts, chat)
│   │   ├── models/          # SQLAlchemy модели
│   │   ├── providers/       # AI, embedding, RAG, memory провайдеры
│   │   └── services/        # Бизнес-логика + AI-агент
│   └── requirements/        # Модульные зависимости
├── frontend/                # Next.js 16 PWA
│   ├── src/app/             # App Router страницы
│   ├── src/components/      # React компоненты
│   └── src/stores/          # Zustand state management
└── docker/                  # Docker Compose развёртывание
    ├── docker-compose.yml   # Production конфигурация
    └── docker-compose.dev.yml # Development переопределения
```

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  PostgreSQL │
│  (Next.js)  │     │  (FastAPI)  │     │  + pgvector │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
        ┌────────────┬─────┴──────┬────────────┐
        ▼            ▼            ▼            ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │  Google  │ │ Anthropic│ │  OpenAI  │ │  Ollama  │
  │  Gemini  │ │  Claude  │ │   GPT    │ │  (Local) │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Сравнение AI-провайдеров

| Провайдер | Статус | Подходит для | Стоимость | Приватность | Качество |
|-----------|--------|--------------|-----------|-------------|----------|
| **Google Gemini** | ✅ Поддерживается | Production, рассуждения | $0.075-2.50/1M токенов | Облако | Отличное |
| **Anthropic Claude** | ✅ По умолчанию | Production | $3-15/1M токенов | Облако | Отличное |
| **OpenAI GPT-4o** | ✅ Протестировано | Широкая совместимость | $2.50-10/1M токенов | Облако | Очень хорошее |
| **Ollama** | ✅ Поддерживается | Приватность, оффлайн | Бесплатно (self-hosted) | Полная | Хорошее |

Подробности о настройке провайдеров и доступных моделях см. в [backend/README.md](backend/README.md).

## Основные возможности

**27 MCP-инструментов**, организованных по категориям:
- **Базовые (7)**: Планы, тренировки, статистика, история
- **CRUD (8)**: Создание/редактирование планов, недель, дней, упражнений
- **Пакетные (2)**: `create_full_plan`, `create_full_week` для эффективного создания
- **Графовые (4)**: Альтернативные упражнения, прогрессии, маппинг мышцы-упражнения
- **RAG (2)**: Поиск в памяти тренировок, сохранение инсайтов
- **Статусные (3)**: Завершить, пропустить, добавить заметки
- **Прочие (1)**: Программы тренировок

**Производительность**: Параллельное выполнение инструментов через asyncio.gather для мульти-инструментальных операций.

**База знаний**: Граф на NetworkX или Neo4j для связей упражнений и прогрессий.

## Документация

| Документ | Описание |
|----------|----------|
| [Backend README](backend/README.md) | Настройка API, конфигурация провайдеров, справочник 27 инструментов |
| [Frontend README](frontend/README.md) | Настройка PWA, компоненты, управление состоянием |
| [Docker Guide](docker/README.md) | Контейнерное развёртывание, production конфигурация |
| [Contributing](CONTRIBUTING.md) | Как внести вклад в проект |

## Разработка

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -e ".[all]"
cp .env.example .env
# Отредактируйте .env с вашими настройками
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

## Вклад в проект

Мы приветствуем вклад в проект. См. [CONTRIBUTING.md](CONTRIBUTING.md) для инструкций.

## Лицензия

MIT License — подробности в [LICENSE](LICENSE).
