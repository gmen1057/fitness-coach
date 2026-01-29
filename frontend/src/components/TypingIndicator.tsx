"use client";

import { Bot } from "lucide-react";

interface TypingIndicatorProps {
  label?: string;
}

export function TypingIndicator({ label = "AI is typing" }: TypingIndicatorProps) {
  return (
    <div className="flex items-start gap-3 animate-fade-in">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 flex items-center justify-center">
        <Bot className="w-4 h-4" />
      </div>

      {/* Typing bubble */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl rounded-tl-md px-4 py-3 border border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2">
          {/* Animated dots */}
          <div className="flex items-center gap-1">
            <span
              className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"
              style={{ animationDelay: "0ms" }}
            />
            <span
              className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"
              style={{ animationDelay: "150ms" }}
            />
            <span
              className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"
              style={{ animationDelay: "300ms" }}
            />
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500 ml-1">
            {label}
          </span>
        </div>
      </div>
    </div>
  );
}
