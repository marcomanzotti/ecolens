"use client";

import { useEffect, useState } from "react";

import type { ProjectionField, ProjectionMeta, ScenarioId } from "@/lib/projections";
import { projectionField, projectionMeta } from "@/hooks/use-projections";
import type { ProjectionLayerVariable } from "./projection-scales";

export type ProjectionLoad =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; meta: ProjectionMeta; field: ProjectionField };

export interface ProjectionControls {
  /** True when the "2050" map replaces the time-lapse. */
  active: boolean;
  setActive: (active: boolean) => void;
  variable: ProjectionLayerVariable;
  setVariable: (variable: ProjectionLayerVariable) => void;
  scenario: ScenarioId;
  setScenario: (scenario: ScenarioId) => void;
  load: ProjectionLoad;
}

/** State of the static "2050" layer; the files are fetched the first time it is shown. */
export function useProjectionLayer(enabled: boolean): ProjectionControls {
  const [active, setActive] = useState(false);
  const [variable, setVariable] = useState<ProjectionLayerVariable>("tas");
  const [scenario, setScenario] = useState<ScenarioId>("ssp245");
  const key = `${variable}:${scenario}`;
  const [loaded, setLoaded] = useState<{ key: string; load: ProjectionLoad } | null>(null);

  useEffect(() => {
    if (!enabled || !active) return;
    let cancelled = false;
    projectionMeta()
      .then(async (meta) => ({ meta, field: await projectionField(meta, variable, scenario) }))
      .then(
        ({ meta, field }) => !cancelled && setLoaded({ key, load: { status: "ready", meta, field } }),
        (error: unknown) =>
          !cancelled &&
          setLoaded({
            key,
            load: { status: "error", message: error instanceof Error ? error.message : "The projection could not be loaded." },
          }),
      );
    return () => {
      cancelled = true;
    };
  }, [enabled, active, variable, scenario, key]);

  // While another variable or scenario loads, the previous map stays on screen.
  const load: ProjectionLoad = loaded ? loaded.load : { status: "loading" };
  return { active: active && enabled, setActive, variable, setVariable, scenario, setScenario, load };
}
