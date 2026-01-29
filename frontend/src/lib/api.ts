// API Configuration
// Set NEXT_PUBLIC_API_URL in .env.local for development
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// Type definitions for API responses
export interface ApiError {
  error: string;
  detail?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  message: ChatMessage;
  conversation_id: string;
}

export interface StreamChunk {
  type: "content" | "done" | "error" | "tool_start" | "tool_result" | "thinking";
  content?: string;
  error?: string;
  tool?: string;
  toolInput?: Record<string, unknown>;
  toolResult?: unknown;
  toolSuccess?: boolean;
}

// SWR Fetcher
export const fetcher = async <T>(url: string): Promise<T> => {
  const response = await fetch(`${API_BASE}${url}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Request failed" }));
    throw new Error(error.error || error.detail || "Request failed");
  }

  return response.json();
};

// POST request helper
export const postData = async <T, R>(url: string, data: T): Promise<R> => {
  const response = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Request failed" }));
    throw new Error(error.error || error.detail || "Request failed");
  }

  return response.json();
};

// SSE Client for chat streaming
export class SSEClient {
  private eventSource: EventSource | null = null;
  private abortController: AbortController | null = null;

  async streamChat(
    message: string,
    conversationId: string | null,
    onChunk: (chunk: StreamChunk) => void,
    onError: (error: Error) => void
  ): Promise<void> {
    // Close any existing connection
    this.close();

    const url = `${API_BASE}/api/fitness/chat`;

    try {
      this.abortController = new AbortController();

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
        },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
        }),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error("Failed to start chat stream");
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          onChunk({ type: "done" });
          break;
        }

        const decoded = decoder.decode(value, { stream: true });
        buffer += decoded;

        // Normalize CRLF to LF for consistent parsing
        buffer = buffer.replace(/\r\n/g, "\n");

        // Process SSE events (format: event: type\ndata: {...}\n\n)
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          if (!event.trim()) continue;

          const lines = event.split("\n");
          let eventType = "text";
          let data = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7);
            } else if (line.startsWith("data: ")) {
              data = line.slice(6);
            }
          }

          if (!data) continue;

          if (data === "[DONE]") {
            onChunk({ type: "done" });
            return;
          }

          try {
            const parsed = JSON.parse(data);

            switch (eventType) {
              case "text":
                if (parsed.content) {
                  onChunk({ type: "content", content: parsed.content });
                }
                break;
              case "thinking":
                if (parsed.content) {
                  onChunk({ type: "thinking", content: parsed.content });
                }
                break;
              case "done":
                onChunk({ type: "done" });
                break;
              case "error":
                onChunk({ type: "error", error: parsed.message || "Unknown error" });
                break;
              case "tool_start":
                onChunk({
                  type: "tool_start",
                  tool: parsed.tool,
                  toolInput: parsed.input,
                });
                break;
              case "tool_result":
                onChunk({
                  type: "tool_result",
                  tool: parsed.tool,
                  toolResult: parsed.result,
                  toolSuccess: parsed.success,
                });
                break;
            }
          } catch {
            // Plain text content fallback
            if (eventType === "text") {
              onChunk({ type: "content", content: data });
            }
          }
        }
      }
    } catch (error) {
      if ((error as Error).name !== "AbortError") {
        onError(error as Error);
      }
    }
  }

  close(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }
}

// Singleton instance
export const sseClient = new SSEClient();

// Utility functions
export const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

export const parseReps = (reps: string): { min: number; max: number } => {
  if (reps.includes("-")) {
    const [min, max] = reps.split("-").map(Number);
    return { min, max };
  }
  const value = parseInt(reps, 10);
  return { min: value, max: value };
};

export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("ru-RU").format(date);
};

export const formatShortDate = (dateString: string): string => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
  }).format(date);
};
