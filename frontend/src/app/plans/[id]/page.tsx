"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { BottomNav } from "@/components/BottomNav";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  CheckCircle,
  XCircle,
  Circle,
  Loader2,
  AlertCircle,
  Target,
  Calendar,
  Play,
  Dumbbell,
  RotateCcw,
} from "lucide-react";
import { clsx } from "clsx";

interface Exercise {
  id: string;
  name: string;
  sets: number;
  reps: string;
  rest_seconds: number;
  comments?: string;
}

interface Day {
  id: string;
  name: string;
  day_number: number;
  notes?: string;
  status: "pending" | "completed" | "skipped";
  exercises: Exercise[];
  completed_at?: string;
}

interface Week {
  id: string;
  week_number: number;
  days: Day[];
}

interface PlanDetails {
  id: string;
  name: string;
  goal: string;
  total_weeks: number;
  current_week: number;
  current_day: number;
  is_active: boolean;
  weeks: Week[];
  created_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function PlanDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const planId = params.id as string;

  const [plan, setPlan] = useState<PlanDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedWeeks, setExpandedWeeks] = useState<Set<number>>(new Set());
  const [updatingDay, setUpdatingDay] = useState<string | null>(null);

  const fetchPlanDetails = useCallback(async () => {
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

      if (data.current_week) {
        setExpandedWeeks(new Set([data.current_week]));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, [planId]);

  useEffect(() => {
    if (planId) {
      fetchPlanDetails();
    }
  }, [planId, fetchPlanDetails]);

  const toggleWeek = (weekNumber: number) => {
    setExpandedWeeks((prev) => {
      const next = new Set(prev);
      if (next.has(weekNumber)) {
        next.delete(weekNumber);
      } else {
        next.add(weekNumber);
      }
      return next;
    });
  };

  const updateDayStatus = async (
    dayId: string,
    status: "completed" | "skipped" | "pending"
  ) => {
    setUpdatingDay(dayId);
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

      await fetchPlanDetails();
    } catch (err) {
      console.error("Error updating day status:", err);
    } finally {
      setUpdatingDay(null);
    }
  };

  const startWorkout = (dayId: string) => {
    router.push(`/workout?day_id=${dayId}`);
  };

  const getStatusIcon = (status: string, isUpdating: boolean) => {
    if (isUpdating) {
      return <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />;
    }
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "skipped":
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Circle className="w-5 h-5 text-gray-300 dark:text-gray-600" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return (
          <span className="text-[10px] font-semibold text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-1.5 py-0.5 rounded">
            Done
          </span>
        );
      case "skipped":
        return (
          <span className="text-[10px] font-semibold text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30 px-1.5 py-0.5 rounded">
            Skipped
          </span>
        );
      default:
        return null;
    }
  };

  const getWeekProgress = (week: Week) => {
    const completed = week.days.filter((d) => d.status === "completed").length;
    const percentage = week.days.length > 0 ? Math.round((completed / week.days.length) * 100) : 0;
    return { completed, total: week.days.length, percentage };
  };

  const getTotalProgress = () => {
    if (!plan?.weeks) return { completed: 0, total: 0, percentage: 0 };
    let completed = 0;
    let total = 0;
    plan.weeks.forEach((week) => {
      week.days.forEach((day) => {
        total++;
        if (day.status === "completed") completed++;
      });
    });
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
    return { completed, total, percentage };
  };

  const progress = getTotalProgress();

  const breadcrumbs = plan
    ? [
        { label: "Plans", href: "/plans" },
        { label: plan.name },
      ]
    : [{ label: "Plans", href: "/plans" }, { label: "Loading..." }];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-24">
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg border-b border-gray-100 dark:border-gray-800">
        <div className="px-4 py-3">
          <div className="flex items-center gap-3">
            <Link
              href="/plans"
              className="p-2 -ml-2 rounded-xl min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="Go back"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </Link>
            <div className="flex-1 min-w-0">
              <Breadcrumbs items={breadcrumbs} />
              {plan?.is_active && (
                <span className="text-xs text-fitness font-semibold mt-0.5 block">
                  Active Plan
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="px-4 py-4">
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-fitness animate-spin" />
            <p className="text-gray-500 dark:text-gray-400 mt-3">
              Loading plan...
            </p>
          </div>
        )}

        {error && !isLoading && (
          <div className="card p-4 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-medium text-red-700 dark:text-red-400">
                  Failed to load plan
                </p>
                <p className="text-sm text-red-600 dark:text-red-300 mt-0.5">
                  {error}
                </p>
              </div>
            </div>
            <button
              onClick={fetchPlanDetails}
              className="mt-3 btn-secondary text-sm w-full"
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && plan && (
          <div className="space-y-4">
            <div className="card p-4">
              <h2 className="font-bold text-xl text-gray-900 dark:text-white">
                {plan.name}
              </h2>

              {plan.goal && (
                <div className="flex items-start gap-2 mt-2">
                  <Target className="w-4 h-4 text-fitness flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    {plan.goal}
                  </p>
                </div>
              )}

              <div className="flex items-center gap-4 mt-3">
                <div className="flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {plan.total_weeks} weeks
                  </span>
                </div>
                <span className="text-gray-300 dark:text-gray-600">|</span>
                <span className="text-sm font-medium text-fitness">
                  Week {plan.current_week}, Day {plan.current_day}
                </span>
              </div>

              <div className="mt-4">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-gray-500 dark:text-gray-400 font-medium">
                    Overall Progress
                  </span>
                  <span className="font-bold text-gray-700 dark:text-gray-300">
                    {progress.completed}/{progress.total} days ({progress.percentage}%)
                  </span>
                </div>
                <div className="h-2.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-fitness to-fitness-light rounded-full transition-all duration-500"
                    style={{ width: `${progress.percentage}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {plan.weeks.map((week) => {
                const isExpanded = expandedWeeks.has(week.week_number);
                const weekProgress = getWeekProgress(week);
                const isCurrentWeek = week.week_number === plan.current_week;

                return (
                  <div
                    key={week.id}
                    className={clsx(
                      "card overflow-hidden",
                      isCurrentWeek && "ring-2 ring-fitness/30"
                    )}
                  >
                    <button
                      onClick={() => toggleWeek(week.week_number)}
                      className={clsx(
                        "w-full p-4 flex items-center justify-between text-left min-h-[56px]",
                        isExpanded && "border-b border-gray-100 dark:border-gray-700"
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={clsx(
                            "w-12 h-12 rounded-xl flex flex-col items-center justify-center",
                            isCurrentWeek
                              ? "bg-gradient-to-br from-fitness to-fitness-light text-white"
                              : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                          )}
                        >
                          <span className="font-bold text-sm leading-none">
                            W{week.week_number}
                          </span>
                          <span className="text-[10px] opacity-80">
                            {weekProgress.percentage}%
                          </span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-gray-900 dark:text-white">
                              Week {week.week_number}
                            </h3>
                            {isCurrentWeek && (
                              <span className="text-[10px] font-semibold text-fitness bg-fitness/10 px-1.5 py-0.5 rounded">
                                Current
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {weekProgress.completed}/{weekProgress.total} days completed
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {isExpanded ? (
                          <ChevronUp className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="divide-y divide-gray-100 dark:divide-gray-700">
                        {week.days.map((day) => {
                          const isUpdating = updatingDay === day.id;
                          const isCurrentDay =
                            isCurrentWeek && day.day_number === plan.current_day;
                          const canStart = day.status === "pending";

                          return (
                            <div
                              key={day.id}
                              className={clsx(
                                "p-4 transition-colors",
                                isCurrentDay && "bg-fitness/5 dark:bg-fitness/10"
                              )}
                            >
                              <div className="flex items-start gap-3">
                                <div className="flex-shrink-0 mt-0.5">
                                  {getStatusIcon(day.status, isUpdating)}
                                </div>

                                <Link
                                  href={`/plans/${planId}/day/${day.id}`}
                                  className="flex-1 min-w-0 group"
                                >
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <h4
                                      className={clsx(
                                        "font-semibold group-hover:text-fitness transition-colors",
                                        day.status === "skipped"
                                          ? "text-gray-400 dark:text-gray-500 line-through"
                                          : "text-gray-900 dark:text-white"
                                      )}
                                    >
                                      {day.name || `Day ${day.day_number}`}
                                    </h4>
                                    {isCurrentDay && (
                                      <span className="text-[10px] font-bold text-white bg-fitness px-1.5 py-0.5 rounded">
                                        TODAY
                                      </span>
                                    )}
                                    {getStatusBadge(day.status)}
                                    <ChevronRight className="w-4 h-4 text-gray-300 dark:text-gray-600 group-hover:text-fitness transition-colors" />
                                  </div>

                                  {day.notes && (
                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-1">
                                      {day.notes}
                                    </p>
                                  )}

                                  {day.exercises?.length > 0 && (
                                    <div className="flex items-center gap-1 mt-1.5">
                                      <Dumbbell className="w-3 h-3 text-gray-400" />
                                      <span className="text-[11px] text-gray-400">
                                        {day.exercises.length} exercises
                                      </span>
                                    </div>
                                  )}
                                </Link>

                                <div className="flex items-center gap-2 flex-shrink-0">
                                  {canStart && (
                                    <button
                                      onClick={() => startWorkout(day.id)}
                                      className={clsx(
                                        "flex items-center gap-1.5 px-3 py-2 rounded-xl font-medium text-sm transition-all min-h-[44px]",
                                        isCurrentDay
                                          ? "bg-fitness text-white shadow-sm shadow-fitness/30 active:scale-95"
                                          : "bg-fitness/10 text-fitness hover:bg-fitness/20 active:scale-95"
                                      )}
                                    >
                                      <Play className="w-4 h-4" />
                                      {isCurrentDay ? "Start" : ""}
                                    </button>
                                  )}

                                  {(day.status === "completed" || day.status === "skipped") && (
                                    <button
                                      onClick={() => updateDayStatus(day.id, "pending")}
                                      disabled={isUpdating}
                                      className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 min-h-[44px] min-w-[44px] flex items-center justify-center active:scale-95 transition-all"
                                      aria-label="Reset status"
                                    >
                                      <RotateCcw className="w-4 h-4" />
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {plan.weeks.length === 0 && (
              <div className="card p-6 text-center">
                <Dumbbell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto" />
                <h3 className="font-semibold text-gray-900 dark:text-white mt-4">
                  No Weeks Found
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  This plan does not have any scheduled weeks yet.
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
