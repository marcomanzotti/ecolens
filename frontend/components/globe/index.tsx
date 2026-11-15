"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { cn } from "cn";

import { AccessiblePanel, GlobeErrorBoundary, GlobeMessage, TrendLegend } from "./overlays";
import type { GlobeProps } from "./types";
import { TimelapseOverlay } from "./timelapse-overlay";
import { useReducedMotion, useWebGLSupport } from "./use-environment";
import { useTimelapse } from "./use-timelapse";

// three.js runs in the browser only: the scene is never rendered on the server.
const GlobeScene = dynamic(() => import("./scene"), {
  ssr: false,
  loading: () => <GlobeMessage>Loading the globe…</GlobeMessage>,
});

const PANEL_HIDDEN =
  "sr-only focus-within:not-sr-only focus-within:absolute focus-within:top-2 focus-within:left-2 focus-within:z-40 focus-within:w-72 focus-within:max-w-[calc(100%-1rem)] focus-within:rounded-md focus-within:border focus-within:border-line-strong focus-within:bg-deep focus-within:p-3";
const PANEL_SHOWN = "relative z-10 mx-auto max-w-sm p-4";

/**
 * 3D globe: pick a place, see a trend map painted on the Earth.
 * Fills its container: give it a size through `className` (e.g. "h-[60vh] w-full").
 */
export default function Globe(props: GlobeProps) {
  const { places, selected, onSelect, trendMap, onCellSelect, highlightTwin, timelapse, className } = props;
  const reducedMotion = useReducedMotion();
  const webgl = useWebGLSupport();
  const timelapseOn = Boolean(timelapse);
  const autoplay = typeof timelapse === "object" ? timelapse.autoplay !== false : timelapseOn;
  const controls = useTimelapse(timelapseOn && webgl === true, autoplay, reducedMotion);
  const timelapseScene =
    timelapseOn && controls.load.status === "ready" && controls.year !== null
      ? { data: controls.load.data, year: controls.year, layers: controls.layers }
      : null;
  const [contextLost, setContextLost] = useState(false);
  const [focusedPlaceId, setFocusedPlaceId] = useState<string | null>(null);

  const failure =
    webgl === false
      ? "This browser cannot show the 3D globe (WebGL is not available)."
      : contextLost
        ? "The 3D globe stopped working (the graphics context was lost)."
        : null;

  const panel = (panelClass: string, compact: boolean) => (
    <AccessiblePanel
      places={places}
      selected={selected}
      onSelect={onSelect}
      onFocusPlace={setFocusedPlaceId}
      trendMap={trendMap}
      twin={highlightTwin}
      onCellSelect={onCellSelect}
      compact={compact}
      className={panelClass}
    />
  );
  const fallback = (reason: string) => (
    <div className="absolute inset-0 overflow-y-auto">
      <p role="alert" className="p-4 pb-0 text-center text-sm">
        {reason} Pick a place from the list instead.
      </p>
      {panel(PANEL_SHOWN, false)}
    </div>
  );

  return (
    <div className={cn("relative isolate overflow-hidden bg-deep text-white", className)}>
      {failure ? (
        fallback(failure)
      ) : (
        <>
          <GlobeErrorBoundary fallback={fallback("The 3D globe could not start.")}>
            <div className="absolute inset-0" aria-hidden="true">
              {webgl === null ? (
                <GlobeMessage>Loading the globe…</GlobeMessage>
              ) : (
                <GlobeScene
                  places={places}
                  selected={selected}
                  onSelect={onSelect}
                  trendMap={trendMap}
                  onCellSelect={onCellSelect}
                  highlightTwin={highlightTwin}
                  timelapse={timelapseScene}
                  focusedPlaceId={focusedPlaceId}
                  reducedMotion={reducedMotion}
                  onContextLost={() => setContextLost(true)}
                />
              )}
            </div>
          </GlobeErrorBoundary>
          {panel(PANEL_HIDDEN, true)}
          {timelapseOn ? <TimelapseOverlay controls={controls} selected={selected} /> : null}
          {trendMap ? <TrendLegend map={trendMap} showTwin={Boolean(highlightTwin)} /> : null}
        </>
      )}
    </div>
  );
}

export type { GlobeProps } from "./types";
