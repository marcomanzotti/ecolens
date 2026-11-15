"use client";

import { useCallback, useState } from "react";
import { loadWorldPlaces } from "@/lib/place-index-loader";
import type { WorldPlace } from "@/lib/place-search";

export type WorldPlacesState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; places: readonly WorldPlace[] }
  | { status: "error"; message: string };

/** The GeoNames list, requested only when `request` is first called (the search opens). */
export function useWorldPlaces(): { state: WorldPlacesState; request: () => void } {
  const [state, setState] = useState<WorldPlacesState>({ status: "idle" });

  const request = useCallback(() => {
    setState((current) => (current.status === "idle" || current.status === "error" ? { status: "loading" } : current));
    loadWorldPlaces().then(
      (places) => setState({ status: "ready", places }),
      (error: unknown) =>
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "The list of places could not be loaded.",
        }),
    );
  }, []);

  return { state, request };
}
