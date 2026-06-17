/**
 * Centralized query key factory for TanStack Query.
 * Ensures consistent cache keys across all hooks and prefetch calls.
 */
export const queryKeys = {
  health: ["health"] as const,
  forecast: (dataDir?: string) => ["forecast", dataDir ?? "./data"] as const,
  insights: (dataDir?: string) => ["insights", dataDir ?? "./data"] as const,
  simulation: (google: number, meta: number, bing: number, horizon: number) =>
    ["simulation", google, meta, bing, horizon] as const,
} as const;
