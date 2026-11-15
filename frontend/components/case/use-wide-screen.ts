"use client";

import { useSyncExternalStore } from "react";

/** Same width as Tailwind's `lg` breakpoint: from here the case gets a globe beside it. */
const WIDE_QUERY = "(min-width: 64rem)";

function subscribe(onChange: () => void): () => void {
  const media = window.matchMedia(WIDE_QUERY);
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

const readWide = () => window.matchMedia(WIDE_QUERY).matches;
const readOnServer = () => false;

/**
 * True on screens wide enough for the two-column case file. Used to mount only one 3D globe:
 * the side globe on wide screens, the globe inside "Where it flips" on phones.
 */
export function useWideScreen(): boolean {
  return useSyncExternalStore(subscribe, readWide, readOnServer);
}
