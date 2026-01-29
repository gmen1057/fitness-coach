"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { BottomNav } from "@/components/BottomNav";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Circle,
  Loader2,
  AlertCircle,
  Dumbbell,
  RotateCcw,
  Clock,
  Hash,
  Weight,
  Play,
  MessageSquare,
  Flame,
} from "lucide-react";
import { clsx } from "clsx";

interface Exercise {
  id: string;
  name: string;
  sets: number;
  reps: string;
  weight?: string;
  rest_seconds: number;
  comments?: string;
  order_index: number;
  status: string;
}

interface Warmup {
  id: string;
  instructions: string;
  comments?: string;
  duration_minutes?: number;
}

interface Day {
  id: string;
  name: string;
  day_number: number;
  notes?: string;
  status: "pending" | "completed" | "skipped";
  exercises: Exercise[];
  warmups: Warmup[];
}

interface Week {
  id: string;
  week_number: number;
  days: Day[];
}

interface PlanDetails {
  id: string;
  name: string;
  weeks: Week[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function DayDetailPage() {
  const params = useParams();
  const router = useRouter();
  const planId = params.id as string;
  const dayId = params.dayId as string;

  const [plan, setPlan] = useState<PlanDetails | null>(null);
  const [day, setDay] = useState<Day | null>(null);
  const [weekNumber, setWeekNumber] = useState<number>(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/fitness/plans/${planId}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("Plan not found");
        }
        throw new Error("Failed to fetch plan details");
      }
      const data = await response.json();
      setPlan(data);

      for (const week of data.weeks) {
        const foundDay = week.days.find((d: Day) => d.id === dayId);
        if (foundDay) {
          setDay(foundDay);
          setWeekNumber(week.week_number);
          break;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, [planId, dayId]);

  useEffect(() => {
    if (planId && dayId) {
      fetchData();
    }
  }, [planId, dayId, fetchData]);

  const updateDayStatus = async (status: "completed" | "skipped" | "pending") => {
    setIsUpdating(true);
    try {
      const endpoint =
        status === "completed"
          ? `${API_BASE}/api/fitness/workouts/complete-day`
          : status === "skipped"
          ? `${API_BASE}/api/fitness/workouts/skip-day`
          : `${API_BASE}/api/fitness/workouts/reset-day`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day_id: dayId }),
      });

      if (!response.ok) {
        throw new Error("Failed to update day status");
      }

