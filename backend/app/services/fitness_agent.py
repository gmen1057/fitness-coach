"""
Provider-agnostic fitness AI agent.

This agent works with any AI provider through the abstraction layer.
Implements manual agentic loop (not SDK-specific) for tool calling.

Features:
- Multi-turn tool execution (max 10 turns)
- Streaming and non-streaming modes
- Plan context injection via plan_navigator
- Works with providers that support tools AND those that don't
- Parallel tool execution for better performance
"""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers import CompletionChunk, Message, get_ai_provider
from app.services.plan_navigator import get_plan_navigation
from app.services.streaming import SSEFormatter
from app.services.tools import TOOLS, ToolExecutor

logger = logging.getLogger(__name__)


# System prompt for fitness coaching
SYSTEM_PROMPT = """Ты мой персональный консультант по физическому здоровью и форме.

## Кто ты
Опытный специалист по фитнесу, здоровью и телу. Помогаешь мне:
- Тренироваться эффективно и безопасно
- Поддерживать физическую форму
- Разбираться в вопросах здоровья, связанных с телом и движением
- Планировать тренировки и отслеживать прогресс
- Учитывать показатели здоровья (анализы крови, вес тела) и ограничения (травмы) при планировании нагрузок

## Стиль
- Отвечай на русском
- По делу, без воды
- Конкретные советы, не общие фразы
- Можешь быть неформальным

## Инструменты
У тебя есть инструменты для работы с моими тренировками, весом тела, травмами и анализами крови.
- **Травмы**: Обязательно проверяй ограничения по здоровью (`get_health_profile`) перед тем как назначать или менять упражнения. Никогда не нагружай травмированные зоны.
- **Анализы крови**: Используй `get_blood_markers`, чтобы проверить показатели (гормоны, липиды и др.) перед тем как советовать добавки, диету или делать выводы о перетренированности.
- **Прогресс и Вес**: Отслеживай динамику веса с помощью `get_body_metrics` и записывай новые замеры через `log_body_weight`.
- Всегда используй инструменты, чтобы получить актуальные данные, а не предполагать их.
"""


