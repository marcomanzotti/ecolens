"use client";

import { useEffect, useState } from "react";

import { TIMELAPSE_UNTESTED_YEAR_MS, TIMELAPSE_YEAR_MS } from "./constants";
import { loadTimelapse, type TimelapseData } from "./timelapse-data";
import { DEFAULT_DATASET, TIMELAPSE_DATASETS, type TimelapseDatasetId } from "./timelapse-datasets";
import type { TimelapseLayers } from "./timelapse-layer";

export type TimelapseLoad =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: TimelapseData };

export interface TimelapseControls {
  load: TimelapseLoad;
  /** Year on screen; null until the data has arrived. */
  year: number | null;
  playing: boolean;
  layers: TimelapseLayers;
  /** Dataset on screen (temperature by default). */
  datasetId: TimelapseDatasetId;
  setDataset: (id: TimelapseDatasetId) => void;
  setYear: (year: number) => void;
  togglePlay: () => void;
  setLayers: (layers: TimelapseLayers) => void;
}

const DEFAULT_LAYERS: TimelapseLayers = { anomaly: true, emergence: true };

type LoadedById = Partial<Record<TimelapseDatasetId, TimelapseLoad>>;

/** Loads a dataset the first time it is chosen and keeps it: switching back costs nothing. */
function useTimelapseData(enabled: boolean, id: TimelapseDatasetId): TimelapseLoad {
  const [loads, setLoads] = useState<LoadedById>({});
  const current = loads[id];
  useEffect(() => {
    if (!enabled || current) return;
    let cancelled = false;
    const settle = (load: TimelapseLoad) => !cancelled && setLoads((prev) => ({ ...prev, [id]: load }));
    loadTimelapse(TIMELAPSE_DATASETS[id]).then(
      (data) => settle({ status: "ready", data }),
      (error: unknown) =>
        settle({ status: "error", message: error instanceof Error ? error.message : "The time-lapse could not be loaded." }),
    );
    return () => {
      cancelled = true;
    };
  }, [enabled, id, current]);
  // While a newly chosen dataset loads, the previous one stays on screen (the controls stay put).
  const previous = Object.values(loads).find((load) => load?.status === "ready");
  return current ?? previous ?? { status: "loading" };
}

/**
 * Playback of the time-lapse: fixed speed (one year every TIMELAPSE_YEAR_MS), starting from the
 * first year. With reduced motion there is no autoplay: the last year is shown, with the slider.
 */
export function useTimelapse(enabled: boolean, autoplay: boolean, reducedMotion: boolean): TimelapseControls {
  const [datasetId, setDatasetId] = useState<TimelapseDatasetId>(DEFAULT_DATASET);
  const load = useTimelapseData(enabled, datasetId);
  const years = load.status === "ready" ? load.data.meta.years : null;
  const first = years ? years[0] : null;
  const last = years ? years[years.length - 1] : null;
  const firstTested = load.status === "ready" && first !== null ? first + load.data.meta.test.min_years - 1 : null;
  const [chosenYear, setChosenYear] = useState<number | null>(null);
  const [playRequest, setPlayRequest] = useState<boolean | null>(null);
  const [layers, setLayers] = useState<TimelapseLayers>(DEFAULT_LAYERS);

  const playing = (playRequest ?? (autoplay && !reducedMotion)) && first !== null;
  // The year range follows the dataset: a year chosen on another dataset is clamped to this one.
  const clamped = chosenYear === null || first === null || last === null ? chosenYear : Math.min(last, Math.max(first, chosenYear));
  const year = clamped ?? (playing ? first : last);

  useEffect(() => {
    if (!playing || year === null || last === null) return;
    if (year >= last) {
      const stop = window.setTimeout(() => setPlayRequest(false), 0);
      return () => window.clearTimeout(stop);
    }
    const untested = firstTested !== null && year + 1 < firstTested;
    const delay = untested ? TIMELAPSE_UNTESTED_YEAR_MS : TIMELAPSE_YEAR_MS;
    const timer = window.setTimeout(() => setChosenYear(year + 1), delay);
    return () => window.clearTimeout(timer);
  }, [playing, year, last, firstTested]);

  const togglePlay = () => {
    if (playing) {
      setPlayRequest(false);
      return;
    }
    if (year !== null && last !== null && year >= last && first !== null) setChosenYear(first);
    setPlayRequest(true);
  };

  const setYear = (next: number) => {
    setPlayRequest(false);
    setChosenYear(next);
  };

  const setDataset = (id: TimelapseDatasetId) => {
    if (id === datasetId) return;
    setDatasetId(id);
    if (!playing) setChosenYear(null); // paused: show the new dataset's last year
  };

  return { load, year, playing, layers, datasetId, setDataset, setYear, togglePlay, setLayers };
}
