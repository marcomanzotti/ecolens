import type { Location, OppositeTwin, Place, TrendMapCell, TrendMapResult } from "@/lib/api";

/** Props of the 3D globe. Fixed in stage 1: FE-1 uses them, FE-2 implements them. */
export interface GlobeProps {
  /** Suggested places, drawn as markers. */
  places: readonly Place[];
  /** The place under investigation, if any. The globe turns to face it. */
  selected: Location | null;
  /** Called when the user picks a marker or any point on the globe. */
  onSelect: (location: Location) => void;
  /** Block B: slopes to paint on the globe. */
  trendMap?: TrendMapResult | null;
  /** Called when the user picks a cell of the trend map. */
  onCellSelect?: (cell: TrendMapCell) => void;
  /** The two opposite cells to highlight, if any. */
  highlightTwin?: OppositeTwin | null;
  /**
   * The GISTEMP temperature time-lapse over the whole planet (anomaly field, emergence front).
   * `true` plays it from the first year; `{ autoplay: false }` shows the last year, paused.
   */
  timelapse?: boolean | TimelapseOptions;
  className?: string;
}

export interface TimelapseOptions {
  autoplay?: boolean;
}
