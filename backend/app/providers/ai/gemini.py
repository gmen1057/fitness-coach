"""
Google Gemini AI provider with Extended Thinking and tool calling support.

Supports:
- Gemini 2.0 Flash, 2.5 Flash, 2.5 Pro
- Extended Thinking (thinking_budget)
- Tool/function calling
- Streaming responses with manual function-calling roundtrips
"""
import json
import logging
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from ..protocols import AIProvider, CompletionChunk, Message, ToolCall

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """
    Google Gemini provider implementing the AIProvider protocol.

    Preserves state across tool calls to satisfy Gemini's thought_signature requirement.
    """

    THINKING_MODELS = {"gemini-2.0", "gemini-2.5"}

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        thinking_budget: int = -1,  # -1 = automatic
        vertexai: bool = False,
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Gemini API key
            model: Model name (default: gemini-2.5-flash)
            thinking_budget: Thinking token budget (-1 for auto, 0 to disable, or >0)
            vertexai: Whether to use Vertex AI backend
        """
        self._client = genai.Client(api_key=api_key, vertexai=vertexai)
        self._model = model
        self._thinking_budget = thinking_budget

        # Keep state for active chat session to handle consecutive tool calls properly
        self._current_chat = None
        self._tool_calls_names: dict[str, str] = {}

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_tools(self) -> bool:
        return True

    @property
    def supports_thinking(self) -> bool:
        """Check if model supports extended thinking."""
        return any(m in self._model for m in self.THINKING_MODELS)

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> str:
        """Non-streaming chat completion."""
        # Fallback to streaming and accumulating text
        text_parts = []
        async for chunk in self.chat_stream(messages, tools, system):
            if chunk.type == "text" and chunk.content:
                text_parts.append(chunk.content)
        return "".join(text_parts)

    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        """
        Streaming chat completion with thinking and tool support.

        Yields chunks of type:
        - "thinking": Extended thinking content
        - "text": Regular response text
        - "tool_use": Tool call started
        - "done": Stream complete
        """
        is_continuation = False
        if messages and isinstance(messages[-1].content, list) and len(messages[-1].content) > 0:
            is_continuation = messages[-1].content[0].get("type") == "tool_result"

        try:
            if not is_continuation:
                # Reset state for a new conversational turn
                self._current_chat = None
                self._tool_calls_names.clear()

                # Build clean history (skip past tool uses/results to avoid thought_signature errors)
                gemini_history = []
                for msg in messages[:-1]:
                    role = "user" if msg.role == "user" else "model"

                    if isinstance(msg.content, list):
                        # Extract only text parts from structured content
                        text_parts = [
                            b["text"] for b in msg.content
                            if b.get("type") == "text" and b.get("text")
                        ]
                        content_str = "\n".join(text_parts) if text_parts else ""
                    else:
                        content_str = msg.content

                    if not content_str.strip():
                        continue

                    # Ensure role alternation
                    if gemini_history and gemini_history[-1].role == role:
                        gemini_history[-1].parts[0].text += f"\n\n{content_str}"
                    else:
                        gemini_history.append(
                            types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=content_str)]
                            )
                        )

                # Configure model options
                gemini_tools = self._convert_tools(tools) if tools else None
                config_kwargs = {
                    "system_instruction": system,
                    "tools": gemini_tools,
                    "temperature": 0.7,
                    "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
                }

                if self.supports_thinking:
                    config_kwargs["thinking_config"] = types.ThinkingConfig(
                        thinking_budget=self._thinking_budget,
                        include_thoughts=True,
                    )

                config = types.GenerateContentConfig(**config_kwargs)

                # Start new chat session
                self._current_chat = self._client.aio.chats.create(
                    model=self._model,
                    config=config,
                    history=gemini_history
                )
                next_input = messages[-1].content
            else:
                # Continue previous chat session with function responses
                if not self._current_chat:
                    raise RuntimeError("Received tool results but no active chat session is found")

                response_parts = []
                for block in messages[-1].content:
                    if block.get("type") == "tool_result":
                        tid = block["tool_use_id"]
                        tool_name = self._tool_calls_names.get(tid, "tool")

                        try:
                            res_data = json.loads(block["content"])
                        except Exception:
                            res_data = {"result": block["content"]}

                        if not isinstance(res_data, dict):
                            res_data = {"result": res_data}

                        response_parts.append(
                            types.Part(
                                function_response=types.FunctionResponse(
                                    id=tid,
                                    name=tool_name,
                                    response=res_data,
                                )
                            )
                        )
                next_input = response_parts

            # Run stream
            stream = await self._current_chat.send_message_stream(next_input)
            async for chunk in stream:
                if chunk.candidates:
                    for candidate in chunk.candidates:
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                # Thoughts block
                                if getattr(part, "thought", False) and part.text:
                                    yield CompletionChunk(type="thinking", content=part.text)
                                # Tool call block
                                elif getattr(part, "function_call", None):
                                    fc = part.function_call
                                    # Save tool name so we can map it back in function response
                                    self._tool_calls_names[fc.id] = fc.name
                                    yield CompletionChunk(
                                        type="tool_use",
                                        tool_call=ToolCall(
                                            id=fc.id,
                                            name=fc.name,
                                            arguments=dict(fc.args) if fc.args else {},
                                        )
                                    )
                                # Plain text block
                                elif part.text:
                                    yield CompletionChunk(type="text", content=part.text)

            yield CompletionChunk(type="done")

        except Exception as e:
            logger.error(f"GeminiProvider stream error: {e}", exc_info=True)
            yield CompletionChunk(type="error", content=str(e))

    async def close(self) -> None:
        """Close the client."""
        # google-genai client doesn't require explicit close
        pass

    def _convert_tools(self, tools: list[dict]) -> list[types.Tool]:
        """Convert universal tool format to Gemini SDK tool format."""
        functions = []
        for t in tools:
            # Reconstruct parameter definitions into schema
            params = t.get("parameters", {})
            properties = {}
            for name, prop in params.get("properties", {}).items():
                p_type = prop.get("type", "string").upper()
                # Translate basic types
                if p_type == "INTEGER":
                    t_type = types.Type.INTEGER
                elif p_type == "NUMBER":
                    t_type = types.Type.NUMBER
                elif p_type == "BOOLEAN":
                    t_type = types.Type.BOOLEAN
                elif p_type == "ARRAY":
                    t_type = types.Type.ARRAY
                elif p_type == "OBJECT":
                    t_type = types.Type.OBJECT
                else:
                    t_type = types.Type.STRING

                schema_kwargs = {
                    "type": t_type,
                    "description": prop.get("description", ""),
                }

                # Handle nested items for array
                if t_type == types.Type.ARRAY and "items" in prop:
                    items_prop = prop["items"]
                    ip_type = items_prop.get("type", "string").upper()
                    if ip_type == "OBJECT":
                        # Simplification for complex object structures
                        nested_props = {}
                        for n_name, n_prop in items_prop.get("properties", {}).items():
                            nested_props[n_name] = types.Schema(
                                type=types.Type.STRING,  # Fallback to string for nested items
                                description=n_prop.get("description", "")
                            )
                        schema_kwargs["items"] = types.Schema(
                            type=types.Type.OBJECT,
                            properties=nested_props
                        )
                    else:
                        schema_kwargs["items"] = types.Schema(
                            type=types.Type.STRING,  # Fallback to string
                        )

                properties[name] = types.Schema(**schema_kwargs)

            functions.append(
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties=properties,
                        required=params.get("required", []),
                    )
                )
            )

        return [types.Tool(function_declarations=functions)]
