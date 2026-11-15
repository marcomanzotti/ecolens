import type { CSSProperties } from "react";

/** Order of an element in the one-time load reveal (see `.reveal` in globals.css). */
export function revealStep(step: number): CSSProperties {
  return { "--reveal-step": step } as CSSProperties;
}
