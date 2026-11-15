"use client";

import type { Location } from "@/lib/api";
import { formatSigned } from "@/lib/format";
import {
  ROBUST_AGREEMENT_PCT,
  SCENARIOS,
  SCENARIO_LABELS,
  SCENARIO_WORDS,
  agreementSentence,
  projectionAt,
  type ProjectionField,
  type ProjectionMeta,
} from "@/lib/projections";
import { DatasetSwitch, Segmented } from "./dataset-switch";
import {
  PROJECTION_LAYERS,
  PROJECTION_LAYER_ORDER,
  type ProjectionLayerSpec,
  type ProjectionLayerVariable,
} from "./projection-scales";
import {
  BOTTOM_BLOCK,
  CONTROLS_PANEL,
  LEGEND_CARD,
  LEGEND_SUMMARY,
  OVERLAY_ROOT,
  TOP_BLOCK,
  TOP_SCRIM,
  TOP_TEXT,
  YEAR_TEXT,
} from "./overlay-layout";
import { scaleGradientCss } from "./timelapse-datasets";
import type { ProjectionControls } from "./use-projection-layer";
import type { TimelapseControls } from "./use-timelapse";

const MINUS = "−";
const HATCH_CSS = "repeating-linear-gradient(45deg, #F16F4C 0 3px, #07173F 3px 5px)";
const CREDIT = "CMIP6 (WCRP), incl. NASA GISS-E2-1-G";
/** Labels that fit two segmented controls side by side on a 375 px phone. */
const SHORT_VARIABLE_LABELS: Readonly<Record<ProjectionLayerVariable, string>> = { tas: "Temp.", pr: "Rain" };

function signed(value: number): string {
  if (value === 0) return "0";
  return value > 0 ? `+${value}` : `${MINUS}${Math.abs(value)}`;
}

function withUnit(value: number, unit: string): string {
  return unit === "%" ? `${formatSigned(value, 2)}%` : `${formatSigned(value, 2)} ${unit}`;
}

interface LegendProps {
  meta: ProjectionMeta;
  spec: ProjectionLayerSpec;
  scenarioLabel: string;
  models: number;
}

/** Hatching, blank areas, method and sources: open on wide screens, folded on phones. */
function LegendKey({ meta, spec, models }: Omit<LegendProps, "scenarioLabel">) {
  return (
    <>
      <p className="mt-1 flex items-center gap-2">
        <span aria-hidden="true" className="size-3 shrink-0" style={{ background: HATCH_CSS }} />
        Hatched: fewer than {ROBUST_AGREEMENT_PCT}% of models agree on the direction
      </p>
      {spec.blankNote ? <p className="mt-1">{spec.blankNote}</p> : null}
      <p className="mt-1 text-white/80">
        Median of {models} models, one run each, on a {meta.grid.step_deg}° grid, {meta.future.join("–")} vs{" "}
        {meta.baseline.join("–")}. Scenario projection, not a forecast.
      </p>
      <p className="mt-1 text-white/80 sm:text-[11px]">
        {CREDIT}
        <span aria-hidden="true" className="mx-1.5 inline-block size-[3px] rounded-full bg-current align-middle" />
        <span className="sr-only">; </span>
        Blue Marble: NASA Earth Observatory / GIBS
      </p>
    </>
  );
}

function ProjectionLegend({ meta, spec, scenarioLabel, models }: LegendProps) {
  const { scale, unit } = spec;
  return (
    <figure className={LEGEND_CARD}>
      <figcaption className="leading-tight font-bold">
        {spec.quantity}, {unit}
        <span className="hidden sm:inline">
          , {meta.future.join("–")} vs {meta.baseline.join("–")}
        </span>
        {` · ${scenarioLabel}`}
      </figcaption>
      <div className="mt-1 flex items-center gap-1">
        <span aria-hidden="true">◀</span>
        <div aria-hidden="true" className="h-2.5 flex-1 rounded-sm" style={{ background: scaleGradientCss(scale) }} />
        <span aria-hidden="true">▶</span>
      </div>
      <div className="flex justify-between px-3 tabular-nums" aria-hidden="true">
        {scale.ticks.map((tick) => (
          <span key={tick}>{signed(tick)}</span>
        ))}
      </div>
      <p className="sr-only">
        Steps of {scale.step} {unit} from {signed(scale.min)} to {signed(scale.max)} {unit}, {spec.armsInWords}; values
        beyond either end take the end colour.
      </p>
      {/* Phones: the key folds away so the globe stays visible; the colour scale stays open. */}
      <details className="sm:hidden">
        <summary className={LEGEND_SUMMARY}>Hatching, method and sources</summary>
        <LegendKey meta={meta} spec={spec} models={models} />
      </details>
      <div className="hidden sm:block">
        <LegendKey meta={meta} spec={spec} models={models} />
      </div>
    </figure>
  );
}

