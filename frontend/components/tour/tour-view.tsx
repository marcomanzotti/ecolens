"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useApi } from "@/hooks/use-api";
import { api, type DemoCase, type DemoSummary } from "@/lib/api";
import Globe from "@/components/globe";
import { useReducedMotion } from "@/components/globe/use-environment";
import { DetectiveMark } from "@/components/site/site-header";
import { SITE_FOOTER_ID } from "@/components/site/site-footer";
import { AsyncView, Skeleton } from "@/components/ui/async-view";
import { TourControls } from "@/components/tour/tour-controls";
import { BeatCard } from "@/components/tour/tour-panels";
import { TOUR_BEATS, tourYear } from "@/components/tour/tour-script";
import { useTour, type TourControls as Controls } from "@/components/tour/use-tour";

const fetchDemos = async (signal: AbortSignal) => (await api.demos(signal)).demos;
const NO_PLACES = [] as const;

function isTyping(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
}

/** Space, arrows and Escape drive the tour unless a field or a focused button takes the key. */
function useTourKeys(tour: Controls, onExit: () => void) {
  useEffect(() => {
    const handle = (event: KeyboardEvent) => {
      if (isTyping(event.target) || event.metaKey || event.ctrlKey || event.altKey) return;
      const onControl = event.target instanceof HTMLElement && event.target.closest("button, a") !== null;
      if (event.key === " " && !onControl) {
        event.preventDefault();
        tour.togglePlay();
      } else if (event.key === "ArrowRight") tour.next();
      else if (event.key === "ArrowLeft") tour.previous();
      else if (event.key === "Escape") onExit();
    };
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, [tour, onExit]);
}

interface TourStageProps {
  demo: DemoCase;
  caseNumber: number;
  caseCount: number;
  onNextCase: (() => void) | null;
}

function TourStage({ demo, caseNumber, caseCount, onNextCase }: TourStageProps) {
  const router = useRouter();
  const reducedMotion = useReducedMotion();
  const tour = useTour(reducedMotion, demo.id);
  useTourKeys(tour, () => router.push("/"));
  const { start_year: first, end_year: last } = demo.case.period;
  const showMap = (tour.beat === "twin" || tour.beat === "end") && demo.trendmap !== null;
  // The planet's temperature runs only while the tour talks about it; the case's own variable
  // follows on a clean Earth, then on its own trend map.
  const showPlanet = tour.beat === "arrive" || tour.beat === "planet";
  const spec = TOUR_BEATS[tour.index];

  return (
    <>
      <Globe
        className="relative h-[46svh] w-full shrink-0 lg:absolute lg:inset-y-0 lg:right-0 lg:h-full lg:w-[62%]"
        places={NO_PLACES}
        selected={demo.case.location}
        onSelect={() => undefined}
        trendMap={showMap ? demo.trendmap : null}
        highlightTwin={showMap ? (demo.trendmap?.opposite_twin ?? null) : null}
        timelapse={showPlanet ? { year: tourYear(tour.beat, tour.progress, first, last) } : false}
      />
      <div className="relative z-10 flex min-h-0 flex-1 flex-col bg-deep lg:absolute lg:inset-y-0 lg:left-0 lg:w-[38%] lg:max-w-[36rem] lg:min-w-[26rem]">
        <div className="flex items-center justify-between gap-3 px-5 pt-4 sm:px-8 lg:pt-8">
          <Link href="/" className="flex items-center gap-2 font-heading font-black">
            <DetectiveMark className="size-6" />
            EcoLens
          </Link>
          <p className="text-sm text-muted-foreground">Guided tour</p>
        </div>
        <p className="sr-only" aria-live="polite">
          Step {tour.index + 1} of {TOUR_BEATS.length}: {spec.label}
        </p>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5 sm:px-8 lg:flex lg:flex-col lg:justify-center">
          <div
            key={`${demo.id}-${tour.beat}`}
            className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-3 motion-safe:duration-500"
          >
            <BeatCard demo={demo} beat={tour.beat} caseNumber={caseNumber} caseCount={caseCount} onNextCase={onNextCase} />
          </div>
        </div>
        <div className="border-t border-line px-5 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-8 lg:pb-8">
          <TourControls tour={tour} />
        </div>
      </div>
    </>
  );
}

function DemoLoader({ demos }: { demos: readonly DemoSummary[] }) {
  const [index, setIndex] = useState(0);
  const summary = demos[index];
  const { state, retry } = useApi(summary ? `demo-${summary.id}` : null, (signal) => api.demo(summary.id, signal));
  const nextCase = demos.length > 1 ? () => setIndex((index + 1) % demos.length) : null;
  return (
    <AsyncView state={state} onRetry={retry} loadingMessage="Opening the case file…" skeleton={<Skeleton className="m-8 h-40" />}>
      {(demo) => <TourStage demo={demo} caseNumber={index + 1} caseCount={demos.length} onNextCase={nextCase} />}
    </AsyncView>
  );
}

/**
 * The tour covers the whole screen, but the site footer is still in the page under it: make it
 * inert while the tour is open, so Tab never lands on links nobody can see (WCAG 2.4.11).
 */
function useInertFooter() {
  useEffect(() => {
    const footer = document.getElementById(SITE_FOOTER_ID);
    if (!(footer instanceof HTMLElement)) return;
    footer.inert = true;
    return () => {
      footer.inert = false;
    };
  }, []);
}

/** "Watch a solved case": the saved demos played as a guided tour over the globe. */
export function TourView() {
  const { state, retry } = useApi("demos", fetchDemos);
  useInertFooter();
  return (
    <div className="fixed inset-0 z-40 flex flex-col overflow-hidden bg-space text-white lg:block">
      <AsyncView state={state} onRetry={retry} loadingMessage="Loading the solved cases…" skeleton={<Skeleton className="m-8 h-40" />}>
        {(demos) =>
          demos.length === 0 ? (
            <p className="m-8">No solved case is available right now. <Link href="/" className="underline">Back to the start</Link></p>
          ) : (
            <DemoLoader demos={demos} />
          )
        }
      </AsyncView>
    </div>
  );
}