class FitnessAgent:
    """
    Provider-agnostic fitness coaching agent.

    Works with any AI provider through abstraction layer.
    Implements manual agentic loop for tool execution.
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        """
        Initialize fitness agent.

        Args:
            db: Database session for tool execution
            user_id: User ID for data access
        """
        self.db = db
        self.user_id = user_id
        self.ai = get_ai_provider()
        self.executor = ToolExecutor(db, user_id)
        self.max_turns = 10  # Prevent infinite loops

    async def chat_stream(
        self,
        message: str,
        conversation_history: list[dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response with agentic tool execution.

        Args:
            message: User's message
            conversation_history: Recent conversation (list of {role, content})

        Yields:
            SSE formatted events (text, thinking, tool_start, tool_result, done, error)
        """
        # Build system prompt with plan context
        system = await self._build_system_prompt()

        # Build messages
        messages = []
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append(Message(
                    role=msg["role"],
                    content=msg["content"]
                ))

        messages.append(Message(role="user", content=message))

        # Track usage
        total_usage = {"input_tokens": 0, "output_tokens": 0}

        try:
            # Agentic loop
            for turn in range(self.max_turns):
                logger.info(f"Agent turn {turn + 1}/{self.max_turns}")

                # Check if provider supports tools
                tools = TOOLS if self.ai.supports_tools else None
                if tools:
                    logger.info(f"Provider supports tools, providing {len(tools)} tools")
                else:
                    logger.info("Provider doesn't support tools, using prompt-based approach")

                # Stream response
                full_text = ""
                tool_calls_map = {}  # id -> ToolCall (to handle updates)
                tool_call_order = []  # Track order of tool calls

                async for chunk in self.ai.chat_stream(messages, tools, system):
                    if chunk.type == "text":
                        full_text += chunk.content or ""
                        yield SSEFormatter.text(chunk.content or "")

                    elif chunk.type == "thinking":
                        # Extended Thinking (if provider supports it)
                        yield SSEFormatter.thinking(chunk.content)

                    elif chunk.type == "tool_use":
                        # Tool call - may be start (empty args) or end (full args)
                        if chunk.tool_call:
                            tc = chunk.tool_call
                            if tc.id in tool_calls_map:
                                # Update existing - this is the final call with real args
                                tool_calls_map[tc.id] = tc
                            else:
                                # New tool call
                                tool_calls_map[tc.id] = tc
                                tool_call_order.append(tc.id)
                                yield SSEFormatter.tool_start(tc.name, tc.arguments)

                # Get final tool calls in order
                tool_calls = [tool_calls_map[tid] for tid in tool_call_order]

                # No tool calls - done
                if not tool_calls:
                    logger.info("No tool calls, ending agentic loop")
                    break

                # Execute tools in parallel
                if len(tool_calls) > 1:
                    logger.info(f"Executing {len(tool_calls)} tool calls in parallel")
                else:
                    logger.info(f"Executing {len(tool_calls)} tool call")

                async def execute_tool(tool_call):
                    """Execute single tool and return result with metadata."""
                    result = await self.executor.execute(
                        tool_call.name,
                        tool_call.arguments
                    )
                    return {
                        "tool_call": tool_call,
                        "result": result,
                        "success": "error" not in result
                    }

                # Execute all tools concurrently
                tool_results = await asyncio.gather(
                    *[execute_tool(tc) for tc in tool_calls],
                    return_exceptions=True
                )

                # Process results in order (for consistent message history)
                for tr in tool_results:
                    if isinstance(tr, Exception):
                        logger.error(f"Tool execution failed: {tr}")
                        yield SSEFormatter.tool_result("unknown", {"error": str(tr)}, False)
                        continue

                    tool_call = tr["tool_call"]
                    result = tr["result"]
                    success = tr["success"]

                    # Yield result to client
                    # ToolExecutor returns dict directly (e.g., {"plans": [...]}, {"error": "..."})
                    yield SSEFormatter.tool_result(tool_call.name, result, success)

                    # Add tool use and result to conversation (Anthropic format)
                    # Tool use goes in assistant message
                    messages.append(Message(
                        role="assistant",
                        content=[{
                            "type": "tool_use",
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "input": tool_call.arguments
                        }]
                    ))
                    # Tool result goes in user message
                    messages.append(Message(
                        role="user",
                        content=[{
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": json.dumps(result)  # Must be string
                        }]
                    ))

                # Add assistant's text response to messages (strip to avoid API error)
                if full_text and full_text.strip():
                    messages.append(Message(role="assistant", content=full_text.strip()))

            # Done
            yield SSEFormatter.done(total_usage)

        except Exception as e:
            logger.error(f"Error in chat_stream: {e}", exc_info=True)
            yield SSEFormatter.error(str(e))

    async def chat_simple(self, message: str) -> str:
        """
        Non-streaming chat for simple use cases.

        Args:
            message: User's message

        Returns:
            Full response as string
        """
        # Build system prompt
        system = await self._build_system_prompt()

        # Build messages
        messages = [Message(role="user", content=message)]

        # Check if provider supports tools
        tools = TOOLS if self.ai.supports_tools else None

        # Agentic loop (non-streaming)
        for turn in range(self.max_turns):
            # Get response
            response = await self.ai.chat(messages, tools, system)

            # Check for tool calls (simplified - assumes response contains tool call JSON)
            # In practice, providers return tool calls differently
            # This is a fallback for non-streaming mode

            # For now, just return the response
            return response

        return response

    async def _build_system_prompt(self) -> str:
        """
        Build system prompt with plan context.

        Returns:
            Complete system prompt string
        """
        parts = [SYSTEM_PROMPT]

        # Add plan navigation context
        try:
            nav_context = await get_plan_navigation(self.db, self.user_id)
            if nav_context:
                parts.append(f"---\n{nav_context}")
        except Exception as e:
            logger.error(f"Failed to get plan navigation: {e}")

        full_prompt = "\n".join(parts)
        logger.info(f"System prompt: {len(full_prompt)} chars")
        return full_prompt


# Singleton instance
_fitness_agent = None


def get_fitness_agent(db: AsyncSession, user_id: UUID) -> FitnessAgent:
    """
    Get fitness agent instance.

    Note: Not a true singleton since it requires db/user_id.
    Creates new instance per request.
    """
    return FitnessAgent(db, user_id)
