/** The guided tour of one solved case: fixed beats, short enough for a 30-second recording. */

export type TourBeat = "arrive" | "planet" | "evidence" | "verdict" | "twin" | "end";

export interface BeatSpec {
  id: TourBeat;
  label: string;
  /** Milliseconds before moving on by itself; null waits for the visitor. */
  durationMs: number | null;
}

export const TOUR_BEATS: readonly BeatSpec[] = [
  { id: "arrive", label: "The place", durationMs: 3200 },
  { id: "planet", label: "The planet", durationMs: 7200 },
  { id: "evidence", label: "The evidence", durationMs: 6500 },
  { id: "verdict", label: "The verdict", durationMs: 6000 },
  { id: "twin", label: "The opposite twin", durationMs: 6500 },
  { id: "end", label: "Your turn", durationMs: null },
];

export const TOUR_TICK_MS = 100;

/** The year the globe shows: the first year until the time-lapse runs, then the last. */
export function tourYear(beat: TourBeat, progress: number, first: number, last: number): number {
  if (beat === "arrive") return first;
  if (beat !== "planet") return last;
  const clamped = Math.min(1, Math.max(0, progress));
  return Math.round(first + clamped * (last - first));
}

export function beatIndex(beat: TourBeat): number {
  return TOUR_BEATS.findIndex((spec) => spec.id === beat);
}
