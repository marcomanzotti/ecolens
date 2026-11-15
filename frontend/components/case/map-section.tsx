"use client";

import type { Ref } from "react";
import type { Section as SectionState } from "@/hooks/use-case-data";
import type { Location, TrendMapCell, TrendMapResult } from "@/lib/api";
import {
  formatCoordinates,
  formatNumber,
  formatP,
  formatPeriod,
  formatSigned,
  placeName,
} from "@/lib/format";
import Globe from "@/components/globe";
import { DirectionIcon } from "@/components/case/direction-icon";
import { AsyncView, Skeleton } from "@/components/ui/async-view";
import { Section } from "@/components/ui/section";

const NO_PLACES: readonly never[] = [];

interface MapSectionProps {
  ref: Ref<HTMLElement>;
  section: SectionState<TrendMapResult>;
  location: Location | null;
  variableName: string | null;
  onOpenPlace: (location: Location) => void;
}

function cellLocation(cell: TrendMapCell): Location {
  return { lat: cell.lat, lon: cell.lon, label: null };
}

function TwinButton({
  cell,
  unit,
  onOpen,
}: {
  cell: TrendMapCell;
  unit: string;
  onOpen: () => void;
}) {
  const rising = cell.direction === "up";
  return (
    <button
      type="button"
      onClick={onOpen}
      className="group flex w-full cursor-pointer items-start gap-3 rounded-lg border border-line-strong p-3 text-left transition-[background-color,border-color] duration-150 hover:border-white hover:bg-electric"
    >
      <DirectionIcon direction={cell.direction} className="mt-0.5" />
      <span className="tabular min-w-0 text-sm">
        <span className="block font-bold">
          {rising ? "Rising" : "Falling"} at {formatCoordinates(cell.lat, cell.lon)}
        </span>
        <span className="block text-muted-foreground">
          {formatSigned(cell.slope_per_decade ?? 0)} {unit} per decade, {formatP(cell.p_adjusted)}{" "}
          corrected
        </span>
        <span className="mt-1 block font-bold underline-offset-4 group-hover:underline">
          Open the case here
        </span>
      </span>
    </button>
  );
}

function TrendMap({
  map,
  onOpenPlace,
}: {
  map: TrendMapResult;
  onOpenPlace: (l: Location) => void;
}) {
  const twin = map.opposite_twin;
  const unit = map.variable.unit;
  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="relative -mx-5 sm:mx-0">
        <Globe
          className="h-[min(70svh,26rem)] w-full sm:h-[34rem] sm:rounded-2xl sm:border sm:border-line lg:h-[40rem]"
          places={NO_PLACES}
          // No `selected` here: with both a selection and a map at mount, the globe keeps the
          // whole-Earth zoom instead of framing the box (reported to FE-2). The box is centred
          // on the place anyway.
          selected={null}
          onSelect={onOpenPlace}
          trendMap={map}
          onCellSelect={(cell) => onOpenPlace(cellLocation(cell))}
          highlightTwin={twin}
        />
      </div>
      <div className="space-y-6">
        <p className="text-lg font-bold">{map.summary.text}</p>
        <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-xl border border-line bg-line text-center">
          {[
            { term: "Rising", value: map.summary.n_up_significant },
            { term: "Falling", value: map.summary.n_down_significant },
            { term: "Tested", value: map.summary.n_valid },
          ].map((item) => (
            <div key={item.term} className="bg-deep px-2 py-3">
              <dt className="text-sm text-muted-foreground">{item.term}</dt>
              <dd className="tabular font-heading text-2xl font-black">{item.value}</dd>
            </div>
          ))}
        </dl>
        <p className="text-sm text-muted-foreground">
          {map.variable.name}, {formatPeriod(map.period)}. One cell per grid point (
          {map.grid.lat_step}° × {map.grid.lon_step}°). Rising and falling count only cells
          significant after the {map.correction.label} across all {map.correction.n_tests} cells.
        </p>
        {twin ? (
          <div className="space-y-3 border-t border-line pt-5">
            <h3 className="font-heading text-xl font-black">The opposite twin</h3>
            <p>
              {twin.text}{" "}
              <span className="text-muted-foreground">
                About {formatNumber(twin.distance_km, 2)} km apart.
              </span>
            </p>
            <TwinButton
              cell={twin.up}
              unit={unit}
              onOpen={() => onOpenPlace(cellLocation(twin.up))}
            />
            <TwinButton
              cell={twin.down}
              unit={unit}
              onOpen={() => onOpenPlace(cellLocation(twin.down))}
            />
          </div>
        ) : (
          <p className="border-t border-line pt-5 text-muted-foreground">
            No opposite twin here: the box has no pair of significant cells moving in opposite
            directions.
          </p>
        )}
        <p className="text-sm text-muted-foreground">
          Click any cell of the map to open a case there.
        </p>
      </div>
    </div>
  );
}

/** Block B: the same test on every grid point around the place, painted on the globe. */
export function MapSection({ ref, section, location, variableName, onOpenPlace }: MapSectionProps) {
  const where = location ? placeName(location) : "this place";
  return (
    <Section
      ref={ref}
      id="map"
      title="Where it flips"
      lede={`The same test, repeated on every grid point of a 10° × 10° box around ${where}. A trend can hold for a whole region or reverse a few hundred kilometres away.`}
    >
      <AsyncView
        state={section.state}
        onRetry={section.retry}
        loadingMessage={`Testing ${variableName ? variableName.toLowerCase() : "the variable"} on every grid point around ${where}. This can take 10 seconds or more…`}
        skeleton={<Skeleton className="h-[26rem] rounded-2xl sm:h-[34rem] lg:h-[40rem]" />}
        idle={
          <div className="grid h-64 place-items-center rounded-2xl border border-dashed border-line-strong p-6 text-center text-muted-foreground">
            The map is drawn when you reach this part of the case.
          </div>
        }
      >
        {(map) => <TrendMap map={map} onOpenPlace={onOpenPlace} />}
      </AsyncView>
    </Section>
  );
}
