"use client";

import type { CellDetail, TimelapseMeta } from "./timelapse-data";
import type { TimelapseDataset } from "./timelapse-datasets";

const MINUS = "−";
const SPARK_WIDTH = 120;
const SPARK_HEIGHT = 32;
const SPARK_PAD = 2;

function signed(value: number, digits: number): string {
  const text = Math.abs(value).toFixed(digits);
  if (Number(text) === 0) return text;
  return value > 0 ? `+${text}` : `${MINUS}${text}`;
}

function coordinates(lat: number, lon: number): string {
  return `${Math.abs(lat)}°${lat >= 0 ? "N" : "S"}, ${Math.abs(lon)}°${lon >= 0 ? "E" : "W"}`;
}

/** The cell's annual anomalies, one point per year (gaps stay gaps), and the year on screen. */
function Sparkline({ detail, firstYear }: { detail: CellDetail; firstYear: number }) {
  const values = detail.series.filter((v): v is number => v !== null);
  if (values.length < 2) return null;
  const min = Math.min(0, ...values);
  const max = Math.max(0, ...values);
  const span = max - min || 1;
  const x = (i: number) => SPARK_PAD + (i / (detail.series.length - 1)) * (SPARK_WIDTH - 2 * SPARK_PAD);
  const y = (v: number) => SPARK_HEIGHT - SPARK_PAD - ((v - min) / span) * (SPARK_HEIGHT - 2 * SPARK_PAD);
  const path = detail.series
    .map((v, i) => (v === null ? null : `${i > 0 && detail.series[i - 1] !== null ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`))
    .filter(Boolean)
    .join(" ");
  const current = detail.year - firstYear;
  return (
    <svg aria-hidden="true" width={SPARK_WIDTH} height={SPARK_HEIGHT} className="mt-1 block">
      <line x1={0} x2={SPARK_WIDTH} y1={y(0)} y2={y(0)} stroke="currentColor" strokeOpacity={0.3} />
      <path d={path} fill="none" stroke="currentColor" strokeWidth={1.5} />
      <line x1={x(current)} x2={x(current)} y1={0} y2={SPARK_HEIGHT} stroke="#EAFE07" strokeWidth={1} />
    </svg>
  );
}

interface TimelapseCellProps {
  detail: CellDetail;
  dataset: TimelapseDataset;
  meta: TimelapseMeta;
}

/** The grid cell under the selected place: values read from the data files. */
export function TimelapseCell({ detail, dataset, meta }: TimelapseCellProps) {
  const firstYear = meta.years[0];
  const lastYear = meta.years[meta.years.length - 1];
  const { unit, scale } = dataset;
  const step = `${meta.grid.step_deg}°`;
  const trend =
    detail.slopePerDecade === null
      ? "not tested"
      : `${signed(detail.slopePerDecade, scale.digits)} ${unit} per decade ${firstYear}–${lastYear}, ${detail.direction === 0 ? "not significant" : "significant"}`;
  const emerged =
    detail.emergedYear === null ? "not significant by " + lastYear : `significant from the window ending ${detail.emergedYear}`;
  return (
    <section
      aria-label="Selected grid cell"
      className="rounded-md border border-line bg-deep/85 p-2 text-[11px] leading-snug text-white backdrop-blur-sm sm:w-60 sm:text-xs"
    >
      <h3 className="font-bold">
        Cell {coordinates(detail.lat, detail.lon)} ({step} × {step})
      </h3>
      <p className="tabular-nums">
        {detail.year}:{" "}
        {detail.anomaly === null
          ? "no data"
          : `${signed(detail.anomaly, scale.digits)} ${unit} vs ${meta.baseline.replace("-", "–")}`}
      </p>
      <p className="tabular-nums">Trend: {trend}</p>
      <p>Emergence: {emerged}</p>
      <Sparkline detail={detail} firstYear={firstYear} />
    </section>
  );
}
