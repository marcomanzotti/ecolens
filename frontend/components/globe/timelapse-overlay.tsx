"use client";

import { Pause, Play } from "lucide-react";

import type { Location } from "@/lib/api";
import { cellDetail, shareFor } from "./timelapse-data";
import { DATASET_ORDER, TIMELAPSE_DATASETS } from "./timelapse-datasets";
import { TimelapseCell } from "./timelapse-cell";
import { TimelapseLegend } from "./timelapse-legend";
import { timelapseSummary } from "./trend-summary";
import type { TimelapseControls } from "./use-timelapse";

const toggle =
  "inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-sm px-1.5 text-xs select-none has-focus-visible:outline-2 has-focus-visible:outline-neon";
const segment =
  "inline-flex min-h-9 flex-1 cursor-pointer items-center justify-center rounded-sm px-2 text-xs font-bold select-none transition-colors duration-150 ease-out has-checked:bg-white has-checked:text-deep has-focus-visible:outline-2 has-focus-visible:outline-offset-1 has-focus-visible:outline-neon";

function percent(value: number): string {
  return `${value.toFixed(value < 10 && value > 0 ? 1 : 0)}%`;
}

interface TimelapseOverlayProps {
  controls: TimelapseControls;
  selected: Location | null;
}

/** Year, counter, controls, legend and the selected cell, drawn over the globe. */
export function TimelapseOverlay({ controls, selected }: TimelapseOverlayProps) {
  const { load, year, playing, layers } = controls;
  if (load.status === "error") {
    const label = TIMELAPSE_DATASETS[controls.datasetId].label.toLowerCase();
    return (
      <div className="absolute top-2 left-2 z-30 flex flex-col gap-1 rounded-md bg-deep/85 p-2 text-xs">
        <p role="status">The {label} time-lapse could not be loaded.</p>
        {controls.datasetId !== "temperature" ? (
          <button type="button" className="underline" onClick={() => controls.setDataset("temperature")}>
            Back to temperature
          </button>
        ) : null}
      </div>
    );
  }
  if (load.status === "loading" || year === null) return null;

  const { meta, dataset } = load.data;
  const { labels } = dataset;
  const first = meta.years[0];
  const last = meta.years[meta.years.length - 1];
  const share = shareFor(meta, year);
  const detail = selected ? cellDetail(load.data, selected.lat, selected.lon, year) : null;
  const tested = share.tested_cells > 0;

  return (
    <div className="pointer-events-none absolute inset-0 z-30 flex flex-col justify-between gap-2 p-2 sm:p-3">
      {/* Top right: on wide screens the page title overlaps the globe's top left corner. */}
      <div className="flex flex-col items-end gap-2">
        <div className="max-w-[75%] text-right [text-shadow:0_1px_6px_rgb(7_23_63/0.9)] sm:max-w-sm">
          <p aria-hidden="true" className="font-heading text-4xl leading-none font-bold tabular-nums sm:text-6xl">
            {year}
          </p>
          <p className="mt-1 text-xs sm:text-sm" aria-live={playing ? "off" : "polite"}>
            {tested ? (
              <>
                Significant {labels.up} over <strong className="tabular-nums">{percent(share.up_pct)}</strong> of the{" "}
                {dataset.denominator}, {labels.down} over <span className="tabular-nums">{percent(share.down_pct)}</span>{" "}
                (trend {first}–{year})
              </>
            ) : (
              <>No trend test yet: it needs at least {meta.test.min_years} years of data.</>
            )}
          </p>
        </div>
        {detail ? (
          <div className="pointer-events-auto hidden sm:block">
            <TimelapseCell detail={detail} dataset={dataset} meta={meta} />
          </div>
        ) : null}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <TimelapseLegend
          dataset={dataset}
          meta={meta}
          year={year}
          showAnomaly={layers.anomaly}
          showEmergence={layers.emergence}
        />
        <div className="pointer-events-auto flex flex-col gap-1 rounded-md border border-line bg-deep/85 p-1.5 backdrop-blur-sm sm:w-80">
          <fieldset className="flex gap-1 rounded-sm bg-white/10 p-0.5">
            <legend className="sr-only">Dataset</legend>
            {DATASET_ORDER.map((id) => (
              <label key={id} className={segment}>
                <input
                  type="radio"
                  name="timelapse-dataset"
                  value={id}
                  className="sr-only"
                  checked={controls.datasetId === id}
                  onChange={() => controls.setDataset(id)}
                />
                {TIMELAPSE_DATASETS[id].label}
              </label>
            ))}
          </fieldset>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={controls.togglePlay}
              aria-label={playing ? "Pause the time-lapse" : "Play the time-lapse"}
              className="grid size-9 shrink-0 place-items-center rounded-full bg-white text-deep transition-transform duration-150 ease-out active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon"
            >
              {playing ? <Pause className="size-4" aria-hidden="true" /> : <Play className="size-4" aria-hidden="true" />}
            </button>
            <label className="flex flex-1 items-center gap-2 text-xs">
              <span className="sr-only">Year</span>
              <input
                type="range"
                min={first}
                max={last}
                step={1}
                value={year}
                onChange={(event) => controls.setYear(Number(event.target.value))}
                aria-valuetext={`${year}`}
                className="h-9 flex-1 cursor-pointer accent-neon"
              />
            </label>
          </div>
          <fieldset className="flex flex-wrap items-center gap-x-1">
            <legend className="sr-only">Layers</legend>
            <label className={toggle}>
              <input
                type="checkbox"
                className="accent-neon"
                checked={layers.anomaly}
                onChange={(event) => controls.setLayers({ ...layers, anomaly: event.target.checked })}
              />
              Anomaly
            </label>
            <label className={toggle}>
              <input
                type="checkbox"
                className="accent-neon"
                checked={layers.emergence}
                onChange={(event) => controls.setLayers({ ...layers, emergence: event.target.checked })}
              />
              Significant trend
            </label>
          </fieldset>
        </div>
      </div>
      {detail ? (
        <div className="pointer-events-auto sm:hidden">
          <TimelapseCell detail={detail} dataset={dataset} meta={meta} />
        </div>
      ) : null}
      <p className="sr-only">{timelapseSummary(meta, dataset)}</p>
    </div>
  );
}
