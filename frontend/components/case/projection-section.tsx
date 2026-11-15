"use client";

import type { CaseResult, Location } from "@/lib/api";
import { formatPeriod, formatSigned, seasonLabel } from "@/lib/format";
import {
  SCENARIOS,
  SCENARIO_LABELS,
  SCENARIO_WORDS,
  agreementSentence,
  cmip6VariableFor,
  projectionAt,
  type ProjectionCell,
  type ProjectionField,
  type ProjectionMeta,
  type ScenarioId,
} from "@/lib/projections";
import { useProjections } from "@/hooks/use-projections";
import { Skeleton } from "@/components/ui/async-view";
import { Section } from "@/components/ui/section";

const FALLBACK_VARIABLES = ["tas", "pr"] as const;
// Same meanings as the globe: warm red for temperature, teal = more, brown = less (the NDVI arms).
const WARM = "#F16F4C";
const MORE = "#22A085";
const LESS = "#C98228";

function bandColor(variableId: string, median: number): string {
  if (variableId === "tas") return WARM;
  return median >= 0 ? MORE : LESS;
}
const CAPTION = "Scenario projections from CMIP6 climate models, not a forecast.";

interface ProjectionSectionProps {
  location: Location | null;
  /** POWER variable of the case; null while the line-up is choosing one. */
  variableId: string | null;
  caseResult: CaseResult | null;
}

/** Temperature changes are absolute (1 K = 1 °C); the others are % of the 1995–2014 mean. */
function unitOf(meta: ProjectionMeta, id: string): string {
  return meta.variables[id].unit === "K" ? "°C" : "%";
}

function format(value: number, unit: string): string {
  return `${formatSigned(value, 2)}${unit === "%" ? "%" : ` ${unit}`}`;
}

interface Row {
  scenario: ScenarioId;
  cell: ProjectionCell;
}

function RangeRows({ rows, unit, variableId }: { rows: Row[]; unit: string; variableId: string }) {
  const low = Math.min(0, ...rows.map((r) => r.cell.p10));
  const high = Math.max(0, ...rows.map((r) => r.cell.p90));
  const pad = (high - low) * 0.08 || 1;
  const min = low - pad;
  const span = high + pad - min;
  const at = (v: number) => `${((v - min) / span) * 100}%`;
  return (
    <ul className="space-y-6">
      {rows.map(({ scenario, cell }) => (
        <li key={scenario}>
          <p className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span className="font-bold">
              {SCENARIO_LABELS[scenario]}{" "}
              <span className="font-normal text-muted-foreground">
                ({SCENARIO_WORDS[scenario]})
              </span>
            </span>
            <span className="tabular-nums">
              <strong className="text-lg">{format(cell.median, unit)}</strong>{" "}
              <span className="text-sm text-muted-foreground">
                median; 10–90% of models {format(cell.p10, unit)} to {format(cell.p90, unit)}
              </span>
            </span>
          </p>
          <div aria-hidden="true" className="relative mt-2 h-6 rounded-sm bg-white/5">
            <span className="absolute inset-y-0 w-px bg-white/40" style={{ left: at(0) }} />
            <span
              className="absolute inset-y-1 rounded-sm opacity-80"
              style={{
                left: at(cell.p10),
                width: `calc(${at(cell.p90)} - ${at(cell.p10)})`,
                background: bandColor(variableId, cell.median),
              }}
            />
            <span
              className="absolute inset-y-0 w-1 -translate-x-1/2 rounded-sm bg-white"
              style={{ left: at(cell.median) }}
            />
          </div>
          <p className="mt-2 text-sm">
            {agreementSentence(variableId, cell)}{" "}
            <span className="text-muted-foreground">
              {cell.robust
                ? "At least 80% agree on the direction: a robust signal."
                : "Fewer than 80% agree on the direction: the models are uncertain here."}
            </span>
          </p>
        </li>
      ))}
    </ul>
  );
}

