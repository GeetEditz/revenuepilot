"use client";

import { useMemo, useRef, useEffect, useCallback, useState } from "react";
import {
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import {
  getForecast,
  getHealth,
  getInsights,
  simulateBudget,
  type ForecastRow,
  type HealthResponse,
  type BudgetSimulationResponse,
} from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

// ─── Cache timing constants ─────────────────────────────────────────────────
const STALE_TIME = 5 * 60 * 1000; // 5 minutes
const GC_TIME = 30 * 60 * 1000; // 30 minutes

// ─── Dev-mode cache logger ──────────────────────────────────────────────────
function logCache(key: string, hit: boolean, background?: boolean) {
  if (process.env.NODE_ENV !== "development") return;
  if (background) {
    console.log(`%c[Background Refresh] ${key} refreshed silently`, "color:#60a5fa");
  } else if (hit) {
    console.log(`%c[Cache Hit] ${key} loaded from cache`, "color:#34d399");
  } else {
    console.log(`%c[Cache Miss] Fetching ${key} from API`, "color:#fbbf24");
  }
}

// ─── useHealth ──────────────────────────────────────────────────────────────
export function useHealth(): UseQueryResult<HealthResponse> & {
  refetchHealth: () => Promise<void>;
} {
  const query = useQuery({
    queryKey: queryKeys.health,
    queryFn: async () => {
      logCache("Health", false);
      return getHealth();
    },
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    placeholderData: (prev) => {
      if (prev) logCache("Health", true);
      return prev;
    },
  });

  const refetchHealth = useCallback(async () => {
    logCache("Health", false, true);
    await query.refetch();
  }, [query]);

  return { ...query, refetchHealth };
}

// ─── useForecast ────────────────────────────────────────────────────────────
export function useForecast(dataDir?: string): UseQueryResult<ForecastRow[]> {
  const query = useQuery({
    queryKey: queryKeys.forecast(dataDir),
    queryFn: async () => {
      logCache("Forecast", false);
      return getForecast(dataDir);
    },
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    placeholderData: (prev) => {
      if (prev) logCache("Forecast", true);
      return prev;
    },
  });

  return query;
}

// ─── useInsights ────────────────────────────────────────────────────────────
export function useInsights(dataDir?: string): UseQueryResult<string[]> {
  const query = useQuery({
    queryKey: queryKeys.insights(dataDir),
    queryFn: async () => {
      logCache("Insights", false);
      return getInsights(dataDir);
    },
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    placeholderData: (prev) => {
      if (prev) logCache("Insights", true);
      return prev;
    },
  });

  return query;
}

// ─── useBudgetSimulation (with debounce) ────────────────────────────────────
export function useBudgetSimulation(
  google: number,
  meta: number,
  bing: number,
  horizon: number
): {
  simulation: BudgetSimulationResponse | null;
  isLoading: boolean;
  isDebouncing: boolean;
} {
  const DEBOUNCE_MS = 500;
  const [debouncedParams, setDebouncedParams] = useState({
    google,
    meta,
    bing,
    horizon,
  });
  const [isDebouncing, setIsDebouncing] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setIsDebouncing(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedParams({ google, meta, bing, horizon });
      setIsDebouncing(false);
    }, DEBOUNCE_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [google, meta, bing, horizon]);

  const query = useQuery({
    queryKey: queryKeys.simulation(
      debouncedParams.google,
      debouncedParams.meta,
      debouncedParams.bing,
      debouncedParams.horizon
    ),
    queryFn: async () => {
      logCache("Budget Simulation", false);
      return simulateBudget(
        debouncedParams.google,
        debouncedParams.meta,
        debouncedParams.bing,
        debouncedParams.horizon
      );
    },
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    placeholderData: (prev) => {
      if (prev) logCache("Budget Simulation", true);
      return prev;
    },
  });

  return {
    simulation: query.data ?? null,
    isLoading: query.isLoading,
    isDebouncing,
  };
}

// ─── Prefetch hook — runs on Dashboard mount ────────────────────────────────
export function usePrefetchAll() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Prefetch forecast
    queryClient.prefetchQuery({
      queryKey: queryKeys.forecast(),
      queryFn: () => getForecast(),
      staleTime: STALE_TIME,
    });

    // Prefetch insights
    queryClient.prefetchQuery({
      queryKey: queryKeys.insights(),
      queryFn: () => getInsights(),
      staleTime: STALE_TIME,
    });

    // Prefetch health
    queryClient.prefetchQuery({
      queryKey: queryKeys.health,
      queryFn: () => getHealth(),
      staleTime: STALE_TIME,
    });

    if (process.env.NODE_ENV === "development") {
      console.log(
        "%c[Prefetch] Background prefetch initiated for Forecast, Insights, Health",
        "color:#a78bfa"
      );
    }
  }, [queryClient]);
}