      await fetchData();
    } catch (err) {
      console.error("Error updating day status:", err);
    } finally {
      setIsUpdating(false);
    }
  };

  const startWorkout = () => {
    router.push(`/workout?day_id=${dayId}`);
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "completed":
        return "Completed";
      case "skipped":
        return "Skipped";
      default:
        return "Pending";
    }
  };

  const breadcrumbs = plan
    ? [
        { label: "Plans", href: "/plans" },
        { label: plan.name, href: `/plans/${planId}` },
        { label: day?.name || `Day ${day?.day_number}` },
      ]
    : [
        { label: "Plans", href: "/plans" },
        { label: "Loading..." },
      ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-24">
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg border-b border-gray-100 dark:border-gray-800">
        <div className="px-4 py-3">
          <div className="flex items-center gap-3">
            <Link
              href={`/plans/${planId}`}
              className="p-2 -ml-2 rounded-xl min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="Go back"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </Link>
            <div className="flex-1 min-w-0">
              <Breadcrumbs items={breadcrumbs} />
            </div>
          </div>
        </div>
      </header>

      <main className="px-4 py-4">
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-fitness animate-spin" />
            <p className="text-gray-500 dark:text-gray-400 mt-3">Loading workout...</p>
          </div>
        )}

        {error && !isLoading && (
          <div className="card p-4 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-medium text-red-700 dark:text-red-400">
                  Failed to load workout
                </p>
                <p className="text-sm text-red-600 dark:text-red-300 mt-0.5">
                  {error}
                </p>
              </div>
            </div>
            <button onClick={fetchData} className="mt-3 btn-secondary text-sm w-full">
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && day && (
          <div className="space-y-4">
            <div className="card p-5">
              <div className="flex items-start gap-4">
                <div
                  className={clsx(
                    "w-14 h-14 rounded-[20px] flex items-center justify-center flex-shrink-0",
                    day.status === "completed"
                      ? "bg-gradient-to-br from-green-500 to-emerald-500"
                      : day.status === "skipped"
                      ? "bg-gradient-to-br from-red-500 to-orange-500"
                      : "bg-gradient-to-br from-fitness to-fitness-light"
                  )}
                >
                  {day.status === "completed" ? (
                    <CheckCircle className="w-7 h-7 text-white" />
                  ) : day.status === "skipped" ? (
                    <XCircle className="w-7 h-7 text-white" />
                  ) : (
                    <Dumbbell className="w-7 h-7 text-white" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold text-fitness bg-fitness/10 px-2 py-0.5 rounded">
                      Week {weekNumber}
                    </span>
                    <span
                      className={clsx(
                        "text-xs font-bold px-2 py-0.5 rounded",
                        day.status === "completed"
                          ? "text-green-600 bg-green-100 dark:bg-green-900/30"
                          : day.status === "skipped"
                          ? "text-red-600 bg-red-100 dark:bg-red-900/30"
                          : "text-gray-600 bg-gray-100 dark:bg-gray-700"
                      )}
                    >
                      {getStatusText(day.status)}
                    </span>
                  </div>

                  <h1 className="text-xl font-bold text-gray-900 dark:text-white mt-1">
                    {day.name || `Day ${day.day_number}`}
                  </h1>

                  {day.notes && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                      {day.notes}
                    </p>
                  )}

                  <div className="flex items-center gap-3 mt-3">
                    <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
                      <Dumbbell className="w-4 h-4" />
                      {day.exercises?.length || 0} exercises
                    </span>
                    {day.warmups?.length > 0 && (
                      <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
                        <Flame className="w-4 h-4 text-orange-500" />
                        Warmup
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                {day.status === "pending" && (
                  <>
                    <button
                      onClick={startWorkout}
                      className="flex-1 flex items-center justify-center gap-2 bg-fitness text-white font-semibold py-3 px-4 rounded-xl shadow-md shadow-fitness/30 active:scale-95 transition-all"
                    >
                      <Play className="w-5 h-5" />
                      Start Workout
                    </button>
                    <button
                      onClick={() => updateDayStatus("completed")}
                      disabled={isUpdating}
                      className="p-3 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-xl active:scale-95 transition-all"
                      aria-label="Mark complete"
                    >
                      {isUpdating ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <CheckCircle className="w-5 h-5" />
                      )}
                    </button>
                    <button
                      onClick={() => updateDayStatus("skipped")}
                      disabled={isUpdating}
                      className="p-3 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded-xl active:scale-95 transition-all"
                      aria-label="Skip"
                    >
                      <XCircle className="w-5 h-5" />
                    </button>
                  </>
                )}

                {(day.status === "completed" || day.status === "skipped") && (
                  <button
                    onClick={() => updateDayStatus("pending")}
                    disabled={isUpdating}
                    className="flex-1 flex items-center justify-center gap-2 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 font-semibold py-3 px-4 rounded-xl active:scale-95 transition-all"
                  >
                    {isUpdating ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <>
                        <RotateCcw className="w-5 h-5" />
                        Reset Status
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {day.warmups && day.warmups.length > 0 && (
              <div className="space-y-2">
                <h2 className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide px-1 flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-500" />
                  Warmup
                </h2>
                {day.warmups.map((warmup) => (
                  <div key={warmup.id} className="card p-4 bg-orange-50 dark:bg-orange-900/10 border-orange-200/50 dark:border-orange-800/50">
                    <p className="text-gray-700 dark:text-gray-300">
                      {warmup.instructions}
                    </p>
                    {warmup.duration_minutes && (
                      <p className="text-xs text-orange-600 dark:text-orange-400 mt-2 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {warmup.duration_minutes} min
                      </p>
                    )}
                    {warmup.comments && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">
                        {warmup.comments}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {day.exercises && day.exercises.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide px-1 flex items-center gap-2">
                  <Dumbbell className="w-4 h-4" />
                  Exercises ({day.exercises.length})
                </h2>
                {day.exercises.map((exercise, index) => (
                  <ExerciseCard key={exercise.id} exercise={exercise} index={index + 1} />
                ))}
              </div>
            )}

            {(!day.exercises || day.exercises.length === 0) && (
              <div className="card p-6 text-center">
                <Dumbbell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto" />
                <h3 className="font-semibold text-gray-900 dark:text-white mt-4">
                  No Exercises
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  This workout day has no exercises defined yet.
                </p>
              </div>
            )}
          </div>
        )}
      </main>

      <BottomNav />
    </div>
  );
}

function ExerciseCard({ exercise, index }: { exercise: Exercise; index: number }) {
  return (
    <div className="card p-4 hover:shadow-md transition-all duration-300">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-fitness/10 text-fitness font-bold rounded-xl flex items-center justify-center flex-shrink-0">
          {index}
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {exercise.name}
          </h3>

          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <span className="inline-flex items-center gap-1 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
              <Hash className="w-3.5 h-3.5" />
              {exercise.sets} sets
            </span>

            {exercise.reps && (
              <span className="inline-flex items-center gap-1 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                <Dumbbell className="w-3.5 h-3.5" />
                {exercise.reps} reps
              </span>
            )}

            {exercise.weight && (
              <span className="inline-flex items-center gap-1 text-sm text-fitness bg-fitness/10 px-2 py-1 rounded font-medium">
                <Weight className="w-3.5 h-3.5" />
                {exercise.weight}
              </span>
            )}

            {exercise.rest_seconds > 0 && (
              <span className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
                <Clock className="w-3.5 h-3.5" />
                {exercise.rest_seconds}s rest
              </span>
            )}
          </div>

          {exercise.comments && (
            <div className="mt-3 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-xs text-gray-600 dark:text-gray-300 flex items-start gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-gray-400 flex-shrink-0 mt-0.5" />
                {exercise.comments}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
