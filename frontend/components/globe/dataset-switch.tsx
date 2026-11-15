"use client";

import { cn } from "cn";

import { DATASET_ORDER, TIMELAPSE_DATASETS } from "./timelapse-datasets";
import type { ProjectionControls } from "./use-projection-layer";
import type { TimelapseControls } from "./use-timelapse";

export const SEGMENT_CLASS =
  "inline-flex min-h-11 min-w-0 flex-1 cursor-pointer items-center justify-center rounded-sm px-1.5 text-xs font-bold select-none transition-colors duration-150 ease-out has-checked:bg-white has-checked:text-deep has-focus-visible:outline-2 has-focus-visible:outline-offset-1 has-focus-visible:outline-neon";

interface Option {
  value: string;
  label: string;
  /** Shorter visible label on phones; the long one is used from the `sm` breakpoint. */
  short?: string;
}

interface SegmentedProps {
  legend: string;
  name: string;
  options: readonly Option[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

/** A row of radio buttons drawn as a segmented control. */
export function Segmented({ legend, name, options, value, onChange, className }: SegmentedProps) {
  return (
    <fieldset className={cn("flex min-w-0 gap-1 rounded-sm bg-white/10 p-0.5", className)}>
      <legend className="sr-only">{legend}</legend>
      {options.map((option) => (
        <label key={option.value} className={SEGMENT_CLASS}>
          <input
            type="radio"
            name={name}
            value={option.value}
            className="sr-only"
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          {option.short ? (
            <>
              <span className="sm:hidden">{option.short}</span>
              <span className="hidden sm:inline">{option.label}</span>
            </>
          ) : (
            option.label
          )}
        </label>
      ))}
    </fieldset>
  );
}

const PROJECTION_VALUE = "projection-2050";

/** Measured time-lapses (temperature, vegetation) and the static "2050" model projection. */
export function DatasetSwitch({ controls, projection }: { controls: TimelapseControls; projection?: ProjectionControls }) {
  const options: Option[] = DATASET_ORDER.map((id) => ({ value: id, label: TIMELAPSE_DATASETS[id].label }));
  if (projection) options.push({ value: PROJECTION_VALUE, label: "2050" });
  const value = projection?.active ? PROJECTION_VALUE : controls.datasetId;
  const choose = (next: string) => {
    if (next === PROJECTION_VALUE) {
      projection?.setActive(true);
      return;
    }
    projection?.setActive(false);
    const id = DATASET_ORDER.find((d) => d === next);
    if (id) controls.setDataset(id);
  };
  return <Segmented legend="Dataset" name="timelapse-dataset" options={options} value={value} onChange={choose} />;
}
