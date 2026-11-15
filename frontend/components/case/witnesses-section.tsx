"use client";

import { CircleCheck, CircleDashed, CircleSlash, Scale } from "lucide-react";
import type { Section as SectionState } from "@/hooks/use-case-data";
import type { Catalog, Variable, Witness, WitnessesResult } from "@/lib/api";
import { isProductConfirmed } from "@/lib/caveats";
import {
  directionWord,
  formatInterval,
  formatNumber,
  formatPeriod,
  formatSigned,
} from "@/lib/format";
import { AsyncView, Skeleton } from "@/components/ui/async-view";
import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/section";
import { SeriesChart } from "@/components/charts/series-chart";
import { EVIDENCE_TEXT } from "@/components/case/evidence-meter";

const WITNESS_CHART_HEIGHT = 200;

const AGREEMENT = {
  agree: { label: "The witnesses agree", Icon: CircleCheck },
  partly: { label: "The witnesses partly agree", Icon: Scale },
  disagree: { label: "The witnesses disagree", Icon: CircleSlash },
  insufficient: { label: "Not enough overlap to compare", Icon: CircleDashed },
} as const;

function WitnessCard({
  witness,
  period,
}: {
  witness: Witness;
  period: WitnessesResult["common_period"];
}) {
  const { variable, trend } = witness;
  const summary = trend
    ? `${variable.name}, ${formatPeriod(period)}: ${directionWord(trend.direction).toLowerCase()}, ${formatSigned(trend.sen.slope_per_decade)} ${variable.unit} per decade.`
    : `${variable.name}, ${formatPeriod(period)}: too few years for a trend.`;
  return (
    <li className="panel min-w-0 rounded-xl p-5">
      <h3 className="font-heading text-lg font-black">{variable.name}</h3>
      <p className="text-sm text-muted-foreground">
        {variable.source.product}
        {isProductConfirmed(variable) ? "" : " (label provisional)"}, {variable.source.kind}
      </p>
      {trend ? (
        <p className="tabular mt-3">
          <span className="font-bold">
            {formatSigned(trend.sen.slope_per_decade)} {variable.unit} per decade
          </span>{" "}
          <span className="text-muted-foreground">
            (95% interval {formatInterval(trend.sen.ci95_low, trend.sen.ci95_high)}).{" "}
            {EVIDENCE_TEXT[trend.evidence].label}.
          </span>
        </p>
      ) : null}
      <div className="mt-4">
        <SeriesChart
          series={witness.series}
          fit={witness.fit}
          unit={variable.unit}
          variableName={variable.name}
          summary={summary}
          height={WITNESS_CHART_HEIGHT}
        />
      </div>
    </li>
  );
}

function Witnesses({ result, variable }: { result: WitnessesResult; variable: Variable | null }) {
  const { agreement } = result;
  const { label, Icon } = AGREEMENT[agreement.level];
  const aboutAnotherQuantity =
    variable !== null && !result.witnesses.some((witness) => witness.variable.id === variable.id);
  return (
    <div className="space-y-6">
      {aboutAnotherQuantity ? (
        <p className="max-w-[68ch] font-bold">
          {variable.name} has no second source, so this solved case calls the witnesses for a
          related quantity: {result.quantity.toLowerCase()}.
        </p>
      ) : null}
      <div className="flex flex-col gap-4 rounded-xl border border-line-strong p-5 sm:flex-row sm:items-start">
        <Icon aria-hidden="true" className="size-8 shrink-0 text-neon" />
        <div className="min-w-0">
          <p className="font-heading text-xl font-black">{label}</p>
          <p className="mt-1">{agreement.text}</p>
          <p className="tabular mt-2 text-sm text-muted-foreground">
            {result.quantity}, compared over {formatPeriod(result.common_period)}, the years both
            cover.
            {agreement.correlation !== null
              ? ` Year-to-year correlation r = ${formatNumber(agreement.correlation, 2)}.`
              : ""}
          </p>
        </div>
      </div>
      <ul className="grid gap-4 lg:grid-cols-2">
        {result.witnesses.map((witness) => (
          <WitnessCard key={witness.variable.id} witness={witness} period={result.common_period} />
        ))}
      </ul>
      {result.limitations.length > 0 ? (
        <ul className="space-y-1 text-sm text-muted-foreground">
          {result.limitations.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

interface NoWitnessesProps {
  variable: Variable | null;
  catalog: Catalog | null;
  onInvestigate: (variableId: string) => void;
}

/** Most variables have one source only: say so, and point to those that have two. */
function NoWitnesses({ variable, catalog, onInvestigate }: NoWitnessesProps) {
  const withWitnesses = catalog?.variables.filter((v) => v.witness_group !== null) ?? [];
  return (
    <div className="rounded-xl border border-dashed border-line-strong p-6">
      <p className="font-bold">
        {variable
          ? `No second source measures ${variable.name.toLowerCase()} here yet.`
          : "No witnesses for this variable yet."}
      </p>
      <p className="mt-1 max-w-[68ch] text-muted-foreground">
        A witness is another dataset that measures the same thing in a different way. In this
        catalogue, only these variables have one:
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {withWitnesses.map((v) => (
          <Button key={v.id} variant="outline" size="sm" onClick={() => onInvestigate(v.id)}>
            Investigate {v.name.toLowerCase()}
          </Button>
        ))}
      </div>
    </div>
  );
}

interface WitnessesSectionProps extends NoWitnessesProps {
  section: SectionState<WitnessesResult>;
  hasWitnesses: boolean;
}

/** Block D: independent datasets for the same quantity, and whether they tell the same story. */
export function WitnessesSection({
  section,
  hasWitnesses,
  variable,
  catalog,
  onInvestigate,
}: WitnessesSectionProps) {
  return (
    <Section
      id="witnesses"
      title="Witnesses"
      lede="A second dataset measuring the same quantity. If both show the same trend, the case is stronger."
    >
      {hasWitnesses ? (
        <AsyncView
          state={section.state}
          onRetry={section.retry}
          loadingMessage="Calling the witnesses: fetching every dataset for the same quantity."
          skeleton={
            <div className="grid gap-4 lg:grid-cols-2">
              <Skeleton className="h-80 rounded-xl" />
              <Skeleton className="h-80 rounded-xl" />
            </div>
          }
        >
          {(result) => <Witnesses result={result} variable={variable} />}
        </AsyncView>
      ) : (
        <NoWitnesses variable={variable} catalog={catalog} onInvestigate={onInvestigate} />
      )}
    </Section>
  );
}
