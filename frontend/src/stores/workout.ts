import { create } from "zustand";
import { persist } from "zustand/middleware";

// Type definitions
export interface Exercise {
  id: string;
  name: string;
  muscle_group: string;
  sets: number;
  reps: string;
  weight?: string;
  rest_seconds: number;
  notes?: string;
  completed?: boolean;
}

export interface Day {
  id: string;
  name: string;
  day_number: number;
  focus: string;
  exercises: Exercise[];
  completed: boolean;
  skipped: boolean;
  completed_at?: string;
}

export interface Week {
  id: string;
  week_number: number;
  days: Day[];
  start_date: string;
  end_date: string;
}

export interface Plan {
  id: string;
  name: string;
  goal: string;
  duration_weeks: number;
  days_per_week: number;
  current_week: number;
  current_day: number;
  weeks: Week[];
  created_at: string;
}

export interface WorkoutStats {
  total_workouts: number;
  current_streak: number;
  this_week_completed: number;
  this_week_target: number;
}

// Offline action queue for sync when back online
export interface OfflineAction {
  type: 'complete' | 'skip';
  dayId: string;
  reason?: string;
}

interface WorkoutState {
  // Data
  currentPlan: Plan | null;
  currentWeek: Week | null;
  currentDay: Day | null;
  stats: WorkoutStats | null;

  // UI State
  isLoading: boolean;
  error: string | null;

  // Offline support
  lastSynced: number | null;
  isOffline: boolean;
  offlineQueue: OfflineAction[];
  isSyncing: boolean;

  // Exercise tracking during workout
  exerciseProgress: Record<string, boolean>;

  // Actions
  setCurrentPlan: (plan: Plan | null) => void;
  setCurrentWeek: (week: Week | null) => void;
  setCurrentDay: (day: Day | null) => void;
  setStats: (stats: WorkoutStats | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Exercise actions
  toggleExercise: (exerciseId: string) => void;
  resetExerciseProgress: () => void;

  // Offline actions
  setIsOffline: (offline: boolean) => void;
  initOfflineListeners: () => () => void;
  syncOfflineQueue: () => Promise<void>;

  // API actions
  fetchCurrentWorkout: () => Promise<void>;
  completeDay: () => Promise<boolean>;
  skipDay: (reason?: string) => Promise<boolean>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export const useWorkoutStore = create<WorkoutState>()(
  persist(
    (set, get) => ({
      // Initial state
      currentPlan: null,
      currentWeek: null,
      currentDay: null,
      stats: null,
      isLoading: false,
      error: null,
      lastSynced: null,
      isOffline: false,
      offlineQueue: [],
      isSyncing: false,
      exerciseProgress: {},

      // Setters
      setCurrentPlan: (plan) => set({ currentPlan: plan }),
      setCurrentWeek: (week) => set({ currentWeek: week }),
      setCurrentDay: (day) => set({ currentDay: day }),
      setStats: (stats) => set({ stats: stats }),
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error: error }),

      // Exercise tracking
      toggleExercise: (exerciseId) => {
        const progress = get().exerciseProgress;
        set({
          exerciseProgress: {
            ...progress,
            [exerciseId]: !progress[exerciseId],
          },
        });
      },

      resetExerciseProgress: () => set({ exerciseProgress: {} }),

      // Offline support
      setIsOffline: (offline) => set({ isOffline: offline }),

      initOfflineListeners: () => {
        if (typeof window === 'undefined') return () => {};

        const handleOnline = async () => {
          set({ isOffline: false });
          const { offlineQueue, syncOfflineQueue } = get();
          if (offlineQueue.length > 0) {
            await syncOfflineQueue();
          }
        };

        const handleOffline = () => {
          set({ isOffline: true });
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        // Set initial state
        set({ isOffline: !navigator.onLine });

        return () => {
          window.removeEventListener('online', handleOnline);
          window.removeEventListener('offline', handleOffline);
        };
      },

      syncOfflineQueue: async () => {
        const { offlineQueue } = get();
        if (offlineQueue.length === 0) return;

        set({ isSyncing: true });

        const failedActions: OfflineAction[] = [];

        for (const action of offlineQueue) {
          try {
            const endpoint = action.type === 'complete'
              ? `${API_BASE}/api/fitness/workouts/complete-day`
              : `${API_BASE}/api/fitness/workouts/skip-day`;

            const body = action.type === 'complete'
              ? { day_id: action.dayId }
              : { day_id: action.dayId, reason: action.reason || 'Skipped offline' };

            const response = await fetch(endpoint, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(body),
            });

            if (!response.ok) {
              failedActions.push(action);
            }
          } catch {
            failedActions.push(action);
          }
        }

        set({ offlineQueue: failedActions, isSyncing: false });

        if (failedActions.length === 0) {
          get().fetchCurrentWorkout();
        }
      },

      // Fetch current workout data
      fetchCurrentWorkout: async () => {
        const { currentPlan } = get();

        // If offline and have cached data, use it silently
        if (typeof window !== 'undefined' && !navigator.onLine && currentPlan) {
          console.log('Offline: using cached workout');
          set({ isOffline: true, isLoading: false });
          return;
        }

        set({ isLoading: true, error: null });
        try {
          // Get active plans
          const plansResponse = await fetch(`${API_BASE}/api/fitness/plans?is_active=true&limit=1`);
          if (!plansResponse.ok) {
            throw new Error("Failed to fetch plans");
          }
          const plansData = await plansResponse.json();

          if (plansData.plans && plansData.plans.length > 0) {
            const planSummary = plansData.plans[0];

            // Get full plan with current workout
            const currentResponse = await fetch(`${API_BASE}/api/fitness/plans/${planSummary.id}/current`);
            if (currentResponse.ok) {
              const currentData = await currentResponse.json();

              // Get stats
              const statsResponse = await fetch(`${API_BASE}/api/fitness/workouts/stats`);
              const statsData = statsResponse.ok ? await statsResponse.json() : null;

              set({
                currentPlan: {
                  id: planSummary.id,
                  name: planSummary.name,
                  goal: planSummary.goal || "",
                  duration_weeks: planSummary.total_weeks,
                  days_per_week: 4,
                  current_week: currentData.week_number,
                  current_day: currentData.day?.day_number || 1,
                  weeks: [],
                  created_at: planSummary.created_at,
                },
                currentWeek: {
                  id: `week-${currentData.week_number}`,
                  week_number: currentData.week_number,
                  days: [],
                  start_date: "",
                  end_date: "",
                },
                currentDay: currentData.day ? {
                  id: currentData.day.id,
                  name: currentData.day.name || `Day ${currentData.day.day_number}`,
                  day_number: currentData.day.day_number,
                  focus: currentData.day.notes || "",
                  exercises: currentData.day.exercises?.map((ex: any) => ({
                    id: ex.id,
                    name: ex.name,
                    muscle_group: "",
                    sets: ex.sets,
                    reps: ex.reps || "",
                    weight: ex.weight || undefined,
                    rest_seconds: ex.rest_seconds || 120,
                    notes: ex.comments,
                    completed: ex.status === "completed",
                  })) || [],
                  completed: currentData.day.status === "completed",
                  skipped: currentData.day.status === "skipped",
                } : null,
                stats: statsData ? {
                  total_workouts: statsData.completed_workouts,
                  current_streak: statsData.current_streak,
                  this_week_completed: statsData.workouts_this_week,
                  this_week_target: 4,
                } : null,
                isLoading: false,
                isOffline: false,
                lastSynced: Date.now(),
              });
            } else {
              set({
                currentPlan: null,
                currentWeek: null,
                currentDay: null,
                stats: null,
                isLoading: false,
              });
            }
          } else {
            set({
              currentPlan: null,
              currentWeek: null,
              currentDay: null,
              stats: null,
              isLoading: false,
            });
          }
        } catch (error) {
          const { currentPlan } = get();
          if (currentPlan) {
            console.log('Network error: using cached workout');
            set({ isOffline: true, isLoading: false });
            return;
          }
          set({
            error: error instanceof Error ? error.message : "Unknown error",
            isLoading: false,
          });
        }
      },

      // Complete current day (with offline support)
      completeDay: async () => {
        const { currentDay, isOffline } = get();
        if (!currentDay) return false;

        // If offline, queue the action and update UI optimistically
        if (isOffline || (typeof window !== 'undefined' && !navigator.onLine)) {
          set((state) => ({
            offlineQueue: [...state.offlineQueue, { type: 'complete', dayId: currentDay.id }],
            currentDay: state.currentDay
              ? { ...state.currentDay, completed: true }
              : null,
          }));
          get().resetExerciseProgress();
          return true;
        }

        set({ isLoading: true, error: null });
        try {
          const response = await fetch(
            `${API_BASE}/api/fitness/workouts/complete-day`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ day_id: currentDay.id }),
            }
          );

          if (!response.ok) {
            throw new Error("Failed to complete day");
          }

          await get().fetchCurrentWorkout();
          get().resetExerciseProgress();
          return true;
        } catch (error) {
          set((state) => ({
            offlineQueue: [...state.offlineQueue, { type: 'complete', dayId: currentDay.id }],
            currentDay: state.currentDay
              ? { ...state.currentDay, completed: true }
              : null,
            isOffline: true,
            isLoading: false,
          }));
          get().resetExerciseProgress();
          return true;
        }
      },

