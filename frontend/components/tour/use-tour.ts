"use client";

import { useEffect, useState } from "react";
import { TOUR_BEATS, TOUR_TICK_MS, type TourBeat } from "@/components/tour/tour-script";

export interface TourState {
  beat: TourBeat;
  index: number;
  /** 0 to 1 inside the current beat. */
  progress: number;
  playing: boolean;
}

export interface TourControls extends TourState {
  togglePlay: () => void;
  next: () => void;
  previous: () => void;
  restart: () => void;
}

/**
 * Clock of the tour. It ticks only while playing; with reduced motion it starts paused and the
 * visitor moves beat by beat. `resetKey` (the case id) starts the tour over.
 */
export function useTour(reducedMotion: boolean, resetKey: string): TourControls {
  const [position, setPosition] = useState({ key: resetKey, index: 0, elapsed: 0 });
  const [playRequest, setPlayRequest] = useState<boolean | null>(null);
  const current = position.key === resetKey ? position : { key: resetKey, index: 0, elapsed: 0 };
  const spec = TOUR_BEATS[current.index];
  const playing = (playRequest ?? !reducedMotion) && spec.durationMs !== null;

  useEffect(() => {
    if (!playing || spec.durationMs === null) return;
    const duration = spec.durationMs;
    const timer = window.setInterval(() => {
      setPosition((now) => {
        const base = now.key === resetKey ? now : { key: resetKey, index: 0, elapsed: 0 };
        const elapsed = base.elapsed + TOUR_TICK_MS;
        if (elapsed < duration) return { ...base, elapsed };
        return { ...base, index: Math.min(base.index + 1, TOUR_BEATS.length - 1), elapsed: 0 };
      });
    }, TOUR_TICK_MS);
    return () => window.clearInterval(timer);
  }, [playing, spec.durationMs, resetKey]);

  const goTo = (index: number) =>
    setPosition({ key: resetKey, index: Math.max(0, Math.min(index, TOUR_BEATS.length - 1)), elapsed: 0 });

  return {
    beat: spec.id,
    index: current.index,
    progress: spec.durationMs ? current.elapsed / spec.durationMs : 1,
    playing,
    togglePlay: () => setPlayRequest(!playing),
    next: () => goTo(current.index + 1),
    previous: () => goTo(current.index - 1),
    restart: () => {
      goTo(0);
      setPlayRequest(!reducedMotion);
    },
  };
}