function PlaceReadout({ meta, field, spec, selected }: { meta: ProjectionMeta; field: ProjectionField; spec: ProjectionLayerSpec; selected: Location }) {
  const cell = projectionAt(meta, field, selected.lat, selected.lon);
  return (
    <p className="max-w-xs rounded-md border border-line bg-deep/85 p-2 text-xs backdrop-blur-sm">
      {cell ? (
        <>
          At the selected place: <strong className="tabular-nums">{withUnit(cell.median, spec.unit)}</strong> (10–90% of
          models {withUnit(cell.p10, spec.unit)} to {withUnit(cell.p90, spec.unit)}). {agreementSentence(spec.id, cell)}
        </>
      ) : (
        "The models give no value for the selected place."
      )}
    </p>
  );
}

interface ProjectionOverlayProps {
  projection: ProjectionControls;
  timelapse: TimelapseControls;
  selected: Location | null;
}

/** Title, legend and controls of the static "2050" layer, drawn over the globe. */
export function ProjectionOverlay({ projection, timelapse, selected }: ProjectionOverlayProps) {
  const { load, variable, scenario } = projection;
  const ready = load.status === "ready" ? load : null;
  // What is on screen: the last loaded field (the next one may still be loading).
  const spec = PROJECTION_LAYERS[(ready?.field.variableId as ProjectionLayerVariable | undefined) ?? variable];
  const shownScenario = ready?.field.scenario ?? scenario;
  const models = ready ? (ready.meta.variables[spec.id]?.models.length ?? 0) : 0;
  return (
    <div className={OVERLAY_ROOT}>
      <div aria-hidden="true" className={TOP_SCRIM} />
      <div className={TOP_BLOCK}>
        <div className={TOP_TEXT}>
          <p aria-hidden="true" className={YEAR_TEXT}>
            2050
          </p>
          <p className="mt-1 text-xs sm:text-sm" role="status">
            {load.status === "error" ? (
              "The model projection could not be loaded."
            ) : (
              <>
                {/* Phones: one short line; the full sentence is read by screen readers everywhere. */}
                <span aria-hidden="true" className="sm:hidden">
                  {spec.label} change by 2041–2060
                </span>
                <span className="sr-only sm:not-sr-only">
                  {`${spec.label} change by 2041–2060 under ${SCENARIO_LABELS[shownScenario]} (${SCENARIO_WORDS[shownScenario]}), median of ${models || "the"} CMIP6 models`}
                </span>
              </>
            )}
          </p>
        </div>
        {ready && selected ? (
          <div className="pointer-events-auto hidden sm:block">
            <PlaceReadout meta={ready.meta} field={ready.field} spec={spec} selected={selected} />
          </div>
        ) : null}
      </div>
      <div className={BOTTOM_BLOCK}>
        {ready ? (
          <ProjectionLegend meta={ready.meta} spec={spec} scenarioLabel={SCENARIO_LABELS[shownScenario]} models={models} />
        ) : (
          <span />
        )}
        <div className={CONTROLS_PANEL}>
          <DatasetSwitch controls={timelapse} projection={projection} />
          {/* Phones: variable and scenario share one row. */}
          <div className="flex gap-1 sm:flex-col">
            <Segmented
              legend="Projected variable"
              name="projection-variable"
              className="flex-1"
              options={PROJECTION_LAYER_ORDER.map((id) => ({
                value: id,
                label: PROJECTION_LAYERS[id].label,
                short: SHORT_VARIABLE_LABELS[id],
              }))}
              value={variable}
              onChange={(next) => projection.setVariable(next === "pr" ? "pr" : "tas")}
            />
            <Segmented
              legend="Emission scenario"
              name="projection-scenario"
              className="flex-1"
              options={SCENARIOS.map((id) => ({ value: id, label: SCENARIO_LABELS[id] }))}
              value={scenario}
              onChange={(next) => projection.setScenario(next === "ssp585" ? "ssp585" : "ssp245")}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
