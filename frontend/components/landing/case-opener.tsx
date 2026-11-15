"use client";

import type { Dispatch, FormEvent, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import type { Catalog } from "@/lib/api";
import { caseHref } from "@/lib/case-query";
import { formatPeriod, placeName, seasonLabel } from "@/lib/format";
import { toCaseQuery, type OpenerAction, type OpenerState } from "@/lib/opener";
import { Button } from "@/components/ui/button";
import { WhatStep } from "@/components/landing/what-step";
import { WhenStep } from "@/components/landing/when-step";
import { ChosenPlace } from "@/components/landing/where-step";

/** Receives focus when a place is chosen, so the keyboard lands on the next question. */
export const OPENER_HEADING_ID = "open-a-case-heading";

interface CaseOpenerProps {
  catalog: Catalog;
  state: OpenerState;
  dispatch: Dispatch<OpenerAction>;
}

function Step({ label, children }: { label: string; children: ReactNode }) {
  return (
    <li className="grid gap-2 border-t border-line pt-5 sm:grid-cols-[5.5rem_1fr] sm:gap-4">
      <span aria-hidden="true" className="font-heading text-xs font-bold tracking-[0.14em] text-neon uppercase sm:pt-1">
        {label}
      </span>
      <div className="min-w-0">{children}</div>
    </li>
  );
}

function summary(state: OpenerState, catalog: Catalog): string {
  const variable = catalog.variables.find((v) => v.id === state.variableId);
  const what = variable ? variable.name : "The strongest trend";
  const where = state.location ? placeName(state.location) : "the chosen place";
  return `${what} around ${where}, ${formatPeriod(state.period)}, ${seasonLabel(state.season).toLowerCase()}.`;
}

/** Second step, once a place is chosen: what to look at and over which years. */
export function CaseOpener({ catalog, state, dispatch }: CaseOpenerProps) {
  const router = useRouter();
  if (!state.location) return null;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    router.push(caseHref(toCaseQuery(state)));
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-labelledby={OPENER_HEADING_ID}
      className="panel mt-8 rounded-xl p-4 sm:p-6 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300"
    >
      <h2
        id={OPENER_HEADING_ID}
        tabIndex={-1}
        className="mb-4 font-heading text-xl font-black tracking-tight outline-none focus-visible:outline-2"
      >
        Open the case file
      </h2>
      <ChosenPlace location={state.location} onClear={() => dispatch({ type: "setLocation", location: null })} />
      <ol className="mt-5 space-y-5">
        <Step label="What">
          <WhatStep
            catalog={catalog}
            themes={state.themes}
            variableId={state.variableId}
            onToggleTheme={(theme, on) => dispatch({ type: "toggleTheme", theme, on })}
            onVariableChange={(variableId) => dispatch({ type: "setVariable", variableId })}
          />
        </Step>
        <Step label="When">
          <WhenStep
            catalog={catalog}
            period={state.period}
            season={state.season}
            onPeriodChange={(period) => dispatch({ type: "setPeriod", period })}
            onSeasonChange={(season) => dispatch({ type: "setSeason", season })}
          />
        </Step>
      </ol>
      <div className="mt-6 flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-[44ch] text-sm text-muted-foreground" aria-live="polite">
          {summary(state, catalog)}
        </p>
        <Button type="submit" size="lg" className="group">
          Open the case
          <ArrowRight aria-hidden="true" className="transition-transform duration-150 ease-out group-hover:translate-x-0.5" />
        </Button>
      </div>
    </form>
  );
}
