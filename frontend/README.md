# Fitness Coach - Frontend

AI-powered fitness coach Progressive Web App built with Next.js 16 and React 19.

## Tech Stack

- **Framework**: Next.js 16.1.3 with App Router + Turbopack
- **UI Library**: React 19
- **Styling**: Tailwind CSS 3.4 with Material 3 design system
- **State Management**: Zustand 5 with persistence
- **Data Fetching**: SWR + SSE streaming
- **Icons**: Lucide React
- **TypeScript**: 5.7

## Design System

**Material 3 / Material You** inspired design:
- Large border-radius (28px for cards, full for buttons)
- Soft shadows with color tints
- Gradient backgrounds
- Floating pill navigation
- Touch-friendly (minimum 44px tap targets)
- Mobile-first responsive design

**Color Scheme:**
- Primary: Emerald/Fitness Green (`#10b981`)
- Gradients: Soft pastels
- Dark mode: Full support

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx          # Root layout with PWA meta
│   │   ├── page.tsx            # Home dashboard
│   │   ├── workout/            # Active workout page
│   │   ├── chat/               # AI chat interface
│   │   ├── plans/              # Workout plans list
│   │   └── progress/           # Progress tracking
│   ├── components/
│   │   ├── ExerciseCard.tsx    # Exercise display component
│   │   └── ToolCallBlock.tsx   # AI tool call visualization
│   ├── stores/
│   │   └── workout.ts          # Zustand store with offline support
│   └── lib/
│       └── api.ts              # API client + SSE streaming
├── public/
│   ├── manifest.json           # PWA manifest
│   ├── sw.js                   # Service Worker (manual)
│   └── icons/                  # PWA icons (192, 512, shortcuts)
└── package.json
```

## Key Features

### Offline Support
- Service Worker caching strategy:
  - Static assets: Cache first with network fallback
  - API data: Network first with cache fallback
  - Workout plans: Aggressive caching for offline access
- Offline action queue with auto-sync when online
- Optimistic UI updates

### State Management
- Zustand with localStorage persistence
- Automatic offline/online detection
- Exercise progress tracking during workouts
- Plan and stats caching

### AI Chat
- SSE (Server-Sent Events) streaming
- Tool call visualization
- Extended thinking display (Claude Agent SDK v2)
- Conversation history

### PWA Features
- Install prompt (HTTPS only)
- Standalone mode
- App shortcuts (Workout, Chat)
- Offline functionality
- Material You splash screen

## Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.local.example .env.local

# Edit .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

```bash
# Start dev server (port 3000)
npm run dev

# Type check
npx tsc --noEmit

# Lint
npm run lint
```

Open [http://localhost:3000](http://localhost:3000)

## Production Build

```bash
# Build
npm run build

# Start production server
npm start
```

Service Worker is active only in production builds and HTTPS contexts.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `""` (relative) |

In production, use relative URLs so nginx can proxy to backend.

## API Integration

### Endpoints Used

```typescript
// Workout Plans
GET  /api/fitness/plans?is_active=true&limit=1
GET  /api/fitness/plans/{id}/current
POST /api/fitness/workouts/complete-day
POST /api/fitness/workouts/skip-day
GET  /api/fitness/workouts/stats

// AI Chat
POST /api/fitness/chat  // SSE streaming
GET  /api/fitness/chat/history
```

### SSE Streaming Protocol

```typescript
// Event types
event: text          // Content chunk
event: thinking      // Extended thinking (Claude Agent SDK v2)
event: tool_start    // Tool call initiated
event: tool_result   // Tool execution result
event: done          // Stream complete
event: error         // Error occurred

