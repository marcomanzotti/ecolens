"use client";

import { MapPin, X } from "lucide-react";
import type { Location } from "@/lib/api";
import { formatCoordinates, placeName } from "@/lib/format";
import { PLACE_SEARCH_ID } from "@/components/landing/place-search";

interface ChosenPlaceProps {
  location: Location;
  onClear: () => void;
}

/** The place under investigation, as the label on a case file, with a way to change it. */
export function ChosenPlace({ location, onClear }: ChosenPlaceProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-white py-2 pr-1 pl-3 text-deep">
      <MapPin aria-hidden="true" className="size-5 shrink-0" />
      <p className="min-w-0 flex-1 leading-tight">
        <span className="block font-heading text-lg leading-tight font-black break-words">{placeName(location)}</span>
        <span className="tabular block text-sm">{formatCoordinates(location.lat, location.lon)}</span>
      </p>
      <button
        type="button"
        onClick={() => document.getElementById(PLACE_SEARCH_ID)?.focus()}
        className="min-h-11 shrink-0 cursor-pointer rounded-md px-3 text-sm font-bold underline underline-offset-4 hover:bg-deep/10"
      >
        Change
      </button>
      <button
        type="button"
        onClick={onClear}
        className="grid size-11 shrink-0 cursor-pointer place-items-center rounded-md hover:bg-deep/10"
        aria-label="Clear the place"
      >
        <X aria-hidden="true" className="size-4" />
      </button>
    </div>
  );
}
