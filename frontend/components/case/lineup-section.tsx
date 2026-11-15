"use client";

import { useState } from "react";
import type { Section as SectionState } from "@/hooks/use-case-data";
import type { LineupResult } from "@/lib/api";
import { formatPeriod, placeName } from "@/lib/format";
import { cn } from "@/lib/utils";
import { AsyncView } from "@/components/ui/async-view";
import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/section";
import { LineupSkeleton } from "@/components/case/case-skeleton";
import { LINEUP_GRID, LineupRow } from "@/components/case/lineup-row";

const FIRST_ROWS = 10;

interface LineupSectionProps {
  section: SectionState<LineupResult>;
  currentVariableId: string | null;
  onInvestigate: (variableId: string) => void;
}

function Lineup({
  result,
  currentVariableId,
  onInvestigate,
}: { result: LineupResult } & Omit<LineupSectionProps, "section">) {
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? result.items : result.items.slice(0, FIRST_ROWS);
  const hidden = result.items.length - shown.length;
  const { correction } = result;

  return (
    <div>
      <p className="mb-5 max-w-[68ch]">
        <span className="font-bold">{result.summary}</span>{" "}
        <span className="text-muted-foreground">
          {placeName(result.location)}, {formatPeriod(result.period)}. Ranked by the size of the
          trend relative to each variable&apos;s own year-to-year spread, so different units can be
          compared. p-values are adjusted with the {correction.label} ({correction.n_tests} tests,
          threshold {correction.alpha}).
        </span>
      </p>
      <div className="overflow-hidden rounded-xl border border-line">
        <div
          aria-hidden="true"
          className={cn(
            LINEUP_GRID,
            "hidden border-b border-line px-4 py-2.5 text-sm text-muted-foreground md:grid",
          )}
        >
          <span>#</span>
          <span>Variable</span>
          <span>{formatPeriod(result.period)}</span>
          <span>Trend</span>
          <span>p, corrected</span>
          <span>After correction</span>
        </div>
        <ol aria-label="Variables ranked by trend strength" className="divide-y divide-line">
          {shown.map((item) => (
            <LineupRow
              key={item.variable.id}
              item={item}
              isCurrent={item.variable.id === currentVariableId}
              onInvestigate={onInvestigate}
            />
          ))}
        </ol>
      </div>
      {hidden > 0 || showAll ? (
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => setShowAll((value) => !value)}
          aria-expanded={showAll}
        >
          {showAll ? "Show the top ten only" : `Show all ${result.items.length} variables`}
        </Button>
      ) : null}
    </div>
  );
}

/** Block A: every variable at this place, tested together and corrected for testing many. */
export function LineupSection({ section, currentVariableId, onInvestigate }: LineupSectionProps) {
  return (
    <Section
      id="lineup"
      title="The line-up"
      lede="Every variable in the catalogue, questioned at the same place and years. Pick one to put it on the stand."
    >
      <AsyncView
        state={section.state}
        onRetry={section.retry}
        loadingMessage="Questioning every variable at this place. This takes several seconds…"
        skeleton={<LineupSkeleton />}
        idle={<p className="text-muted-foreground">This solved case has no line-up.</p>}
      >
        {(result) => (
          <Lineup
            result={result}
            currentVariableId={currentVariableId}
            onInvestigate={onInvestigate}
          />
        )}
      </AsyncView>
    </Section>
  );
}
