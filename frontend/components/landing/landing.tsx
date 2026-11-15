"use client";

import { useReducer } from "react";
import type { Location } from "@/lib/api";
import { revealStep } from "@/lib/motion";
import { enrichLocation, INITIAL_OPENER, openerReducer } from "@/lib/opener";
import Globe from "@/components/globe";
import { useReferenceData, usePlaces } from "@/components/providers/reference-data";
import { ErrorNotice, Skeleton } from "@/components/ui/async-view";
import { CaseOpener } from "@/components/landing/case-opener";
import { HeroHeading, HeroLede } from "@/components/landing/hero-intro";
import { ServiceBanner, useServiceUnreachable } from "@/components/site/service-banner";

function OpenerSkeleton() {
  return (
    <div role="status" aria-live="polite" className="space-y-6">
      <span className="sr-only">Loading the questions…</span>
      {[0, 1, 2].map((row) => (
        <div key={row} className="grid grid-cols-[2.5rem_1fr] gap-3" aria-hidden="true">
          <Skeleton className="h-8 w-6" />
          <div className="space-y-3">
            <Skeleton className="h-5 w-56" />
            <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/** The first screen: what the tool does, the questions, and the globe to pick a place. */
export function Landing() {
  const { catalog, retryCatalog, assistantAvailable } = useReferenceData();
  const places = usePlaces();
  const [state, dispatch] = useReducer(openerReducer, INITIAL_OPENER);
  const unreachable = useServiceUnreachable();

  const selectLocation = (location: Location) =>
    dispatch({ type: "setLocation", location: enrichLocation(location, places) });

  const globe = (
    <div
      className="reveal relative order-3 -mx-5 mt-6 sm:-mx-8 lg:col-start-2 lg:row-span-3 lg:row-start-1 lg:mx-0 lg:mt-0"
      style={revealStep(2)}
    >
      <div className="lg:sticky lg:top-4">
        <Globe
          className="h-[min(72svh,34rem)] w-full sm:h-[34rem] lg:h-[calc(100svh-6.5rem)] lg:max-h-[56rem] lg:min-h-[36rem] lg:rounded-2xl"
          places={places}
          selected={state.location}
          onSelect={selectLocation}
          timelapse
        />
        <p className="px-5 pt-2 text-center text-sm text-muted-foreground lg:pt-3">
          <span className="lg:hidden">
            Tap a marker or anywhere on Earth. Drag to turn the globe.
          </span>
          <span className="hidden rounded-full border border-line bg-deep/80 px-4 py-2 backdrop-blur-sm lg:inline-block">
            Click a marker or anywhere on Earth to choose the place. Drag to turn the globe.
          </span>
        </p>
      </div>
    </div>
  );

  const opener =
    catalog.status === "success" ? (
      <CaseOpener
        catalog={catalog.data}
        places={places}
        state={state}
        dispatch={dispatch}
        assistantAvailable={assistantAvailable}
      />
    ) : catalog.status === "error" ? (
      unreachable ? (
        <p className="text-muted-foreground">
          The questions appear here as soon as the service answers.
        </p>
      ) : (
        <ErrorNotice error={catalog.error} onRetry={retryCatalog} />
      )
    ) : (
      <OpenerSkeleton />
    );

  // DOM order is intro, questions, globe, so the keyboard reaches the questions first;
  // on phones the globe is shown between the intro and the questions.
  return (
    <>
      {unreachable ? (
        <div className="mx-auto w-full max-w-[90rem] px-5 pt-2 sm:px-8">
          <ServiceBanner consequence="Cases cannot be opened until it is back." />
        </div>
      ) : null}
      <section
        aria-labelledby="hero-heading"
        className="mx-auto grid w-full max-w-[90rem] gap-x-12 px-5 sm:px-8 lg:grid-cols-[minmax(0,36rem)_minmax(0,1fr)] lg:grid-rows-[auto_auto_1fr]"
      >
        <div className="pointer-events-none relative z-10 order-1 lg:col-span-2 lg:col-start-1 lg:row-start-1">
          <HeroHeading />
        </div>
        <div className="order-2 lg:col-start-1 lg:row-start-2">
          <HeroLede catalog={catalog.status === "success" ? catalog.data : null} />
        </div>
        <div
          id="open-a-case"
          className="reveal order-4 mt-10 scroll-mt-6 lg:col-start-1 lg:row-start-3 lg:mt-12 lg:pb-16"
          style={revealStep(3)}
        >
          <h2 className="sr-only">Open a case</h2>
          {opener}
        </div>
        {globe}
      </section>
    </>
  );
}
