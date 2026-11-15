"use client";

import type { Section as SectionState } from "@/hooks/use-case-data";
import type { CaseResult, Emergence } from "@/lib/api";
import { formatNumber, placeName } from "@/lib/format";
import { AsyncView, Skeleton } from "@/components/ui/async-view";
import { Section } from "@/components/ui/section";
import { EmergenceChart } from "@/components/charts/emergence-chart";

export interface Headline {
  big: string;
  small: string;
}

/** The emergence in two lines: shared by this block and the verdict card. */
export function emergenceHeadline(emergence: Emergence | null): Headline {
  if (emergence === null) {
    return {
      big: "Too early to say",
      small: "Not enough years to follow the trend over time",
    };
  }
  if (emergence.status === "emerged" && emergence.emerged_year !== null) {
    return {
      big: String(emergence.emerged_year),
      small: "The year the trend became significant and stayed so",
    };
  }
  if (emergence.status === "not_yet") {
    const more = emergence.additional_years;
    return {
      big: "Not yet",
      small:
        more !== null && more > 0
          ? `Roughly ${formatNumber(more, 2)} more years of data may be needed (a rough estimate)`
          : "The trend has not stayed significant to the end of the record",
    };
  }
  return {
    big: "Too early to say",
    small: "Not enough years to follow the trend over time",
  };
}

function chartSummary(result: CaseResult, emergence: Emergence): string {
  const lead = `How the Mann-Kendall p-value of ${result.variable.name.toLowerCase()} at ${placeName(result.location)} changes as years are added, starting from ${result.period.start_year}.`;
  return emergence.emerged_year === null
    ? `${lead} It does not stay below the threshold to the end of the record.`
    : `${lead} It falls below the threshold for good in ${emergence.emerged_year}.`;
}

function Cracked({ result }: { result: CaseResult }) {
  const { emergence, variable } = result;
  if (emergence === null) {
    return (
      <p className="text-muted-foreground">
        There are too few years to follow this trend over time.
      </p>
    );
  }
  const text = emergenceHeadline(emergence);
  const alpha = result.trend?.alpha;
  return (
    <div className="grid gap-10 @3xl:grid-cols-[16rem_minmax(0,1fr)]">
      <div>
        <p className="tabular font-heading text-[clamp(3.5rem,2.5rem+4vw,6rem)] leading-none font-black tracking-tight text-neon">
          {text.big}
        </p>
        <p className="mt-3 font-bold">{text.small}</p>
        <p className="mt-4 text-muted-foreground">{emergence.explanation}</p>
        {emergence.years_needed !== null ? (
          <p className="mt-4 border-t border-line pt-4 text-sm text-muted-foreground">
            A trend of this size, against this much year-to-year noise, needs about{" "}
            <strong className="text-white">{formatNumber(emergence.years_needed, 2)} years</strong>{" "}
            of data to be detected. This is a rough estimate (after Weatherhead et al., 1998,
            adapted to yearly data), not a prediction.
          </p>
        ) : null}
      </div>
      {emergence.running.length > 0 && alpha !== undefined ? (
        <div className="min-w-0">
          <EmergenceChart
            running={emergence.running}
            emergedYear={emergence.emerged_year}
            alpha={alpha}
            unit={variable.unit}
            startYear={result.period.start_year}
            summary={chartSummary(result, emergence)}
          />
        </div>
      ) : null}
    </div>
  );
}

/** Block C: from which year the record was long enough to call the trend. */
export function EmergenceSection({ section }: { section: SectionState<CaseResult> }) {
  return (
    <Section
      id="cracked"
      title="When the case cracked"
      lede="The test is repeated on a record that grows one year at a time. The case cracks when the trend becomes significant and stays significant until today."
    >
      <AsyncView
        state={section.state}
        onRetry={section.retry}
        loadingMessage="Waiting for the evidence…"
        idle={<p className="text-muted-foreground">This block follows the verdict above.</p>}
        skeleton={
          <div className="grid gap-10 @3xl:grid-cols-[16rem_minmax(0,1fr)]">
            <Skeleton className="h-40" />
            <Skeleton className="h-64" />
          </div>
        }
      >
        {(result) => <Cracked result={result} />}
      </AsyncView>
    </Section>
  );
}
