import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface LegendEntry {
  label: string;
  /** A small inline SVG or shape that matches the mark in the chart. */
  swatch: ReactNode;
}

export interface DataTable {
  caption: string;
  columns: readonly string[];
  rows: readonly (readonly string[])[];
}

interface ChartFigureProps {
  /** One plain sentence saying what the chart shows: the text alternative. */
  summary: string;
  legend?: readonly LegendEntry[];
  table: DataTable;
  className?: string;
  children: ReactNode;
}

/** Wraps a chart with its legend, a text summary and the same data as a table. */
export function ChartFigure({ summary, legend, table, className, children }: ChartFigureProps) {
  return (
    <figure className={cn("min-w-0", className)}>
      {legend && legend.length > 0 ? (
        <ul className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted-foreground">
          {legend.map((entry) => (
            <li key={entry.label} className="flex items-center gap-2">
              <span aria-hidden="true" className="inline-flex w-7 items-center justify-center">
                {entry.swatch}
              </span>
              {entry.label}
            </li>
          ))}
        </ul>
      ) : null}
      <div role="img" aria-label={summary}>
        {children}
      </div>
      <figcaption className="mt-2 text-sm text-muted-foreground">{summary}</figcaption>
      <details className="mt-2 text-sm">
        <summary className="inline-block rounded-sm py-1 text-muted-foreground underline underline-offset-4 hover:text-foreground">
          Show the data as a table
        </summary>
        <div
          className="mt-2 max-h-72 overflow-auto rounded-md border border-line"
          tabIndex={0}
          role="region"
          aria-label={table.caption}
        >
          <table className="tabular w-full border-collapse text-left">
            <caption className="sr-only">{table.caption}</caption>
            <thead className="sticky top-0 bg-background">
              <tr>
                {table.columns.map((column) => (
                  <th key={column} scope="col" className="border-b border-line px-3 py-2 font-bold">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row) => (
                <tr key={row[0]} className="border-b border-line last:border-0">
                  {row.map((cell, index) => (
                    <td key={table.columns[index]} className="px-3 py-1.5">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

interface TooltipLine {
  label: string;
  value: string;
}

interface TooltipBoxProps {
  title: string;
  lines: readonly TooltipLine[];
}

/** The floating box shown while hovering a chart. Text wears text colours only. */
export function TooltipBox({ title, lines }: TooltipBoxProps) {
  return (
    <div className="tabular rounded-md border border-line-strong bg-background px-3 py-2 text-sm shadow-lg">
      <p className="font-bold">{title}</p>
      <dl className="mt-1 grid grid-cols-[auto_auto] gap-x-4 gap-y-0.5">
        {lines.map((line) => (
          <div key={line.label} className="contents">
            <dt className="text-muted-foreground">{line.label}</dt>
            <dd className="text-right">{line.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

/** Shared axis styling so every chart reads as one system. */
export const AXIS_TICK = { fill: "var(--chart-axis)", fontSize: 12 } as const;
export const AXIS_LINE = { stroke: "var(--line-strong)" } as const;
export const CHART_MARGIN = { top: 12, right: 16, bottom: 4, left: 0 } as const;
