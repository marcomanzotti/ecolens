"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Emergence } from "@/lib/api";
import { formatP, formatSigned } from "@/lib/format";
import {
  AXIS_LINE,
  AXIS_TICK,
  AXIS_TITLE_OFFSET,
  AXIS_TITLE_ROOM,
  CHART_MARGIN,
  ChartFigure,
  TooltipBox,
} from "@/components/charts/chart-figure";

interface EmergenceChartProps {
  running: Emergence["running"];
  emergedYear: number | null;
  alpha: number;
  unit: string;
  startYear: number;
  summary: string;
}

interface RunningRow {
  endYear: number;
  p: number;
  shownP: number;
  slope: number;
}

const CHART_HEIGHT = 260;
/** Smallest p-value drawn: the axis is logarithmic, so zero cannot be shown. */
const P_FLOOR = 0.0001;
const P_TICKS = [1, 0.1, 0.01, 0.001, 0.0001];

function formatTick(value: number): string {
  return value >= 0.001 ? String(value) : value.toExponential(0);
}

/** Running p-value of the trend as years are added, against the alpha threshold. */
export function EmergenceChart({
  running,
  emergedYear,
  alpha,
  unit,
  startYear,
  summary,
}: EmergenceChartProps) {
  const rows: RunningRow[] = running.map((point) => ({
    endYear: point.end_year,
    p: point.p_value,
    shownP: Math.max(point.p_value, P_FLOOR),
    slope: point.slope_per_decade,
  }));
  const lowest = Math.min(...rows.map((row) => row.shownP), alpha);
  const floor = P_TICKS.filter((tick) => tick <= lowest)[0] ?? P_FLOOR;

  return (
    <ChartFigure
      summary={summary}
      legend={[
        {
          label: `p-value using the years from ${startYear} up to each year`,
          swatch: (
            <svg width="28" height="10" viewBox="0 0 28 10">
              <line x1="0" y1="5" x2="28" y2="5" stroke="var(--chart-series)" strokeWidth="2" />
            </svg>
          ),
        },
        {
          label: `Significance threshold (${alpha})`,
          swatch: (
            <svg width="28" height="10" viewBox="0 0 28 10">
              <line
                x1="0"
                y1="5"
                x2="28"
                y2="5"
                stroke="var(--chart-fit)"
                strokeWidth="2"
                strokeDasharray="5 4"
              />
            </svg>
          ),
        },
      ]}
      table={{
        caption: `Mann-Kendall p-value of the trend from ${startYear} to each end year`,
        columns: ["End year", "p-value", `Slope (${unit} per decade)`, "Below threshold"],
        rows: rows.map((row) => [
          String(row.endYear),
          formatP(row.p).replace("p ", "").replace("= ", ""),
          formatSigned(row.slope),
          row.p < alpha ? "yes" : "no",
        ]),
      }}
    >
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <LineChart
          data={rows}
          margin={{ ...CHART_MARGIN, top: AXIS_TITLE_ROOM }}
          accessibilityLayer={false}
        >
          <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
          <XAxis
            dataKey="endYear"
            type="number"
            domain={["dataMin", "dataMax"]}
            tick={AXIS_TICK}
            axisLine={AXIS_LINE}
            tickLine={false}
            allowDecimals={false}
          />
          <YAxis
            scale="log"
            domain={[floor, 1]}
            ticks={P_TICKS.filter((tick) => tick >= floor)}
            allowDataOverflow
            tick={AXIS_TICK}
            axisLine={false}
            tickLine={false}
            width={52}
            tickFormatter={formatTick}
            label={{
              value: "p-value (log scale)",
              position: "insideTopLeft",
              fill: "var(--chart-axis)",
              fontSize: 12,
              // Above the top tick, not on it: the unit and the first number used to overlap.
              dy: AXIS_TITLE_OFFSET,
              dx: 4,
            }}
          />
          <ReferenceArea
            y1={floor}
            y2={alpha}
            fill="var(--chart-band)"
            fillOpacity={0.14}
            stroke="none"
            label={{
              value: "significant below this line",
              position: "insideBottomLeft",
              fill: "var(--chart-axis)",
              fontSize: 12,
            }}
          />
          <ReferenceLine
            y={alpha}
            stroke="var(--chart-fit)"
            strokeWidth={2}
            strokeDasharray="5 4"
          />
          {emergedYear !== null ? (
            <ReferenceLine
              x={emergedYear}
              stroke="var(--chart-fit)"
              strokeWidth={2}
              label={{
                value: `Cracked in ${emergedYear}`,
                position: "top",
                fill: "var(--foreground)",
                fontSize: 13,
                fontWeight: 700,
              }}
            />
          ) : null}
          <Tooltip
            cursor={{ stroke: "var(--line-strong)" }}
            content={({ active, payload }) => {
              const row = payload?.[0]?.payload as RunningRow | undefined;
              if (!active || !row) return null;
              return (
                <TooltipBox
                  title={`${startYear}–${row.endYear}`}
                  lines={[
                    { label: "Mann-Kendall", value: formatP(row.p) },
                    { label: "Slope", value: `${formatSigned(row.slope)} ${unit}/decade` },
                    { label: "Significant", value: row.p < alpha ? "yes" : "not yet" },
                  ]}
                />
              );
            }}
          />
          <Line
            dataKey="shownP"
            stroke="var(--chart-series)"
            strokeWidth={2}
            dot={false}
            activeDot={{
              r: 5,
              fill: "var(--chart-series)",
              stroke: "var(--background)",
              strokeWidth: 2,
            }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFigure>
  );
}
