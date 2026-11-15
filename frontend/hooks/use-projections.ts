"use client";

import { useEffect, useState } from "react";

import {
  SCENARIOS,
  loadProjectionField,
  loadProjectionMeta,
  type ProjectionField,
  type ProjectionMeta,
  type ScenarioId,
} from "@/lib/projections";

export type ProjectionsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; meta: ProjectionMeta; fields: Record<string, Record<ScenarioId, ProjectionField>> };

// Static files: loaded once per page view and shared by every component that asks.
let metaPromise: Promise<ProjectionMeta> | null = null;
const fieldPromises = new Map<string, Promise<ProjectionField>>();

export function projectionMeta(): Promise<ProjectionMeta> {
  metaPromise ??= loadProjectionMeta().catch((error: unknown) => {
    metaPromise = null; // let a later attempt retry
    throw error;
  });
  return metaPromise;
}

export function projectionField(meta: ProjectionMeta, variableId: string, scenario: ScenarioId): Promise<ProjectionField> {
  const key = `${variableId}:${scenario}`;
  let promise = fieldPromises.get(key);
  if (!promise) {
    promise = loadProjectionField(meta, variableId, scenario);
    promise.catch(() => fieldPromises.delete(key));
    fieldPromises.set(key, promise);
  }
  return promise;
}

/**
 * Both scenarios of the given CMIP6 variables (those missing from meta.json are skipped); when
 * none of them is available, the `fallback` variables are loaded instead.
 */
export function useProjections(variableIds: readonly string[], fallback: readonly string[] = []): ProjectionsState {
  const key = `${variableIds.join(",")}|${fallback.join(",")}`;
  const [state, setState] = useState<{ key: string; value: ProjectionsState } | null>(null);
  useEffect(() => {
    let cancelled = false;
    const [ids, spare] = key.split("|").map((part) => part.split(",").filter(Boolean));
    (async () => {
      const meta = await projectionMeta();
      const wanted = ids.filter((id) => id in meta.variables);
      const available = wanted.length > 0 ? wanted : spare.filter((id) => id in meta.variables);
      const entries = await Promise.all(
        available.map(async (id) => {
          const pair = await Promise.all(SCENARIOS.map((scenario) => projectionField(meta, id, scenario)));
          return [id, { ssp245: pair[0], ssp585: pair[1] }] as const;
        }),
      );
      return { status: "ready" as const, meta, fields: Object.fromEntries(entries) };
    })().then(
      (value) => !cancelled && setState({ key, value }),
      (error: unknown) =>
        !cancelled &&
        setState({
          key,
          value: { status: "error", message: error instanceof Error ? error.message : "Could not load the projections." },
        }),
    );
    return () => {
      cancelled = true;
    };
  }, [key]);
  return state && state.key === key ? state.value : { status: "loading" };
}