function measuredLine(caseResult: CaseResult | null, cmip6Id: string): string | null {
  if (!caseResult?.trend || cmip6VariableFor(caseResult.variable.id) !== cmip6Id) return null;
  const season = caseResult.season === "annual" ? "" : `, ${seasonLabel(caseResult.season)}`;
  const slope = `${formatSigned(caseResult.trend.sen.slope_per_decade)} ${caseResult.variable.unit} per decade`;
  return `Measured trend ${formatPeriod(caseResult.period)}${season}: ${slope} (NASA POWER, Sen's slope, from the verdict above).`;
}

interface VariableBlockProps {
  meta: ProjectionMeta;
  fields: Record<ScenarioId, ProjectionField>;
  variableId: string;
  location: Location;
  caseResult: CaseResult | null;
}

function VariableBlock({ meta, fields, variableId, location, caseResult }: VariableBlockProps) {
  const variable = meta.variables[variableId];
  const rows = SCENARIOS.flatMap((scenario) => {
    const cell = projectionAt(meta, fields[scenario], location.lat, location.lon);
    return cell ? [{ scenario, cell }] : [];
  });
  const measured = measuredLine(caseResult, variableId);
  const unit = unitOf(meta, variableId);
  return (
    <div className="min-w-0 rounded-md border border-line p-5">
      <h3 className="font-heading text-xl font-bold">{variable.name}</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Change from {meta.baseline.join("–")} to {meta.future.join("–")}
        {unit === "%" ? ", as a share of the 1995–2014 mean" : ""}
      </p>
      <div className="mt-5">
        {rows.length > 0 ? (
          <RangeRows rows={rows} unit={unit} variableId={variableId} />
        ) : (
          <p className="text-muted-foreground">
            The models give no value for this grid cell (for example over the sea, or where the
            1995–2014 amount is close to zero).
          </p>
        )}
      </div>
      {measured ? <p className="mt-5 border-t border-line pt-4 text-sm">{measured}</p> : null}
    </div>
  );
}

/** What CMIP6 climate models project for the case's place by 2041–2060, under two scenarios. */
export function ProjectionSection({ location, variableId, caseResult }: ProjectionSectionProps) {
  const mapped = cmip6VariableFor(caseResult?.variable.id ?? variableId);
  const state = useProjections(mapped ? [mapped] : [], FALLBACK_VARIABLES);
  const shown = state.status === "ready" ? Object.keys(state.fields) : [];
  const fellBack = mapped === null || (state.status === "ready" && !shown.includes(mapped));
  const modelLists =
    state.status === "ready" ? shown.map((id) => state.meta.variables[id].models) : [];
  const models = Math.max(0, ...modelLists.map((list) => list.length));
  const withGiss = modelLists.some((list) => list.some((m) => m.source_id === "GISS-E2-1-G"));

  return (
    <Section
      id="future"
      title="What climate models project"
      lede={
        <>
          <strong className="text-white">{CAPTION}</strong> Each model is run under two emission
          scenarios; the bar spans the middle 80% of models, the white mark is the median.
        </>
      }
    >
      {location === null ? (
        <p className="text-muted-foreground">Pick a place to see the projections.</p>
      ) : state.status === "loading" ? (
        <Skeleton className="h-56" />
      ) : state.status === "error" ? (
        <p role="status" className="text-muted-foreground">
          The model projections could not be loaded.
        </p>
      ) : (
        <>
          {fellBack ? (
            <p className="mb-5 text-muted-foreground">
              There is no model projection for this case&apos;s variable (the models do not publish
              it in a comparable form), so temperature and precipitation are shown instead.
            </p>
          ) : null}
          <div className={shown.length > 1 ? "grid gap-6 @4xl:grid-cols-2" : "max-w-3xl"}>
            {shown.map((id) => (
              <VariableBlock
                key={id}
                meta={state.meta}
                fields={state.fields[id]}
                variableId={id}
                location={location}
                caseResult={caseResult}
              />
            ))}
          </div>
          <p className="mt-6 max-w-[80ch] text-sm text-muted-foreground">
            {models > 0
              ? `${models} CMIP6 models (WCRP)${withGiss ? ", incl. NASA GISS-E2-1-G," : ""} `
              : "CMIP6 models (WCRP), "}
            one run each, read at the 2° grid cell containing this place. Models resolve about
            1–2.5°, are not bias-corrected, and know nothing about the local trend measured above.
          </p>
        </>
      )}
    </Section>
  );
}
