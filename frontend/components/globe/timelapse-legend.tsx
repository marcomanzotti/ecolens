"use client";

import type { TimelapseMeta } from "./timelapse-data";
import { scaleGradientCss, type TimelapseDataset } from "./timelapse-datasets";
import { LEGEND_CARD, LEGEND_SUMMARY } from "./overlay-layout";
import { MISSING_COLOR, MISSING_HATCH_COLOR } from "./timelapse-palette";

const MINUS = "−";
const HATCH_CSS = `repeating-linear-gradient(45deg, ${MISSING_COLOR} 0 3px, ${MISSING_HATCH_COLOR} 3px 6px)`;

function signed(value: number): string {
  if (value === 0) return "0";
  return value > 0 ? `+${value}` : `${MINUS}${Math.abs(value)}`;
}

/** Sources, with the separator as its own element so it never sticks to a word. */
function Credits({ credit, detail }: { credit: string; detail: string | null }) {
  return (
    <p className="mt-1 text-[10px] text-white/75 sm:mt-1.5 sm:text-[11px]">
      {credit}
      {detail}
      <span aria-hidden="true" className="mx-1.5 inline-block size-[3px] rounded-full bg-current align-middle" />
      <span className="sr-only">; </span>
      Blue Marble: NASA Earth Observatory / GIBS
    </p>
  );
}

interface TimelapseLegendProps {
  dataset: TimelapseDataset;
  meta: TimelapseMeta;
  year: number;
  showAnomaly: boolean;
  showEmergence: boolean;
}

/** What every colour, line, glow and ring on the globe stands for. Always visible. */
export function TimelapseLegend({ dataset, meta, year, showAnomaly, showEmergence }: TimelapseLegendProps) {
  const first = meta.years[0];
  const cell = `${meta.grid.step_deg}°`;
  const { scale, labels, frontColors, unit } = dataset;
  const creditDetail =
    dataset.id === "temperature"
      ? ` (file of ${meta.source.file_date})`
      : meta.quantisation
        ? ` (decoded from the GIBS colour map, ±${meta.quantisation.max_error} per pixel)`
        : "";
  const quantisation = meta.quantisation ? ` · colour-map steps, ±${meta.quantisation.max_error} ${unit} per pixel` : "";
  return (
    <figure className={LEGEND_CARD}>
      <figcaption className="font-bold leading-tight">
        {dataset.quantity}, {unit} vs {meta.baseline.replace("-", "–")}
      </figcaption>
      <div className={showAnomaly ? "mt-1" : "mt-1 opacity-60"}>
        <div className="flex items-center gap-1">
          <span aria-hidden="true">◀</span>
          <div aria-hidden="true" className="h-2.5 flex-1 rounded-sm" style={{ background: scaleGradientCss(scale) }} />
          <span aria-hidden="true">▶</span>
        </div>
        <div className="flex justify-between px-3 tabular-nums">
          {scale.ticks.map((tick) => (
            <span key={tick}>{signed(tick)}</span>
          ))}
        </div>
        <p className="sr-only">
          Steps of {scale.step} {unit} from {signed(scale.min)} to {signed(scale.max)} {unit}, {dataset.armsInWords};
          values beyond either end take the end colour.{quantisation}
        </p>
      </div>
      {/* Phones: the key folds away so the globe stays visible; the colour scale stays open. */}
      <details className="mt-1 sm:hidden">
        <summary className={LEGEND_SUMMARY}>Lines, rings and sources</summary>
        <p className={showEmergence ? "mt-1" : "mt-1 opacity-60"}>
          <span aria-hidden="true" style={{ color: frontColors.up }}>━</span>
          <span aria-hidden="true" style={{ color: frontColors.down }}>━</span> border of significant {labels.up} /{" "}
          {labels.down} {first}–{year} (Mann-Kendall, {meta.test.correction}, α {meta.test.alpha}); glow one {cell}{" "}
          cell; ring = significant from this year; hatched = no data
        </p>
        <Credits credit={dataset.credit} detail={null} />
      </details>
      <ul className={showEmergence ? "mt-1.5 hidden space-y-0.5 sm:block" : "mt-1.5 hidden space-y-0.5 opacity-60 sm:block"}>
        <li className="flex items-start gap-2">
          <span aria-hidden="true" className="mt-1.5 flex w-4 shrink-0 flex-col gap-0.5">
            <span className="h-0.5" style={{ background: frontColors.up }} />
            <span className="h-0.5" style={{ background: frontColors.down }} />
          </span>
          <span>
            Border: significant {labels.up} / {labels.down} trend {first}–{year} (Mann-Kendall,{" "}
            {meta.test.correction}, α {meta.test.alpha}); glow = one {cell} cell inside it
          </span>
        </li>
        <li className="flex items-center gap-2">
          <span aria-hidden="true" className="size-3 shrink-0 rounded-full border-2" style={{ borderColor: frontColors.up }} />
          Ring: the cell became significant in this year
        </li>
        <li className="flex items-center gap-2">
          <span aria-hidden="true" className="size-3 shrink-0" style={{ background: HATCH_CSS }} />
          No data (never filled){dataset.id === "vegetation" ? "; sea, ice and desert are not measured" : ""}
        </li>
      </ul>
      <div className="hidden sm:block">
        <Credits credit={dataset.credit} detail={creditDetail} />
      </div>
    </figure>
  );
}
