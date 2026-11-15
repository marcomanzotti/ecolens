"use client";

import { useId, useState, type KeyboardEvent } from "react";
import { MapPin, Search, X } from "lucide-react";
import type { Location, Place } from "@/lib/api";
import { formatCoordinates, placeName } from "@/lib/format";
import { matchesPlace, parseCoordinates, placeToLocation } from "@/lib/opener";
import { cn } from "@/lib/utils";

/** Fixed id so the form can move focus here when no place was picked. */
export const PLACE_SEARCH_ID = "place-search";
export const PLACE_ERROR_ID = "place-error";

interface WhereStepProps {
  places: readonly Place[];
  location: Location | null;
  onLocationChange: (location: Location | null) => void;
  /** Shown under the search when the visitor tried to open a case without a place. */
  missing: boolean;
}

const chip =
  "inline-flex min-h-11 items-center gap-1.5 rounded-lg border px-3 text-sm font-bold transition-[background-color,border-color,color,transform] duration-150 ease-out active:scale-[0.98]";

function samePlace(place: Place, location: Location | null): boolean {
  return location !== null && place.lat === location.lat && place.lon === location.lon;
}

/** Question 2: the chosen place, a search among suggested places, or typed coordinates. */
export function WhereStep({ places, location, onLocationChange, missing }: WhereStepProps) {
  const [query, setQuery] = useState("");
  const statusId = useId();
  const matches = places.filter((place) => matchesPlace(place, query));
  const typedCoordinates = parseCoordinates(query);

  const pick = (next: Location) => {
    onLocationChange(next);
    setQuery("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    if (typedCoordinates) pick(typedCoordinates);
    else if (matches.length > 0 && query.trim() !== "") pick(placeToLocation(matches[0]));
  };

  return (
    <fieldset className="min-w-0 space-y-3">
      <legend className="mb-1 font-heading text-base font-bold">Where?</legend>
      <p className="text-sm text-muted-foreground">
        Click anywhere on the globe, choose a suggested place, or type coordinates.
      </p>

      {location ? (
        <div className="flex items-center gap-3 rounded-lg border border-white bg-white px-3 py-2 text-deep">
          <MapPin aria-hidden="true" className="size-5 shrink-0" />
          <p className="min-w-0 flex-1 leading-tight">
            <span className="block font-bold">{placeName(location)}</span>
            <span className="tabular block text-sm">
              {formatCoordinates(location.lat, location.lon)}
            </span>
          </p>
          <button
            type="button"
            onClick={() => onLocationChange(null)}
            className="grid size-11 shrink-0 cursor-pointer place-items-center rounded-md hover:bg-deep/10"
            aria-label="Clear the place"
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        </div>
      ) : null}

      <div className="relative">
        <label htmlFor={PLACE_SEARCH_ID} className="sr-only">
          Search places or type coordinates
        </label>
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
        />
        <input
          id={PLACE_SEARCH_ID}
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search places or type coordinates, e.g. 45.4, 12.3…"
          autoComplete="off"
          enterKeyHint="search"
          aria-describedby={missing ? `${PLACE_ERROR_ID} ${statusId}` : statusId}
          aria-invalid={missing || undefined}
          className="min-h-11 w-full rounded-lg border border-line-strong bg-deep py-2 pr-3 pl-9 text-white placeholder:text-muted-foreground hover:border-white"
        />
      </div>
      {missing ? (
        <p id={PLACE_ERROR_ID} role="alert" className="font-bold text-neon">
          Pick a place first: click the globe, choose a suggestion, or type coordinates.
        </p>
      ) : null}
      <p id={statusId} aria-live="polite" className="sr-only">
        {typedCoordinates
          ? "Coordinates recognised. Press Enter to use them."
          : `${matches.length} suggested places match.`}
      </p>

      <ul className="flex flex-wrap gap-2" aria-label="Suggested places">
        {typedCoordinates ? (
          <li>
            <button
              type="button"
              onClick={() => pick(typedCoordinates)}
              className={cn(chip, "cursor-pointer border-neon text-neon hover:bg-electric")}
            >
              <MapPin aria-hidden="true" className="size-4" />
              Use {formatCoordinates(typedCoordinates.lat, typedCoordinates.lon)}
            </button>
          </li>
        ) : null}
        {matches.map((place) => {
          const active = samePlace(place, location);
          return (
            <li key={place.id}>
              <button
                type="button"
                aria-pressed={active}
                title={place.blurb}
                onClick={() => pick(placeToLocation(place))}
                className={cn(
                  chip,
                  "cursor-pointer",
                  active
                    ? "border-white bg-electric text-white"
                    : "border-line-strong hover:border-white",
                )}
              >
                {place.name}
                <span className="font-normal text-muted-foreground">{place.country}</span>
              </button>
            </li>
          );
        })}
        {matches.length === 0 && !typedCoordinates ? (
          <li className="py-2 text-sm text-muted-foreground">
            No suggested place matches. Click the globe or type coordinates instead.
          </li>
        ) : null}
      </ul>
    </fieldset>
  );
}
