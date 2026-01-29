"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BottomNav } from "@/components/BottomNav";
import {
  ArrowLeft,
  Plus,
  Target,
  Calendar,
  ChevronRight,
  Loader2,
  AlertCircle,
  Dumbbell,
} from "lucide-react";
import { clsx } from "clsx";

interface PlanSummary {
  id: string;
  name: string;
  goal: string;
  description?: string;
  total_weeks: number;
  is_active: boolean;
  created_at: string;
  progress_percent: number;
  completed_days: number;
  total_days: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function PlansPage() {
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/fitness/plans`);
      if (!response.ok) {
        throw new Error("Failed to fetch plans");
      }
      const data = await response.json();
      setPlans(data.plans || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  const getProgressPercentage = (plan: PlanSummary) => {
    return Math.round(plan.progress_percent || 0);
  };

  const getStatusBadge = (plan: PlanSummary) => {
    if (plan.is_active) {
      return (
        <span className="text-xs font-medium text-fitness bg-fitness/10 px-2 py-0.5 rounded-full">
          Active
        </span>
      );
    }
    if (plan.progress_percent >= 100) {
      return (
        <span className="text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 rounded-full">
          Completed
        </span>
      );
    }
    return (
      <span className="text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
        Inactive
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg border-b border-gray-100 dark:border-gray-800">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="p-2 -ml-2 rounded-xl min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label="Go back"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              </Link>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                Training Plans
              </h1>
            </div>
            <Link
              href="/chat"
              className="p-2 rounded-xl bg-fitness text-white min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="Create new plan"
            >
              <Plus className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="px-4 py-4">
        {/* Loading state */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-fitness animate-spin" />
            <p className="text-gray-500 dark:text-gray-400 mt-3">
              Loading plans...
            </p>
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div className="card p-4 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-medium text-red-700 dark:text-red-400">
                  Failed to load plans
                </p>
                <p className="text-sm text-red-600 dark:text-red-300 mt-0.5">
                  {error}
                </p>
              </div>
            </div>
            <button
              onClick={fetchPlans}
              className="mt-3 btn-secondary text-sm w-full"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && plans.length === 0 && (
          <div className="card p-6 text-center">
            <Dumbbell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto" />
            <h3 className="font-semibold text-gray-900 dark:text-white mt-4">
              No Training Plans
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Chat with AI to create your personalized workout plan.
            </p>
            <Link
              href="/chat"
              className="btn-primary mt-4 inline-flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Create Plan
            </Link>
          </div>
        )}

        {/* Plans list */}
        {!isLoading && !error && plans.length > 0 && (
          <div className="space-y-3">
            {plans.map((plan) => (
              <Link
                key={plan.id}
                href={`/plans/${plan.id}`}
                className="block"
              >
                <div className="card p-4 hover:shadow-md transition-shadow active:scale-[0.98]">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusBadge(plan)}
                      </div>
                      <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                        {plan.name}
                      </h3>
                      {plan.goal && (
                        <div className="flex items-center gap-1.5 mt-1">
                          <Target className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                            {plan.goal}
                          </p>
                        </div>
                      )}
                      <div className="flex items-center gap-3 mt-2">
                        <div className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 text-gray-400" />
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {plan.total_weeks} weeks
                          </span>
                        </div>
                        <span className="text-xs text-gray-400">|</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {plan.completed_days}/{plan.total_days} days
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0 ml-2" />
                  </div>

                  {/* Progress bar */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-gray-500 dark:text-gray-400">
                        Progress
                      </span>
                      <span className="font-medium text-gray-700 dark:text-gray-300">
                        {getProgressPercentage(plan)}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={clsx(
                          "h-full rounded-full transition-all duration-300",
                          plan.is_active ? "bg-fitness" : "bg-gray-400"
                        )}
                        style={{ width: `${getProgressPercentage(plan)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      <BottomNav />
    </div>
  );
}
