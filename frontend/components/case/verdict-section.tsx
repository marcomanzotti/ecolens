"use client";

import type { AsyncState } from "@/hooks/use-api";
import type { Section as SectionState } from "@/hooks/use-case-data";
import type { CaseResult, LineupResult } from "@/lib/api";
import { CONTRACT_ALPHA, isProductConfirmed } from "@/lib/caveats";
import { directionWord, formatPeriod, formatSigned, placeName, seasonLabel } from "@/lib/format";
import { AsyncView, ErrorNotice, LoadingNotice } from "@/components/ui/async-view";
import { SeriesChart } from "@/components/charts/series-chart";
import { TrendStats } from "@/components/case/trend-stats";
import { VerdictPanel } from "@/components/case/verdict-panel";
import { VerdictSkeleton } from "@/components/case/case-skeleton";

interface VerdictSectionProps {
  section: SectionState<CaseResult>;
  variableFromLineup: boolean;
  /** No variable yet: the line-up is choosing one. */
  waitingForLineup: boolean;
  lineupState: AsyncState<LineupResult>;
}

function chartSummary(result: CaseResult): string {
  const where = `${placeName(result.location)}, ${formatPeriod(result.period)}, ${seasonLabel(result.season).toLowerCase()}`;
  if (!result.trend)
    return `Yearly ${result.variable.name.toLowerCase()} at ${where}. Too few years for a trend.`;
  return `Yearly ${result.variable.name.toLowerCase()} at ${where}. ${directionWord(result.trend.direction)} by ${formatSigned(result.trend.ols.slope_per_decade)} ${result.variable.unit} per decade along the fitted line.`;
}

function Evidence({ result }: { result: CaseResult }) {
  const { variable, trend } = result;
  return (
    <div className="mt-14 grid gap-10 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="min-w-0">
        <h3 className="mb-4 font-heading text-2xl font-black">The evidence, year by year</h3>
        <SeriesChart
          series={result.series}
          fit={result.fit}
          unit={variable.unit}
          variableName={variable.name}
          summary={chartSummary(result)}
        />
      </div>
      <aside aria-label="What is measured" className="space-y-5 lg:pt-12">
        <div>
          <h3 className="font-heading text-lg font-bold">What is measured</h3>
          <p className="mt-1">{variable.definition}</p>
        </div>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
          <dt className="text-muted-foreground">Unit</dt>
          <dd>{variable.unit}</dd>
          <dt className="text-muted-foreground">Product</dt>
          <dd>
            {variable.source.product}
            {isProductConfirmed(variable) ? "" : " (label provisional)"}
          </dd>
          <dt className="text-muted-foreground">Kind</dt>
          <dd className="capitalize">{variable.source.kind}</dd>
          <dt className="text-muted-foreground">Served by</dt>
          <dd>
            {variable.source.url ? (
              <a
                href={variable.source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-4 hover:text-neon"
              >
                {variable.source.provider}
              </a>
            ) : (
              variable.source.provider
            )}
          </dd>
        </dl>
      </aside>
      {trend ? (
        <div className="lg:col-span-2">
          <h3 className="sr-only">Statistics behind the verdict</h3>
          <TrendStats trend={trend} />
        </div>
      ) : null}
    </div>
  );
}

/** The verdict in plain words, then the series and every number behind it. */
export function VerdictSection({
  section,
  variableFromLineup,
  waitingForLineup,
  lineupState,
}: VerdictSectionProps) {
  const body = waitingForLineup ? (
    lineupState.status === "error" ? (
      <ErrorNotice error={lineupState.error} className="max-w-2xl" />
    ) : lineupState.status === "success" ? (
      <p className="max-w-2xl rounded-xl border border-line-strong p-5">
        No variable has usable data here, so there is nothing to put on the stand. Try another place
        or period.
      </p>
    ) : (
      <LoadingNotice message="Calling the line-up to find the strongest trend here. Every variable is tested, so this takes a few seconds…">
        <VerdictSkeleton />
      </LoadingNotice>
    )
  ) : (
    <AsyncView
      state={section.state}
      onRetry={section.retry}
      loadingMessage="Fetching the yearly record from NASA POWER and testing it. This takes a few seconds…"
      skeleton={<VerdictSkeleton />}
    >
      {(result) => (
        <>
          <VerdictPanel
            result={result}
            alpha={result.trend?.alpha ?? CONTRACT_ALPHA}
            pickedByLineup={variableFromLineup}
          />
          <Evidence result={result} />
        </>
      )}
    </AsyncView>
  );

  return (
    <section id="verdict" aria-labelledby="verdict-heading" className="scroll-mt-24">
      <h2 id="verdict-heading" className="sr-only">
        Verdict and evidence
      </h2>
      {body}
    </section>
  );
}
