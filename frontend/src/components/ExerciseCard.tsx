"use client";

import { clsx } from "clsx";
import { Check, Clock, Dumbbell } from "lucide-react";
import type { Exercise } from "@/stores/workout";
import { formatTime } from "@/lib/api";

interface ExerciseCardProps {
  exercise: Exercise;
  index: number;
  isCompleted: boolean;
  isActive?: boolean;
  onToggle: () => void;
  onStartRest?: () => void;
}

export function ExerciseCard({
  exercise,
  index,
  isCompleted,
  isActive = false,
  onToggle,
  onStartRest,
}: ExerciseCardProps) {
  return (
    <div
      className={clsx(
        "exercise-card",
        isCompleted && "completed",
        isActive && !isCompleted && "in-progress"
      )}
    >
      {/* Header: checkbox + name */}
      <div className="flex items-start gap-4">
        {/* Checkbox - Material You circular */}
        <button
          onClick={onToggle}
          className={clsx(
            "flex-shrink-0 w-8 h-8 rounded-full border-2 flex items-center justify-center",
            "transition-all duration-300 min-h-[48px] min-w-[48px] -m-2.5",
            isCompleted
              ? "bg-gradient-to-br from-fitness to-fitness-light border-fitness text-white scale-110 shadow-lg shadow-fitness/30"
              : "border-gray-300 dark:border-gray-600 bg-transparent hover:bg-gray-50 dark:hover:bg-gray-700/50"
          )}
          aria-label={isCompleted ? "Mark incomplete" : "Mark complete"}
        >
          {isCompleted && <Check className="w-5 h-5 stroke-[3px]" />}
        </button>

        {/* Exercise name and number */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-400 dark:text-gray-500">
              #{index + 1}
            </span>
            <h3
              className={clsx(
                "font-semibold text-gray-900 dark:text-white",
                isCompleted && "line-through opacity-60"
              )}
            >
              {exercise.name}
            </h3>
          </div>

          {exercise.muscle_group && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {exercise.muscle_group}
            </p>
          )}
        </div>
      </div>

      {/* Details: vertical stack for mobile-friendly display */}
      <div className="mt-4 ml-11 space-y-3">
        {/* Sets x Reps row */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-2 bg-gradient-to-r from-gray-100 to-gray-50 dark:from-gray-700 dark:to-gray-700/80 px-4 py-2 rounded-full shadow-sm">
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              {exercise.sets} sets
            </span>
            <span className="text-gray-400">×</span>
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              {exercise.reps} reps
            </span>
          </div>

          {/* Weight badge */}
          {exercise.weight && (
            <div className="flex items-center gap-2 bg-gradient-to-r from-fitness/15 to-emerald-500/10 dark:from-fitness/25 dark:to-emerald-500/15 px-4 py-2 rounded-full shadow-sm">
              <Dumbbell className="w-4 h-4 text-fitness" />
              <span className="text-sm font-bold text-fitness">
                {exercise.weight}
              </span>
            </div>
          )}

          {/* Rest timer button */}
          {onStartRest && !isCompleted && (
            <button
              onClick={onStartRest}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-full",
                "text-sm font-medium",
                "bg-gradient-to-r from-blue-100 to-blue-50 dark:from-blue-900/30 dark:to-blue-900/20",
                "text-blue-600 dark:text-blue-400",
                "min-h-[40px] active:scale-95 transition-all duration-300 shadow-sm hover:shadow-md"
              )}
            >
              <Clock className="w-4 h-4" />
              {formatTime(exercise.rest_seconds)}
            </button>
          )}
        </div>

        {/* Notes - clearly separated */}
        {exercise.notes && (
          <div className="bg-gradient-to-r from-amber-50 to-orange-50/50 dark:from-amber-900/20 dark:to-orange-900/10 border border-amber-200/80 dark:border-amber-800/80 rounded-[20px] px-4 py-3 shadow-sm">
            <p className="text-sm text-amber-800 dark:text-amber-200 leading-relaxed">
              {exercise.notes}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
