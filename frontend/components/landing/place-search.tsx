"use client";

import { useId, useState, type KeyboardEvent } from "react";
import { MapPin, Search } from "lucide-react";
import type { Location, Place } from "@/lib/api";
import { formatCoordinates } from "@/lib/format";
import { matchesPlace, parseCoordinates, placeToLocation } from "@/lib/opener";
import { searchPlaces, worldPlaceLabel } from "@/lib/place-search";
import { useWorldPlaces, type WorldPlacesState } from "@/hooks/use-world-places";
import { cn } from "@/lib/utils";

/** Fixed id so other controls can move focus to the search. */
export const PLACE_SEARCH_ID = "place-search";
const WORLD_LIMIT = 7;

interface Option {
  key: string;
  group: "coordinates" | "suggested" | "world";
  title: string;
  detail: string;
  location: Location;
}

function buildOptions(query: string, suggested: readonly Place[], world: WorldPlacesState): Option[] {
  const typed = parseCoordinates(query);
  const coordinates: Option[] = typed
    ? [{ key: "coords", group: "coordinates", title: `Use ${formatCoordinates(typed.lat, typed.lon)}`, detail: "Any point on Earth works", location: typed }]
    : [];
  const curated = suggested
    .filter((place) => matchesPlace(place, query))
    .slice(0, query.trim() === "" ? suggested.length : 3)
    .map<Option>((place) => ({
      key: `s-${place.id}`,
      group: "suggested",
      title: place.name,
      detail: `${place.country}, ${place.kind}`,
      location: placeToLocation(place),
    }));
  const found =
    world.status === "ready" && !typed
      ? searchPlaces(world.places, query, WORLD_LIMIT).map<Option>((place) => ({
          key: `w-${place.rank}`,
          group: "world",
          title: place.name,
          detail: `${place.country}, ${formatCoordinates(place.lat, place.lon)}`,
          location: { lat: place.lat, lon: place.lon, label: worldPlaceLabel(place) },
        }))
      : [];
  return [...coordinates, ...curated, ...found];
}

function statusText(query: string, options: readonly Option[], world: WorldPlacesState): string {
  if (world.status === "loading" && query.trim() !== "") return "Loading every city on Earth…";
  if (world.status === "error") return `${world.message} Suggested places and coordinates still work.`;
  if (options.length === 0) return query.trim() === "" ? "" : "No place matches. Try coordinates, e.g. 64.1, -21.9, or click the globe.";
  return `${options.length} ${options.length === 1 ? "place" : "places"} listed. Use the arrow keys, then Enter.`;
}

const GROUP_LABEL: Record<Option["group"], string> = {
  coordinates: "Coordinates",
  suggested: "Suggested investigations",
  world: "Cities of the world",
};

interface PlaceSearchProps {
  suggested: readonly Place[];
  onPick: (location: Location) => void;
  /** Shown as a visible label above the field. */
  label?: string;
  className?: string;
}

/** Combobox (ARIA 1.2 pattern): suggested places, any city above 15,000 people, or coordinates. */
export function PlaceSearch({ suggested, onPick, label = "Search any place on Earth", className }: PlaceSearchProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const { state: world, request } = useWorldPlaces();
  const listId = useId();
  const statusId = useId();
  const options = open ? buildOptions(query, suggested, world) : [];
  const activeIndex = Math.min(active, Math.max(0, options.length - 1));
  const status = statusText(query, options, world);

  const pick = (option: Option) => {
    onPick(option.location);
    setQuery("");
    setOpen(false);
    setActive(0);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        request();
        return;
      }
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((activeIndex + step + options.length) % Math.max(1, options.length));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (options[activeIndex]) pick(options[activeIndex]);
    } else if (event.key === "Escape") {
      if (open) setOpen(false);
      else setQuery("");
    }
  };

  const groups = (["coordinates", "suggested", "world"] as const)
    .map((group) => ({ group, items: options.map((o, i) => ({ o, i })).filter(({ o }) => o.group === group) }))
    .filter(({ items }) => items.length > 0);
  const expanded = open && options.length > 0;

  return (
    <div className={cn("relative", className)}>
      <label htmlFor={PLACE_SEARCH_ID} className="mb-2 block font-heading text-sm font-bold tracking-wide text-neon uppercase">
        {label}
      </label>
      <div className="relative">
        <Search aria-hidden="true" className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2" />
        <input
          id={PLACE_SEARCH_ID}
          type="text"
          role="combobox"
          aria-expanded={expanded}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={expanded ? `${listId}-${activeIndex}` : undefined}
          aria-describedby={statusId}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
            setActive(0);
            request();
          }}
          onFocus={() => {
            setOpen(true);
            request();
          }}
          onBlur={() => setOpen(false)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Reykjavík or 64.1, -21.9"
          autoComplete="off"
          spellCheck={false}
          enterKeyHint="search"
          className="min-h-14 w-full rounded-lg border border-line-strong bg-deep py-3 pr-4 pl-12 text-lg text-white shadow-[0_0_0_1px_rgb(0_0_0/0.2)] placeholder:text-muted-foreground hover:border-white focus-visible:border-white"
        />
      </div>
      <p id={statusId} aria-live="polite" className="sr-only">
        {status}
      </p>
      <div
        id={listId}
        role="listbox"
        aria-label="Places"
        hidden={!expanded}
        className="absolute inset-x-0 top-full z-50 mt-2 max-h-[min(24rem,60svh)] overflow-y-auto overscroll-contain rounded-lg border border-line-strong bg-deep p-1 shadow-2xl shadow-black/60"
      >
        {groups.map(({ group, items }) => (
          <div key={group} role="group" aria-labelledby={`${listId}-${group}`}>
            <p id={`${listId}-${group}`} role="presentation" className="px-3 pt-2 pb-1 text-xs font-bold tracking-wide text-muted-foreground uppercase">
              {GROUP_LABEL[group]}
            </p>
            {items.map(({ o, i }) => (
              <div
                key={o.key}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === activeIndex}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => pick(o)}
                onMouseMove={() => setActive(i)}
                className={cn(
                  "flex min-h-11 cursor-pointer items-center gap-3 rounded-md px-3 py-1.5",
                  i === activeIndex ? "bg-electric" : "",
                )}
              >
                <MapPin aria-hidden="true" className={cn("size-4 shrink-0", o.group === "suggested" ? "text-neon" : "")} />
                <span className="min-w-0 leading-tight">
                  <span className="block truncate font-bold">{o.title}</span>
                  <span className="tabular block truncate text-sm text-muted-foreground">{o.detail}</span>
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
      {open && status !== "" && options.length === 0 ? (
        <p aria-hidden="true" className="absolute inset-x-0 top-full z-50 mt-2 rounded-lg border border-line-strong bg-deep px-4 py-3 text-sm">
          {status}
        </p>
      ) : null}
    </div>
  );
}
