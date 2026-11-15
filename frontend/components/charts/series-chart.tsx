"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FitPoint, SeriesPoint } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import {
  AXIS_LINE,
  AXIS_TICK,
  AXIS_TITLE_OFFSET,
  AXIS_TITLE_ROOM,
  CHART_MARGIN,
  ChartFigure,
  TooltipBox,
  type LegendEntry,
} from "@/components/charts/chart-figure";

interface SeriesChartProps {
  series: readonly SeriesPoint[];
  fit: readonly FitPoint[];
  unit: string;
  variableName: string;
  summary: string;
  /** Pixel height of the plot area; smaller for side-by-side witnesses. */
  height?: number;
  /** Year the trend became statistically clear (emergence, from the API), marked on the chart. */
  crackedYear?: number | null;
}

interface SeriesRow {
  year: number;
  value: number | null;
  fit: number | null;
  band: [number, number] | null;
}

const CHART_HEIGHT = 320;

const LEGEND: readonly LegendEntry[] = [
  {
    label: "Yearly value",
    swatch: (
      <svg width="28" height="10" viewBox="0 0 28 10">
        <line x1="0" y1="5" x2="28" y2="5" stroke="var(--chart-series)" strokeWidth="1.5" />
        <circle cx="14" cy="5" r="3" fill="var(--chart-series)" />
      </svg>
    ),
  },
  {
    label: "Trend line",
    swatch: (
      <svg width="28" height="10" viewBox="0 0 28 10">
        <line x1="0" y1="5" x2="28" y2="5" stroke="var(--chart-fit)" strokeWidth="2.5" />
      </svg>
    ),
  },
  {
    label: "95% confidence band of the trend",
    swatch: (
      <svg width="28" height="10" viewBox="0 0 28 10">
        <rect width="28" height="10" fill="var(--chart-band)" fillOpacity="0.3" />
      </svg>
    ),
  },
];

const CRACKED_ENTRY: LegendEntry = {
  label: "Year the trend became statistically clear",
  swatch: (
    <svg width="28" height="10" viewBox="0 0 28 10">
      <line
        x1="14"
        y1="0"
        x2="14"
        y2="10"
        stroke="var(--brand-neon-yellow)"
        strokeWidth="2"
        strokeDasharray="3 2"
      />
    </svg>
  ),
};

function buildRows(series: readonly SeriesPoint[], fit: readonly FitPoint[]): SeriesRow[] {
  const fitByYear = new Map(fit.map((point) => [point.year, point]));
  return series.map((point) => {
    const fitted = fitByYear.get(point.year);
    return {
      year: point.year,
      value: point.value,
      fit: fitted ? fitted.value : null,
      band: fitted ? [fitted.ci_low, fitted.ci_high] : null,
    };
  });
}

/** Yearly series with the fitted straight line and its 95% confidence band. */
export function SeriesChart({
  series,
  fit,
  unit,
  variableName,
  summary,
  height = CHART_HEIGHT,
  crackedYear = null,
}: SeriesChartProps) {
  const rows = buildRows(series, fit);
  const hasFit = fit.length > 0;

  return (
    <ChartFigure
      summary={summary}
      legend={[
        ...(hasFit ? LEGEND : LEGEND.slice(0, 1)),
        ...(crackedYear !== null ? [CRACKED_ENTRY] : []),
      ]}
      table={{
        caption: `${variableName} by year, in ${unit}`,
        columns: ["Year", `Value (${unit})`, `Trend line (${unit})`, "95% band"],
        rows: rows.map((row) => [
          String(row.year),
          row.value === null ? "missing" : formatNumber(row.value),
          row.fit === null ? "n/a" : formatNumber(row.fit),
          row.band === null
            ? "n/a"
            : `${formatNumber(row.band[0])} to ${formatNumber(row.band[1])}`,
        ]),
      }}
    >
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={rows}
          margin={{ ...CHART_MARGIN, top: AXIS_TITLE_ROOM }}
          accessibilityLayer={false}
        >
          <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
          <XAxis
            dataKey="year"
            type="number"
            domain={["dataMin", "dataMax"]}
            tick={AXIS_TICK}
            axisLine={AXIS_LINE}
            tickLine={false}
            tickCount={8}
            allowDecimals={false}
          />
          <YAxis
            tick={AXIS_TICK}
            axisLine={false}
            tickLine={false}
            width={52}
            domain={["auto", "auto"]}
            tickFormatter={(value: number) => formatNumber(value)}
            label={{
              value: unit,
              position: "insideTopLeft",
              fill: "var(--chart-axis)",
              fontSize: 12,
              // Above the top tick, not on it: the unit and the first number used to overlap.
              dy: AXIS_TITLE_OFFSET,
              dx: 4,
            }}
          />
          <Tooltip
            cursor={{ stroke: "var(--line-strong)" }}
            content={({ active, payload }) => {
              const row = payload?.[0]?.payload as SeriesRow | undefined;
              if (!active || !row) return null;
              return (
                <TooltipBox
                  title={String(row.year)}
                  lines={[
                    {
                      label: "Value",
                      value: row.value === null ? "missing" : `${formatNumber(row.value)} ${unit}`,
                    },
                    ...(row.fit === null
                      ? []
                      : [{ label: "Trend line", value: `${formatNumber(row.fit)} ${unit}` }]),
                  ]}
                />
              );
            }}
          />
          {crackedYear !== null ? (
            <ReferenceLine
              x={crackedYear}
              stroke="var(--brand-neon-yellow)"
              strokeDasharray="4 4"
              label={{
                value: `Clear from ${crackedYear}`,
                position: "top",
                fill: "var(--brand-neon-yellow)",
                fontSize: 12,
                fontWeight: 700,
              }}
            />
          ) : null}
          <Area
            dataKey="band"
            stroke="none"
            fill="var(--chart-band)"
            fillOpacity={0.3}
            isAnimationActive={false}
            activeDot={false}
            connectNulls
          />
          <Line
            dataKey="value"
            stroke="var(--chart-series)"
            strokeWidth={1.5}
            dot={{ r: 3, fill: "var(--chart-series)", strokeWidth: 0 }}
            activeDot={{
              r: 5,
              fill: "var(--chart-series)",
              stroke: "var(--background)",
              strokeWidth: 2,
            }}
            isAnimationActive={false}
          />
          <Line
            dataKey="fit"
            stroke="var(--chart-fit)"
            strokeWidth={2.5}
            dot={false}
            activeDot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartFigure>
  );
}
