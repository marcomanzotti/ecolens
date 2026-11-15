"use client";

import { createContext, use, useMemo, type ReactNode } from "react";
import { useApi, type AsyncState } from "@/hooks/use-api";
import { api, type Catalog, type Health, type Place, type Variable } from "@/lib/api";

/** Data every page needs and that never changes during a visit. */
interface ReferenceData {
  health: AsyncState<Health>;
  catalog: AsyncState<Catalog>;
  places: AsyncState<readonly Place[]>;
  retryCatalog: () => void;
  retryPlaces: () => void;
  /** Retry everything that failed, e.g. after the service came back. */
  retryAll: () => void;
  /** Variable from the catalog, or null while the catalog is loading or unknown id. */
  findVariable: (id: string | null) => Variable | null;
  /** True only when /health says the free-text assistant works. */
  assistantAvailable: boolean;
}

const ReferenceDataContext = createContext<ReferenceData | null>(null);

const fetchHealth = (signal: AbortSignal) => api.health(signal);
const fetchCatalog = (signal: AbortSignal) => api.catalog(signal);
const fetchPlaces = async (signal: AbortSignal) => (await api.places(signal)).places;

export function ReferenceDataProvider({ children }: { children: ReactNode }) {
  const health = useApi("health", fetchHealth);
  const catalog = useApi("catalog", fetchCatalog);
  const places = useApi("places", fetchPlaces);

  const value = useMemo<ReferenceData>(() => {
    const variables = catalog.state.status === "success" ? catalog.state.data.variables : [];
    return {
      health: health.state,
      catalog: catalog.state,
      places: places.state,
      retryCatalog: catalog.retry,
      retryPlaces: places.retry,
      retryAll: () => {
        if (health.state.status === "error") health.retry();
        if (catalog.state.status === "error") catalog.retry();
        if (places.state.status === "error") places.retry();
      },
      findVariable: (id) => (id === null ? null : (variables.find((v) => v.id === id) ?? null)),
      assistantAvailable:
        health.state.status === "success" && health.state.data.assistant_available,
    };
  }, [health, catalog, places]);

  return <ReferenceDataContext value={value}>{children}</ReferenceDataContext>;
}

export function useReferenceData(): ReferenceData {
  const value = use(ReferenceDataContext);
  if (value === null) {
    throw new Error("useReferenceData must be used inside <ReferenceDataProvider>.");
  }
  return value;
}

/** The places list, or an empty list while it loads or if it failed. */
export function usePlaces(): readonly Place[] {
  const { places } = useReferenceData();
  return places.status === "success" ? places.data : [];
}
