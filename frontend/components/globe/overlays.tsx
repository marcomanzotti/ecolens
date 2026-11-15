"use client";

import { Component, type ReactNode } from "react";
import { cn } from "cn";

import type { Location, OppositeTwin, Place, TrendMapCell, TrendMapResult } from "@/lib/api";
import { GLOBE_COLORS, TREND_ALPHA_NOT_SIGNIFICANT, trendColor, trendGradientCss } from "./colors";
import { cellLabel, signedSlope, trendMapSummary } from "./trend-summary";

interface AccessiblePanelProps {
  places: readonly Place[];
  selected: Location | null;
  onSelect: (location: Location) => void;
  onFocusPlace: (placeId: string | null) => void;
  trendMap?: TrendMapResult | null;
  twin?: OppositeTwin | null;
  onCellSelect?: (cell: TrendMapCell) => void;
  /** Cap the height of the place list (when shown over the globe). */
  compact?: boolean;
  className?: string;
}

const listButton =
  "min-h-9 w-full rounded-sm px-2 text-left text-sm hover:bg-electric focus-visible:outline-2 focus-visible:outline-neon";

/**
 * What the canvas shows, as text and buttons: the places, the selection and the
 * trend map. Hidden until it receives keyboard focus, or always shown as a fallback.
 */
export function AccessiblePanel(props: AccessiblePanelProps) {
  const { places, selected, onSelect, onFocusPlace, trendMap, twin, onCellSelect, compact, className } = props;
  const twinCells = trendMap && twin && onCellSelect ? [twin.up, twin.down] : [];
  return (
    <section aria-label="Globe: places and map" className={className}>
      <h2 className="mb-1 text-sm font-bold">Places on the globe</h2>
      <ul className={compact ? "max-h-56 overflow-y-auto" : undefined} onBlur={() => onFocusPlace(null)}>
        {places.map((place) => (
          <li key={place.id}>
            <button
              type="button"
              className={listButton}
              onFocus={() => onFocusPlace(place.id)}
              onClick={() => onSelect({ lat: place.lat, lon: place.lon, label: place.name })}
            >
              {place.name}, {place.country}
            </button>
          </li>
        ))}
      </ul>
      <p aria-live="polite" className="mt-1 text-xs">
        {selected ? `Selected: ${[selected.label, `${selected.lat.toFixed(2)}, ${selected.lon.toFixed(2)}`].filter(Boolean).join(" at ")}` : ""}
      </p>
      {trendMap ? <p className="mt-1 text-xs">{trendMapSummary(trendMap, twin)}</p> : null}
      {twinCells.map((cell) => (
        <button key={`${cell.lat}:${cell.lon}`} type="button" className={listButton} onClick={() => onCellSelect?.(cell)}>
          Open cell {cellLabel(cell, trendMap?.variable.unit ?? "")}
        </button>
      ))}
    </section>
  );
}

interface TrendLegendProps {
  map: TrendMapResult;
  showTwin: boolean;
}

/** Colour scale, units and what "significant" looks like on the globe. */
export function TrendLegend({ map, showTwin }: TrendLegendProps) {
  const max = map.summary.max_abs_slope;
  return (
    <figure className="pointer-events-none absolute bottom-2 left-2 z-30 w-44 max-w-[calc(100%-1rem)] sm:w-56 rounded-md border border-line bg-deep/85 p-2 text-xs text-white backdrop-blur-sm">
      <figcaption className="mb-1 font-bold">
        {map.variable.name}, {map.variable.unit} per decade
      </figcaption>
      <div aria-hidden="true" className="h-2.5 rounded-sm" style={{ background: trendGradientCss() }} />
      <div className="mt-0.5 flex justify-between tabular-nums">
        <span>{signedSlope(-max)}</span>
        <span>0</span>
        <span>{signedSlope(max)}</span>
      </div>
      {/* On narrow screens the key would cover the map; the text beside the globe explains it. */}
      <ul className="mt-1.5 hidden space-y-1 sm:block">
        <li className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="size-3 border-2"
            style={{ background: trendColor(max, max), borderColor: GLOBE_COLORS.significantOutline, outline: "1px solid white" }}
          />
          Significant (bright, outlined)
        </li>
        <li className="flex items-center gap-2">
          <span aria-hidden="true" className="size-3" style={{ background: GLOBE_COLORS.land }}>
            <span
              className="block size-full"
              style={{ background: trendColor(max, max), opacity: TREND_ALPHA_NOT_SIGNIFICANT }}
            />
          </span>
          Not significant (faded)
        </li>
        {showTwin ? (
          <li className="flex items-center gap-2">
            <span aria-hidden="true" className="h-0.5 w-3" style={{ background: GLOBE_COLORS.twin }} />
            Opposite twin
          </li>
        ) : null}
      </ul>
    </figure>
  );
}

export function GlobeMessage({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div role="status" className={cn("absolute inset-0 grid place-items-center p-4 text-center text-sm", className)}>
      {children}
    </div>
  );
}

interface ErrorBoundaryProps {
  fallback: ReactNode;
  children: ReactNode;
}

/** Shows `fallback` instead of crashing the page if the 3D scene throws. */
export class GlobeErrorBoundary extends Component<ErrorBoundaryProps, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
