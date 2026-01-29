"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Wrench, Check, X, Loader2 } from "lucide-react";
import { clsx } from "clsx";

interface ToolCallBlockProps {
  toolName: string;
  input?: Record<string, unknown>;
  result?: unknown;
  success?: boolean;
  isLoading?: boolean;
}

// Format tool name for display
const formatToolName = (name: string): string => {
  return name
    .replace(/_/g, " ")
    .replace(/([A-Z])/g, " $1")
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase())
    .trim();
};

export function ToolCallBlock({
  toolName,
  input,
  result,
  success,
  isLoading = false,
}: ToolCallBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasDetails = Boolean(input || result !== undefined);

  return (
    <div className="my-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={() => hasDetails && setIsExpanded(!isExpanded)}
        disabled={!hasDetails}
        className={clsx(
          "w-full px-3 py-2 flex items-center gap-2 text-left",
          hasDetails && "hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
        )}
      >
        {/* Status icon */}
        <div
          className={clsx(
            "w-5 h-5 rounded flex items-center justify-center flex-shrink-0",
            isLoading
              ? "bg-blue-100 dark:bg-blue-900/30 text-blue-500"
              : success === true
              ? "bg-green-100 dark:bg-green-900/30 text-green-500"
              : success === false
              ? "bg-red-100 dark:bg-red-900/30 text-red-500"
              : "bg-gray-200 dark:bg-gray-700 text-gray-500"
          )}
        >
          {isLoading && <Loader2 className="w-3 h-3 animate-spin" />}
          {!isLoading && success === true && <Check className="w-3 h-3" />}
          {!isLoading && success === false && <X className="w-3 h-3" />}
          {!isLoading && success === undefined && <Wrench className="w-3 h-3" />}
        </div>

        {/* Tool name */}
        <span className="text-xs font-medium text-gray-600 dark:text-gray-300 flex-1 truncate">
          {formatToolName(toolName)}
        </span>

        {/* Expand/collapse icon */}
        {hasDetails && (
          <div className="flex-shrink-0 text-gray-400">
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </div>
        )}
      </button>

      {/* Expandable details */}
      {isExpanded && hasDetails && (
        <div className="px-3 pb-3 pt-1 border-t border-gray-200 dark:border-gray-700 space-y-2">
          {input && (
            <div>
              <span className="text-[10px] uppercase tracking-wide text-gray-400 dark:text-gray-500 font-medium">
                Input
              </span>
              <pre className="mt-1 text-[11px] text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-900 rounded p-2 overflow-x-auto max-h-32">
                {JSON.stringify(input, null, 2)}
              </pre>
            </div>
          )}
          {result !== undefined && (
            <div>
              <span className="text-[10px] uppercase tracking-wide text-gray-400 dark:text-gray-500 font-medium">
                Result
              </span>
              <pre className="mt-1 text-[11px] text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-900 rounded p-2 overflow-x-auto max-h-32">
                {typeof result === "string"
                  ? result
                  : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
