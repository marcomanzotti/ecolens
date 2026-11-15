"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight, Pause, Play, X } from "lucide-react";
import { TOUR_BEATS } from "@/components/tour/tour-script";
import type { TourControls as Controls } from "@/components/tour/use-tour";
import { cn } from "@/lib/utils";

const iconButton =
  "grid size-11 shrink-0 cursor-pointer place-items-center rounded-full border border-line-strong transition-[background-color,transform] duration-150 ease-out hover:bg-electric active:scale-[0.96] disabled:pointer-events-none disabled:opacity-40";

/** Progress by beat, play/pause, back, next, exit. Keys: Space, arrows, Escape. */
export function TourControls({ tour }: { tour: Controls }) {
  const last = tour.index === TOUR_BEATS.length - 1;
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={tour.previous}
        disabled={tour.index === 0}
        aria-label="Previous step"
        aria-keyshortcuts="ArrowLeft"
        className={iconButton}
      >
        <ChevronLeft aria-hidden="true" className="size-5" />
      </button>
      <button
        type="button"
        onClick={last ? tour.restart : tour.togglePlay}
        aria-label={last ? "Watch again" : tour.playing ? "Pause the tour" : "Play the tour"}
        aria-keyshortcuts="Space"
        className="grid size-12 shrink-0 cursor-pointer place-items-center rounded-full bg-white text-deep transition-transform duration-150 ease-out active:scale-[0.96]"
      >
        {tour.playing ? <Pause aria-hidden="true" className="size-5" /> : <Play aria-hidden="true" className="size-5" />}
      </button>
      <button
        type="button"
        onClick={tour.next}
        disabled={last}
        aria-label="Next step"
        aria-keyshortcuts="ArrowRight"
        className={iconButton}
      >
        <ChevronRight aria-hidden="true" className="size-5" />
      </button>
      <ol aria-label="Steps of the tour" className="mx-2 flex min-w-0 flex-1 gap-1">
        {TOUR_BEATS.map((beat, i) => (
          <li key={beat.id} className="min-w-0 flex-1" aria-current={i === tour.index ? "step" : undefined}>
            <span className="sr-only">{beat.label}</span>
            <span aria-hidden="true" className="block h-1 overflow-hidden rounded-full bg-white/20">
              <span
                className={cn("block h-full origin-left rounded-full bg-neon", i > tour.index && "scale-x-0")}
                style={i === tour.index ? { transform: `scaleX(${tour.progress})`, transition: "transform 100ms linear" } : undefined}
              />
            </span>
          </li>
        ))}
      </ol>
      <Link href="/" aria-label="Exit the tour" aria-keyshortcuts="Escape" className={iconButton}>
        <X aria-hidden="true" className="size-5" />
      </Link>
    </div>
  );
}
