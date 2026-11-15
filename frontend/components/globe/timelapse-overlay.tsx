"use client";

import { Pause, Play } from "lucide-react";

import type { Location } from "@/lib/api";
import { cellDetail, shareFor } from "./timelapse-data";
import { DatasetSwitch } from "./dataset-switch";
import { ProjectionOverlay } from "./projection-overlay";
import { TIMELAPSE_DATASETS } from "./timelapse-datasets";
import { TimelapseCell } from "./timelapse-cell";
import { TimelapseLegend } from "./timelapse-legend";
import { timelapseSummary } from "./trend-summary";
import type { ProjectionControls } from "./use-projection-layer";
import type { TimelapseControls } from "./use-timelapse";
import { BOTTOM_BLOCK, CONTROLS_PANEL, OVERLAY_ROOT, TOP_BLOCK, TOP_SCRIM, TOP_TEXT, YEAR_TEXT } from "./overlay-layout";

const toggle =
  "inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-sm px-1.5 text-xs select-none has-focus-visible:outline-2 has-focus-visible:outline-neon";

function percent(value: number): string {
  return `${value.toFixed(value < 10 && value > 0 ? 1 : 0)}%`;
}

interface TimelapseOverlayProps {
  controls: TimelapseControls;
  selected: Location | null;
  /** False when the year is driven from outside (the guided tour). */
  showControls?: boolean;
  /** The static "2050" model projection, offered in the dataset switch when given. */
  projection?: ProjectionControls;
}

/** Year, counter, controls, legend and the selected cell, drawn over the globe. */
export function TimelapseOverlay({ controls, selected, showControls = true, projection }: TimelapseOverlayProps) {
  const { load, year, playing, layers } = controls;
  if (projection?.active && showControls) {
    return <ProjectionOverlay projection={projection} timelapse={controls} selected={selected} />;
  }
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
    <div className={OVERLAY_ROOT}>
      <div aria-hidden="true" className={TOP_SCRIM} />
      {/* Top right: on wide screens the page title overlaps the globe's top left corner. */}
      <div className={TOP_BLOCK}>
        <div className={TOP_TEXT}>
          <p aria-hidden="true" className={YEAR_TEXT}>
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

      <div className={BOTTOM_BLOCK}>
        <TimelapseLegend
          dataset={dataset}
          meta={meta}
          year={year}
          showAnomaly={layers.anomaly}
          showEmergence={layers.emergence}
        />
        <div hidden={!showControls} className={CONTROLS_PANEL}>
          <DatasetSwitch controls={controls} projection={projection} />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={controls.togglePlay}
              aria-label={playing ? "Pause the time-lapse" : "Play the time-lapse"}
              className="grid size-11 shrink-0 cursor-pointer place-items-center rounded-full bg-white text-deep transition-transform duration-150 ease-out active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon"
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
                className="h-11 min-w-0 flex-1 cursor-pointer accent-neon"
              />
            </label>
          </div>
          <fieldset className="hidden flex-wrap items-center gap-x-1 sm:flex">
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
      {detail && showControls ? (
        <details className="pointer-events-auto rounded-md border border-line bg-deep/90 px-2 text-xs backdrop-blur-sm sm:hidden">
          <summary className="flex min-h-11 cursor-pointer items-center font-bold">Selected place: its grid cell</summary>
          <div className="pb-2">
            <TimelapseCell detail={detail} dataset={dataset} meta={meta} />
          </div>
        </details>
      ) : null}
      <p className="sr-only">{timelapseSummary(meta, dataset)}</p>
    </div>
  );
}
