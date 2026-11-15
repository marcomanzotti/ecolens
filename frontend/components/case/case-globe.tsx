"use client";

import { MapPin } from "lucide-react";
import type { Section as SectionState } from "@/hooks/use-case-data";
import type { Location, TrendMapCell, TrendMapResult } from "@/lib/api";
import { formatCoordinates, placeName } from "@/lib/format";
import Globe from "@/components/globe";

const NO_PLACES: readonly never[] = [];
/** Width at which the 2048 px Blue Marble is drawn in the phone locator (1° ≈ 4.4 px). */
const LOCATOR_IMAGE_WIDTH = 1600;

function cellLocation(cell: TrendMapCell): Location {
  return { lat: cell.lat, lon: cell.lon, label: null };
}

interface CaseGlobeProps {
  location: Location | null;
  trendMap: SectionState<TrendMapResult>;
  onOpenPlace: (location: Location) => void;
}

/** Wide screens: the globe stays beside the evidence, and paints the trend map once it is ready. */
export function CaseGlobe({ location, trendMap, onOpenPlace }: CaseGlobeProps) {
  const map = trendMap.state.status === "success" ? trendMap.state.data : null;
  const status =
    trendMap.state.status === "loading"
      ? "Testing every grid point around the place…"
      : map
        ? "Trend map painted. Click a cell to open a case there."
        : "Scroll to “Where it flips” to paint the trend map around the place.";

  return (
    <figure className="flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-space">
      <Globe
        className="min-h-0 flex-1"
        places={NO_PLACES}
        selected={location}
        onSelect={onOpenPlace}
        trendMap={map}
        onCellSelect={(cell) => onOpenPlace(cellLocation(cell))}
        highlightTwin={map?.opposite_twin ?? null}
      />
      <figcaption className="border-t border-line bg-deep px-4 py-3 text-sm">
        {location ? (
          <span className="flex items-baseline justify-between gap-3">
            <span className="min-w-0 truncate font-bold">{placeName(location)}</span>
            <span className="tabular shrink-0 text-muted-foreground">
              {formatCoordinates(location.lat, location.lon)}
            </span>
          </span>
        ) : null}
        <span role="status" className="mt-0.5 block text-muted-foreground">
          {status}
        </span>
      </figcaption>
    </figure>
  );
}

/**
 * Phones: a flat strip of the Blue Marble centred on the place, with a pin. Light and
 * scroll-friendly; the 3D globe stays in "Where it flips", where the trend map is painted.
 */
export function CaseLocator({ location }: { location: Location | null }) {
  if (location === null) return null;
  const width = LOCATOR_IMAGE_WIDTH;
  const x = ((location.lon + 180) / 360) * width;
  const y = ((90 - location.lat) / 180) * (width / 2);
  return (
    <figure className="overflow-hidden rounded-xl border border-line">
      <div
        aria-hidden="true"
        className="relative h-32 bg-space"
        style={{
          backgroundImage: "url(/earth/bluemarble-2048.webp)",
          backgroundSize: `${width}px ${width / 2}px`,
          backgroundRepeat: "repeat-x",
          backgroundPosition: `calc(50% + ${width / 2 - x}px) calc(50% + ${width / 4 - y}px)`,
        }}
      >
        <span className="absolute top-1/2 left-1/2 size-14 -translate-1/2 rounded-full border border-neon/70" />
        <MapPin
          className="absolute top-1/2 left-1/2 size-7 -translate-x-1/2 -translate-y-full fill-deep text-neon"
          strokeWidth={2.5}
        />
      </div>
      <figcaption className="flex items-baseline justify-between gap-3 bg-deep px-4 py-2.5 text-sm">
        <span className="min-w-0 truncate font-bold">{placeName(location)}</span>
        <span className="tabular shrink-0 text-muted-foreground">
          {formatCoordinates(location.lat, location.lon)}
        </span>
      </figcaption>
    </figure>
  );
}