      // Skip current day (with offline support)
      skipDay: async (reason?: string) => {
        const { currentDay, isOffline } = get();
        if (!currentDay) return false;

        const skipReason = reason || "Skipped via app";

        if (isOffline || (typeof window !== 'undefined' && !navigator.onLine)) {
          set((state) => ({
            offlineQueue: [...state.offlineQueue, { type: 'skip', dayId: currentDay.id, reason: skipReason }],
            currentDay: state.currentDay
              ? { ...state.currentDay, skipped: true }
              : null,
          }));
          get().resetExerciseProgress();
          return true;
        }

        set({ isLoading: true, error: null });
        try {
          const response = await fetch(
            `${API_BASE}/api/fitness/workouts/skip-day`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                day_id: currentDay.id,
                reason: skipReason,
              }),
            }
          );

          if (!response.ok) {
            throw new Error("Failed to skip day");
          }

          await get().fetchCurrentWorkout();
          get().resetExerciseProgress();
          return true;
        } catch (error) {
          set((state) => ({
            offlineQueue: [...state.offlineQueue, { type: 'skip', dayId: currentDay.id, reason: skipReason }],
            currentDay: state.currentDay
              ? { ...state.currentDay, skipped: true }
              : null,
            isOffline: true,
            isLoading: false,
          }));
          get().resetExerciseProgress();
          return true;
        }
      },
    }),
    {
      name: "workout-storage",
      partialize: (state) => ({
        exerciseProgress: state.exerciseProgress,
        currentPlan: state.currentPlan,
        currentWeek: state.currentWeek,
        currentDay: state.currentDay,
        stats: state.stats,
        lastSynced: state.lastSynced,
        offlineQueue: state.offlineQueue,
      }),
    }
  )
);
