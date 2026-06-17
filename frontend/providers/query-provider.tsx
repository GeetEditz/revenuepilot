"use client";

import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";

const STALE_TIME = 5 * 60 * 1000; // 5 minutes
const GC_TIME = 30 * 60 * 1000; // 30 minutes

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: STALE_TIME,
        gcTime: GC_TIME,
        retry: 1,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        refetchOnMount: false,
      },
    },
  });
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => makeQueryClient());

  // Only create the persister on the client side (window is defined)
  const [persister] = useState(() => {
    if (typeof window === "undefined") return null;
    return createSyncStoragePersister({
      storage: window.localStorage,
      key: "FORECAST_QUERY_CACHE",
    });
  });

  if (!persister) {
    // SSR fallback — just use standard provider without persistence
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  }

  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: GC_TIME,
        dehydrateOptions: {
          shouldDehydrateQuery: (query) => {
            // Only persist successful queries
            return query.state.status === "success";
          },
        },
      }}
    >
      {children}
    </PersistQueryClientProvider>
  );
}
