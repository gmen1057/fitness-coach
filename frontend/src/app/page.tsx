"use client";

import { useEffect } from "react";
import { useWorkoutStore } from "@/stores/workout";
import { BottomNav } from "@/components/BottomNav";
import { Dumbbell, MessageSquare, Calendar, TrendingUp } from "lucide-react";
import Link from "next/link";

export default function HomePage() {
  const { currentPlan, currentDay, stats, fetchCurrentWorkout, initOfflineListeners } = useWorkoutStore();

  useEffect(() => {
    // Initialize offline listeners
    const cleanup = initOfflineListeners();
    // Fetch workout data
    fetchCurrentWorkout();
    return cleanup;
  }, [fetchCurrentWorkout, initOfflineListeners]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-gray-900 dark:to-gray-800 pb-24">
      {/* Header */}
      <header className="safe-area-pt p-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Fitness Coach
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Your AI-powered training companion
        </p>
      </header>

      {/* Current Workout Card */}
      {currentDay && !currentDay.completed && (
        <div className="px-6 mb-8">
          <Link href="/workout">
            <div className="card p-6 bg-gradient-to-br from-fitness to-fitness-light text-white hover:shadow-xl transition-all cursor-pointer">
              <div className="flex items-center gap-3 mb-3">
                <Dumbbell className="w-6 h-6" />
                <h2 className="text-xl font-bold">Today&apos;s Workout</h2>
              </div>
              <p className="text-emerald-50 mb-2">{currentDay.name}</p>
              <p className="text-sm text-emerald-100">
                {currentDay.exercises.length} exercises
              </p>
            </div>
          </Link>
        </div>
      )}

      {/* Stats Grid */}
      {stats && (
        <div className="px-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
            Your Progress
          </h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="card p-4">
              <p className="text-2xl font-bold text-fitness">{stats.current_streak}</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Day Streak</p>
            </div>
            <div className="card p-4">
              <p className="text-2xl font-bold text-fitness">{stats.total_workouts}</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Workouts</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="px-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Quick Actions
        </h2>
        <div className="flex flex-col gap-4">
          <Link href="/chat">
            <div className="card p-5 flex items-center gap-4 hover:shadow-lg transition-all cursor-pointer">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white">
                <MessageSquare className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 dark:text-white">AI Chat</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Get workout advice and tips
                </p>
              </div>
            </div>
          </Link>

          <Link href="/plans">
            <div className="card p-5 flex items-center gap-4 hover:shadow-lg transition-all cursor-pointer">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white">
                <Calendar className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 dark:text-white">Workout Plans</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  View and manage your plans
                </p>
              </div>
            </div>
          </Link>

          <Link href="/progress">
            <div className="card p-5 flex items-center gap-4 hover:shadow-lg transition-all cursor-pointer">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center text-white">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 dark:text-white">Progress</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Track your fitness journey
                </p>
              </div>
            </div>
          </Link>
        </div>
      </div>

      {/* Current Plan Info */}
      {currentPlan && (
        <div className="px-6">
          <div className="card p-5 border-l-4 border-fitness">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
              {currentPlan.name}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Week {currentPlan.current_week} of {currentPlan.duration_weeks}
            </p>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