// Data format (JSON)
data: {"content": "text chunk"}
data: {"tool": "get_workout_plans", "input": {...}}
data: {"tool": "complete_workout_day", "result": {...}, "success": true}
```

## PWA Setup

### Icons Required

Place in `public/icons/`:
- `icon-192.png` (192x192) - Install prompt
- `icon-512.png` (512x512) - Splash screen
- `workout-96.png` (96x96) - Workout shortcut
- `chat-96.png` (96x96) - Chat shortcut

Generate icons from a single source:
```bash
# Using ImageMagick
convert source.png -resize 192x192 icon-192.png
convert source.png -resize 512x512 icon-512.png
```

### Service Worker

Manual implementation at `public/sw.js`:
- Cache version: `fitness-coach-v1`
- Caching strategies defined per route type
- Chat endpoints bypassed (SSE streaming)
- Auto-cleanup of old caches

## Components

### ExerciseCard

Material You styled exercise card with:
- Circular checkbox
- Sets/reps badges
- Weight display (if available)
- Rest timer button
- Notes section
- Completion state styling

Props:
```typescript
interface ExerciseCardProps {
  exercise: Exercise;
  index: number;
  isCompleted: boolean;
  isActive?: boolean;
  onToggle: () => void;
  onStartRest?: () => void;
}
```

### ToolCallBlock

Collapsible AI tool call display:
- Status indicator (loading/success/error)
- Tool name formatting
- Input/result JSON display
- Expandable details

## Store Structure

### WorkoutStore (Zustand)

```typescript
interface WorkoutState {
  // Data
  currentPlan: Plan | null;
  currentWeek: Week | null;
  currentDay: Day | null;
  stats: WorkoutStats | null;

  // UI State
  isLoading: boolean;
  error: string | null;

  // Offline
  isOffline: boolean;
  offlineQueue: OfflineAction[];
  lastSynced: number | null;

  // Exercise tracking
  exerciseProgress: Record<string, boolean>;

  // Actions
  fetchCurrentWorkout: () => Promise<void>;
  completeDay: () => Promise<boolean>;
  skipDay: (reason?: string) => Promise<boolean>;
  toggleExercise: (exerciseId: string) => void;
}
```

Persisted fields:
- `exerciseProgress` - Checkbox states
- `currentPlan`, `currentWeek`, `currentDay` - Workout data
- `stats` - User statistics
- `offlineQueue` - Pending actions

## Implementation TODO

The following pages need implementation (copy from Helper PWA):

1. **Chat Page** (`/chat`)
   - Source: `/opt/helper/frontend/src/app/fitness/chat/page.tsx`
   - Features: SSE streaming, message history, tool calls

2. **Plans Page** (`/plans`)
   - Source: `/opt/helper/frontend/src/app/fitness/plans/page.tsx`
   - Features: Plan list, week/day details, plan creation

3. **Progress Page** (`/progress`)
   - Source: `/opt/helper/frontend/src/app/fitness/progress/page.tsx`
   - Features: Stats visualization, workout history

4. **Service Worker Registration Component**
   - Source: `/opt/helper/frontend/src/components/ServiceWorkerRegister.tsx`
   - Add to `layout.tsx` for auto-registration

## Browser Support

- Modern browsers (Chrome, Safari, Firefox, Edge)
- iOS Safari 14+ (PWA support)
- Android Chrome (full PWA support)

## Troubleshooting

### PWA Not Installing
1. Check HTTPS (required for Service Worker)
2. Verify icons exist (192x192, 512x512)
3. Check manifest.json is accessible
4. Open DevTools → Application → Service Workers

### SSE Streaming Not Working
1. Check nginx proxy config (`proxy_buffering off`)
2. Verify backend CORS settings
3. Check browser console for errors

### Offline Sync Issues
1. Check `offlineQueue` in localStorage
2. Verify network connectivity
3. Check Service Worker cache in DevTools

## Next Steps

1. Copy missing page implementations from Helper PWA
2. Generate PWA icons
3. Configure backend API URL
4. Set up nginx proxy for production
5. Add user authentication (if needed)
6. Implement additional features (rest timer, exercise videos, etc.)

## License

MIT License - Part of Open-Source Fitness Coach project
