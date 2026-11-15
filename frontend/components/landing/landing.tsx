"use client";

import { useReducer } from "react";
import Link from "next/link";
import { Play } from "lucide-react";
import type { Location } from "@/lib/api";
import { revealStep } from "@/lib/motion";
import { enrichLocation, INITIAL_OPENER, openerReducer } from "@/lib/opener";
import Globe from "@/components/globe";
import { useReferenceData, usePlaces } from "@/components/providers/reference-data";
import { ErrorNotice, Skeleton } from "@/components/ui/async-view";
import { buttonVariants } from "@/components/ui/button";
import { AskToggle } from "@/components/landing/ask-toggle";
import { CaseOpener, OPENER_HEADING_ID } from "@/components/landing/case-opener";
import { HeroHeading, HeroLede } from "@/components/landing/hero-intro";
import { PlaceSearch } from "@/components/landing/place-search";
import { ServiceBanner, useServiceUnreachable } from "@/components/site/service-banner";

/** Moves the keyboard (and the phone's scroll) to the second step once a place is chosen. */
function focusSecondStep() {
  window.requestAnimationFrame(() => {
    const heading = document.getElementById(OPENER_HEADING_ID);
    if (!heading) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    heading.scrollIntoView({ block: "start", behavior: reduced ? "auto" : "smooth" });
    heading.focus({ preventScroll: true });
  });
}

/** First screen: the Earth, the title, one line of action; the case questions come second. */
export function Landing() {
  const { catalog, retryCatalog, assistantAvailable } = useReferenceData();
  const places = usePlaces();
  const [state, dispatch] = useReducer(openerReducer, INITIAL_OPENER);
  const unreachable = useServiceUnreachable();

  const selectLocation = (location: Location) =>
    dispatch({ type: "setLocation", location: enrichLocation(location, places) });
  const pickFromSearch = (location: Location) => {
    selectLocation(location);
    focusSecondStep();
  };

  const secondStep =
    state.location === null ? null : catalog.status === "success" ? (
      <CaseOpener catalog={catalog.data} state={state} dispatch={dispatch} />
    ) : catalog.status === "error" ? (
      unreachable ? (
        <p className="text-muted-foreground">The questions appear here as soon as the service answers.</p>
      ) : (
        <ErrorNotice error={catalog.error} onRetry={retryCatalog} />
      )
    ) : (
      <div role="status" className="space-y-3">
        <span className="sr-only">Loading the questions…</span>
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-28" />
      </div>
    );

  // DOM order: intro and search, second step, globe; on phones the globe sits between them.
  return (
    <>
      {unreachable ? (
        <div className="mx-auto w-full max-w-[90rem] px-5 pt-2 sm:px-8">
          <ServiceBanner consequence="Cases cannot be opened until it is back." />
        </div>
      ) : null}
      <section aria-labelledby="hero-heading" className="hero-space relative isolate">
        <div className="mx-auto grid w-full max-w-[90rem] grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,38rem)_minmax(0,1fr)] lg:gap-x-10">
          <div className="relative z-20 order-1 px-5 sm:px-8 lg:col-start-1 lg:row-start-1 lg:pr-0">
            <HeroHeading />
            <HeroLede catalog={catalog.status === "success" ? catalog.data : null} />
            <div className="reveal relative z-30 mt-5 flex flex-col gap-3 sm:mt-8 sm:flex-row sm:items-end" style={revealStep(2)}>
              <PlaceSearch suggested={places} onPick={pickFromSearch} className="min-w-0 flex-1" />
              <Link href="/tour" className={buttonVariants({ variant: "accent", size: "lg", className: "min-h-14 group" })}>
                <Play aria-hidden="true" className="transition-transform duration-150 ease-out group-hover:scale-110" />
                Watch a solved case
              </Link>
            </div>
            <p className="reveal mt-3 max-w-[52ch] text-sm text-muted-foreground" style={revealStep(3)}>
              Every point on Earth is a valid case: any city above 15,000 people, coordinates, or a
              <span className="lg:hidden"> tap</span>
              <span className="hidden lg:inline"> click</span> on the globe.
            </p>
            {assistantAvailable && catalog.status === "success" ? (
              <AskToggle catalog={catalog.data} onUse={(result) => {
                dispatch({ type: "applyAsk", result });
                if (result.location) focusSecondStep();
              }} />
            ) : null}
          </div>
          <div
            id="open-a-case"
            className="order-3 scroll-mt-6 px-5 sm:px-8 lg:col-start-1 lg:row-start-2 lg:pr-0 lg:pb-16"
          >
            {secondStep}
          </div>
          <div className="reveal relative order-2 mt-6 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:mt-0" style={revealStep(1)}>
            <div className="lg:sticky lg:top-0">
              <Globe
                className="h-[min(70svh,34rem)] w-full sm:h-[40rem] lg:h-[calc(100svh-5rem)] lg:min-h-[38rem]"
                places={places}
                selected={state.location}
                onSelect={selectLocation}
                timelapse
              />
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
