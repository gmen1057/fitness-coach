"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BottomNav } from "@/components/BottomNav";
import {
  ArrowLeft,
  TrendingUp,
  Calendar,
  Flame,
  Target,
  CheckCircle,
  Loader2,
  AlertCircle,
} from "lucide-react";

interface WorkoutStats {
  total_workouts: number;
  completed_workouts: number;
  current_streak: number;
  longest_streak: number;
  workouts_this_week: number;
  workouts_this_month: number;
}

interface RecentWorkout {
  id: string;
  date: string;
  day_name: string;
  plan_name: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function ProgressPage() {
  const [stats, setStats] = useState<WorkoutStats | null>(null);
  const [recentWorkouts, setRecentWorkouts] = useState<RecentWorkout[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProgress();
  }, []);

  const fetchProgress = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/fitness/workouts/stats`);
      if (!response.ok) {
        throw new Error("Failed to fetch stats");
      }
      const data = await response.json();
      setStats(data);

      // Get recent workouts (mock for now - would need actual API endpoint)
      setRecentWorkouts([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
    }).format(date);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg border-b border-gray-100 dark:border-gray-800">
        <div className="px-4 py-3">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="p-2 -ml-2 rounded-xl min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="Go back"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                Your Progress
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Track your fitness journey
              </p>
            </div>
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
              Loading progress...
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
                  Failed to load progress
                </p>
                <p className="text-sm text-red-600 dark:text-red-300 mt-0.5">
                  {error}
                </p>
              </div>
            </div>
            <button
              onClick={fetchProgress}
              className="mt-3 btn-secondary text-sm w-full"
            >
              Retry
            </button>
          </div>
        )}

        {/* Stats grid */}
        {!isLoading && !error && stats && (
          <div className="space-y-4">
            {/* Main stats */}
            <div className="grid grid-cols-2 gap-3">
              <div className="card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Flame className="w-5 h-5 text-orange-500" />
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    Current Streak
                  </p>
                </div>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                  {stats.current_streak}
                </p>
                <p className="text-xs text-gray-400 mt-1">days</p>
              </div>

              <div className="card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-5 h-5 text-fitness" />
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    Total Workouts
                  </p>
                </div>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                  {stats.completed_workouts}
                </p>
                <p className="text-xs text-gray-400 mt-1">completed</p>
              </div>

              <div className="card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Calendar className="w-5 h-5 text-blue-500" />
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    This Week
                  </p>
                </div>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                  {stats.workouts_this_week}
                </p>
                <p className="text-xs text-gray-400 mt-1">workouts</p>
              </div>

              <div className="card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-5 h-5 text-purple-500" />
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    Best Streak
                  </p>
                </div>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                  {stats.longest_streak}
                </p>
                <p className="text-xs text-gray-400 mt-1">days</p>
              </div>
            </div>

            {/* Progress this month */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  This Month
                </h3>
                <span className="text-sm font-medium text-fitness">
                  {stats.workouts_this_month} workouts
                </span>
              </div>
              <div className="h-2.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-fitness to-fitness-light rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min((stats.workouts_this_month / 20) * 100, 100)}%`,
                  }}
                />
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                Goal: 20 workouts per month
              </p>
            </div>

            {/* Motivational message */}
            <div className="card p-5 bg-gradient-to-br from-fitness/5 to-fitness/10 border-fitness/20">
              <div className="flex items-start gap-3">
                <TrendingUp className="w-6 h-6 text-fitness flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    {stats.current_streak > 0
                      ? `Amazing! ${stats.current_streak} day streak! 🔥`
                      : "Start your streak today!"}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    {stats.current_streak > 0
                      ? "Keep up the great work. Consistency is key to reaching your fitness goals."
                      : "Begin your fitness journey by completing your first workout."}
                  </p>
                </div>
              </div>
            </div>

            {/* Recent workouts */}
            {recentWorkouts.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                  Recent Workouts
                </h3>
                <div className="space-y-2">
                  {recentWorkouts.map((workout) => (
                    <div key={workout.id} className="card p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {workout.day_name}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {workout.plan_name}
                          </p>
                        </div>
                        <span className="text-xs text-gray-400">
                          {formatDate(workout.date)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      <BottomNav />
    </div>
  );
}
