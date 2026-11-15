"use client";

import { useState, type Dispatch, type FormEvent, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import type { Catalog, Place } from "@/lib/api";
import { caseHref } from "@/lib/case-query";
import { formatPeriod, placeName, seasonLabel } from "@/lib/format";
import { toCaseQuery, type OpenerAction, type OpenerState } from "@/lib/opener";
import { Button } from "@/components/ui/button";
import { AskPanel } from "@/components/landing/ask-panel";
import { OpenerTabs, type OpenerMode } from "@/components/landing/opener-tabs";
import { WhatStep } from "@/components/landing/what-step";
import { WhenStep } from "@/components/landing/when-step";
import { PLACE_SEARCH_ID, WhereStep } from "@/components/landing/where-step";

interface CaseOpenerProps {
  catalog: Catalog;
  places: readonly Place[];
  state: OpenerState;
  dispatch: Dispatch<OpenerAction>;
  assistantAvailable: boolean;
}

function Step({ index, children }: { index: number; children: ReactNode }) {
  return (
    <li className="grid grid-cols-[2rem_1fr] gap-3 sm:grid-cols-[2.5rem_1fr]">
      <span
        aria-hidden="true"
        className="tabular font-heading text-2xl leading-none font-black text-neon sm:text-3xl"
      >
        {index}
      </span>
      <div className="min-w-0 border-b border-line pb-7">{children}</div>
    </li>
  );
}

function summary(state: OpenerState, catalog: Catalog): string {
  const variable = catalog.variables.find((v) => v.id === state.variableId);
  const what = variable ? variable.name : "The strongest trend";
  const where = state.location ? placeName(state.location) : "a place you pick";
  return `${what} around ${where}, ${formatPeriod(state.period)}, ${seasonLabel(state.season).toLowerCase()}.`;
}

/** The three guided questions (what, where, when), or a free-text question when available. */
export function CaseOpener({
  catalog,
  places,
  state,
  dispatch,
  assistantAvailable,
}: CaseOpenerProps) {
  const router = useRouter();
  const [mode, setMode] = useState<OpenerMode>("guided");
  const [missingPlace, setMissingPlace] = useState(false);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!state.location) {
      setMissingPlace(true);
      document.getElementById(PLACE_SEARCH_ID)?.focus();
      return;
    }
    router.push(caseHref(toCaseQuery(state)));
  };

  const guided = (
    <form onSubmit={submit} noValidate aria-label="Open a case">
      <ol className="space-y-7">
        <Step index={1}>
          <WhatStep
            catalog={catalog}
            themes={state.themes}
            variableId={state.variableId}
            onToggleTheme={(theme, on) => dispatch({ type: "toggleTheme", theme, on })}
            onVariableChange={(variableId) => dispatch({ type: "setVariable", variableId })}
          />
        </Step>
        <Step index={2}>
          <WhereStep
            places={places}
            location={state.location}
            missing={missingPlace && !state.location}
            onLocationChange={(location) => {
              setMissingPlace(false);
              dispatch({ type: "setLocation", location });
            }}
          />
        </Step>
        <Step index={3}>
          <WhenStep
            catalog={catalog}
            period={state.period}
            season={state.season}
            onPeriodChange={(period) => dispatch({ type: "setPeriod", period })}
            onSeasonChange={(season) => dispatch({ type: "setSeason", season })}
          />
        </Step>
      </ol>
      <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-[44ch] text-sm text-muted-foreground" aria-live="polite">
          {summary(state, catalog)}
        </p>
        <Button type="submit" size="lg" className="group">
          Open the case
          <ArrowRight
            aria-hidden="true"
            className="transition-transform duration-150 ease-out group-hover:translate-x-0.5"
          />
        </Button>
      </div>
    </form>
  );

  if (!assistantAvailable) {
    return (
      <div className="space-y-6">
        {guided}
        <p className="text-sm text-muted-foreground">
          Free-text questions are switched off right now. The three questions above cover everything
          the assistant would ask.
        </p>
      </div>
    );
  }

  return (
    <OpenerTabs mode={mode} onModeChange={setMode}>
      {mode === "guided" ? (
        guided
      ) : (
        <AskPanel
          catalog={catalog}
          onUse={(result) => {
            dispatch({ type: "applyAsk", result });
            setMode("guided");
          }}
        />
      )}
    </OpenerTabs>
  );
}
