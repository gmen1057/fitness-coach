"use client";

import { useEffect } from "react";
import { useWorkoutStore } from "@/stores/workout";
import { ExerciseCard } from "@/components/ExerciseCard";
import { BottomNav } from "@/components/BottomNav";
import { ArrowLeft, CheckCircle, Calendar } from "lucide-react";
import Link from "next/link";

export default function WorkoutPage() {
  const { currentDay, exerciseProgress, toggleExercise, completeDay, fetchCurrentWorkout } = useWorkoutStore();

  useEffect(() => {
    fetchCurrentWorkout();
  }, [fetchCurrentWorkout]);

  const handleComplete = async () => {
    const success = await completeDay();
    if (success) {
      // Navigate back to home
      window.location.href = "/";
    }
  };

  const completedExercises = currentDay?.exercises.filter(ex => exerciseProgress[ex.id]).length || 0;
  const totalExercises = currentDay?.exercises.length || 0;
  const allCompleted = completedExercises === totalExercises && totalExercises > 0;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-24">
      {/* Header */}
      <header className="sticky top-0 bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl z-10 border-b border-gray-200 dark:border-gray-700">
        <div className="p-4 flex items-center gap-3">
          <Link href="/">
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </button>
          </Link>
          <div className="flex-1">
            <h1 className="font-bold text-gray-900 dark:text-white">
              {currentDay?.name || "Today's Workout"}
            </h1>
            {currentDay && (
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {completedExercises} / {totalExercises} completed
              </p>
            )}
          </div>
        </div>
      </header>

      {/* Content */}
      {!currentDay || currentDay.completed ? (
        <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
          <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mb-4">
            {currentDay?.completed ? (
              <CheckCircle className="w-8 h-8 text-green-500" />
            ) : (
              <Calendar className="w-8 h-8 text-gray-400" />
            )}
          </div>
          <p className="text-gray-900 dark:text-white font-semibold mb-2">
            {currentDay?.completed ? "All workouts completed! 🎉" : "No workout scheduled for today"}
          </p>
          <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
            {currentDay?.completed
              ? "Great job! Take a rest or start a new training plan."
              : "Take a rest day or check your workout plans to schedule one"}
          </p>
          <Link href="/plans">
            <button className="btn-primary">View Plans</button>
          </Link>
        </div>
      ) : (
        <>
          {/* Exercises */}
          <div className="p-4 space-y-4">
            {currentDay.exercises.map((exercise, index) => (
              <ExerciseCard
                key={exercise.id}
                exercise={exercise}
                index={index}
                isCompleted={exerciseProgress[exercise.id] || false}
                isActive={index === completedExercises && !allCompleted}
                onToggle={() => toggleExercise(exercise.id)}
              />
            ))}
          </div>

          {/* Complete Button */}
          {allCompleted && (
            <div className="fixed bottom-20 left-6 right-6 z-40">
              <button
                onClick={handleComplete}
                className="btn-primary w-full gap-2"
              >
                <CheckCircle className="w-5 h-5" />
                Complete Workout
              </button>
            </div>
          )}
        </>
      )}

      <BottomNav />
    </div>
  );
}
