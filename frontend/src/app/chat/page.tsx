"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { BottomNav } from "@/components/BottomNav";
import { ToolCallBlock } from "@/components/ToolCallBlock";
import { TypingIndicator } from "@/components/TypingIndicator";
import { sseClient, API_BASE, type StreamChunk } from "@/lib/api";
import {
  ArrowLeft,
  Send,
  Loader2,
  Bot,
  User,
  Trash2,
  Sparkles,
} from "lucide-react";
import { clsx } from "clsx";

interface ToolCall {
  id: string;
  tool: string;
  input?: Record<string, unknown>;
  result?: unknown;
  success?: boolean;
  isLoading: boolean;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [showTypingIndicator, setShowTypingIndicator] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load chat history on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/fitness/chat/history?limit=50`);
        if (response.ok) {
          const data = await response.json();
          if (data.messages && data.messages.length > 0) {
            // API returns newest-first, we need oldest-first (chronological)
            const chronological = [...data.messages].reverse();
            setMessages(
              chronological.map((msg: { id: string; role: "user" | "assistant"; content: string }) => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                isStreaming: false,
                toolCalls: [],
              }))
            );
          }
        }
      } catch (error) {
        console.error("Failed to load chat history:", error);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadHistory();
  }, []);

  // Scroll to bottom - instant for initial load, smooth for new messages
  const scrollToBottom = useCallback((instant = true) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({
            behavior: instant ? "instant" : "smooth",
            block: "end",
          });
        }
      });
    });
  }, []);

  // Scroll when messages change
  useEffect(() => {
    if (messages.length > 0 && !isLoadingHistory) {
      scrollToBottom(false);
    }
  }, [messages, scrollToBottom, isLoadingHistory]);

  // Scroll after history loads
  useEffect(() => {
    if (!isLoadingHistory && messages.length > 0) {
      scrollToBottom(true);
      setTimeout(() => scrollToBottom(true), 100);
      setTimeout(() => scrollToBottom(true), 300);
    }
  }, [isLoadingHistory, messages.length, scrollToBottom]);

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  };

  // Send message
  const handleSend = async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmedInput,
      toolCalls: [],
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setShowTypingIndicator(true);

    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }

    const assistantId = `assistant-${Date.now()}`;
    const assistantMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      isStreaming: true,
      toolCalls: [],
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      await sseClient.streamChat(
        trimmedInput,
        null,
        (chunk: StreamChunk) => {
          if (chunk.type === "content" || chunk.type === "tool_start") {
            setShowTypingIndicator(false);
          }

          if (chunk.type === "content" && chunk.content) {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: msg.content + chunk.content }
                  : msg
              )
            );
          }

          if (chunk.type === "tool_start" && chunk.tool) {
            const toolCall: ToolCall = {
              id: `tool-${Date.now()}-${chunk.tool}`,
              tool: chunk.tool,
              input: chunk.toolInput,
              isLoading: true,
            };

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, toolCalls: [...(msg.toolCalls || []), toolCall] }
                  : msg
              )
            );
          }

          if (chunk.type === "tool_result" && chunk.tool) {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      toolCalls: (msg.toolCalls || []).map((tc) =>
                        tc.tool === chunk.tool && tc.isLoading
                          ? {
                              ...tc,
                              result: chunk.toolResult,
                              success: chunk.toolSuccess,
                              isLoading: false,
                            }
                          : tc
                      ),
                    }
                  : msg
              )
            );
          }

          if (chunk.type === "done") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, isStreaming: false }
                  : msg
              )
            );
            setIsLoading(false);
            setShowTypingIndicator(false);
          }

          if (chunk.type === "error") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      content: chunk.error || "An error occurred",
                      isStreaming: false,
                    }
                  : msg
              )
            );
            setIsLoading(false);
            setShowTypingIndicator(false);
          }
        },
        (error) => {
          setShowTypingIndicator(false);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? {
                    ...msg,
                    content: msg.content || `Error: ${error.message}`,
                    isStreaming: false,
                  }
                : msg
            )
          );
          setIsLoading(false);
        }
      );
    } catch (error) {
      setShowTypingIndicator(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                content: msg.content || `Error: ${(error as Error).message}`,
                isStreaming: false,
              }
            : msg
        )
      );
      setIsLoading(false);
    }
  };

  // Handle keyboard submit
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Clear chat
  const handleClearChat = async () => {
    if (messages.length === 0) return;
    if (confirm("Clear chat history?")) {
      try {
        await fetch(`${API_BASE}/api/fitness/chat/history`, {
          method: "DELETE",
        });
      } catch (error) {
        console.error("Failed to clear history:", error);
      }
      setMessages([]);
    }
  };

  // Go back
  const handleBack = () => {
    router.push("/");
  };

  // Quick suggestions
  const suggestions = [
    "Show my current workout",
    "What exercises are today?",
    "My progress this week",
    "Create a new plan",
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg border-b border-gray-100 dark:border-gray-800">
        <div className="px-4 py-3 flex items-center gap-3">
          <button
            onClick={handleBack}
            className="p-2 -ml-2 rounded-xl min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Go back"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h1 className="font-semibold text-gray-900 dark:text-white">
                AI Trainer
              </h1>
              <Sparkles className="w-4 h-4 text-fitness" />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Personal fitness assistant
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="p-2 rounded-xl min-h-[44px] min-w-[44px] flex items-center justify-center text-gray-400 hover:text-red-500 transition-colors"
              aria-label="Clear chat"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          )}
        </div>
      </header>

      {/* Messages */}
      <main ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-4 pb-52 scrollbar-hide">
        {/* Loading history */}
        {isLoadingHistory && (
          <div className="flex items-center justify-center h-full min-h-[300px]">
            <Loader2 className="w-8 h-8 text-fitness animate-spin" />
          </div>
        )}

        {/* Welcome message */}
        {!isLoadingHistory && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center">
            <div className="w-20 h-20 bg-gradient-to-br from-fitness/20 to-fitness/5 rounded-3xl flex items-center justify-center mb-4">
              <Bot className="w-10 h-10 text-fitness" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              AI Fitness Trainer
            </h2>
            <p className="text-gray-500 dark:text-gray-400 mt-2 max-w-xs">
              Ask me about workouts, exercises, nutrition, or your fitness goals.
            </p>
            <div className="flex flex-wrap justify-center gap-2 mt-6 max-w-sm">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-700 dark:text-gray-300 hover:border-fitness/50 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {!isLoadingHistory && messages.length > 0 && (
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={clsx(
                  "flex gap-3 animate-fade-in",
                  message.role === "user" ? "flex-row-reverse" : ""
                )}
              >
                {/* Avatar */}
                <div
                  className={clsx(
                    "flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center",
                    message.role === "user"
                      ? "bg-gradient-to-br from-fitness to-fitness-dark text-white"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
                  )}
                >
                  {message.role === "user" ? (
                    <User className="w-4 h-4" />
                  ) : (
                    <Bot className="w-4 h-4" />
                  )}
                </div>

                {/* Message bubble */}
                <div
                  className={clsx(
                    "max-w-[85%] rounded-2xl",
                    message.role === "user"
                      ? "bg-gradient-to-br from-fitness to-fitness-dark text-white rounded-tr-md px-4 py-3"
                      : "bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-tl-md border border-gray-100 dark:border-gray-700 shadow-sm"
                  )}
                >
                  {/* Tool calls */}
                  {message.role === "assistant" && message.toolCalls && message.toolCalls.length > 0 && (
                    <div className="px-3 pt-3">
                      {message.toolCalls.map((toolCall) => (
                        <ToolCallBlock
                          key={toolCall.id}
                          toolName={toolCall.tool}
                          input={toolCall.input}
                          result={toolCall.result}
                          success={toolCall.success}
                          isLoading={toolCall.isLoading}
                        />
                      ))}
                    </div>
                  )}

                  {/* Content */}
                  {message.role === "assistant" ? (
                    <div className="px-4 py-3">
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                        {message.isStreaming && (
                          <span className="inline-block w-0.5 h-4 bg-fitness ml-0.5 animate-pulse" />
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap break-words">
                      {message.content}
                    </p>
                  )}
                </div>
              </div>
            ))}

            {showTypingIndicator && <TypingIndicator label="Thinking..." />}
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* Input area */}
      <div className="fixed bottom-24 left-0 right-0 bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl border-t border-gray-100/50 dark:border-gray-800/50 p-4">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask AI trainer..."
              rows={1}
              className={clsx(
                "w-full px-4 py-3 bg-gray-100 dark:bg-gray-800",
                "border border-transparent rounded-2xl resize-none",
                "focus:border-fitness focus:ring-2 focus:ring-fitness/20 outline-none",
                "text-gray-900 dark:text-white placeholder-gray-400",
                "transition-all max-h-[120px]"
              )}
            />
          </div>

          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className={clsx(
              "flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all",
              input.trim() && !isLoading
                ? "bg-gradient-to-br from-fitness to-fitness-dark text-white active:scale-95 shadow-sm shadow-fitness/30"
                : "bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed"
            )}
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
