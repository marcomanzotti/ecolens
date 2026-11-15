/**
 * Layout shared by the time-lapse and "2050" overlays.
 *
 * Phones: the legend and controls sit in the flow under the canvas, so the globe shrinks to fit
 * above them instead of being covered; only the year floats over the top of the view.
 * From `sm`: everything floats over the globe's corners.
 */
export const OVERLAY_ROOT =
  "pointer-events-none z-30 flex shrink-0 flex-col gap-1.5 px-2 pb-2 sm:absolute sm:inset-0 sm:justify-between sm:gap-2 sm:p-3";

/** Darkens the top of the view so the year and its sentence keep their contrast over bright land. */
export const TOP_SCRIM =
  "pointer-events-none absolute inset-x-0 top-0 z-20 h-24 bg-linear-to-b from-space/75 to-transparent sm:h-36";

export const TOP_BLOCK = "absolute top-2 right-2 z-30 flex flex-col items-end gap-2 sm:static";

export const TOP_TEXT =
  "max-w-[min(75vw,20rem)] text-right [text-shadow:0_1px_6px_rgb(7_23_63/0.95),0_0_2px_rgb(7_23_63)] sm:max-w-sm";

export const YEAR_TEXT = "font-heading text-3xl leading-none font-bold tabular-nums sm:text-6xl";

export const BOTTOM_BLOCK = "flex flex-col gap-1.5 sm:flex-row sm:items-end sm:justify-between sm:gap-2";

export const CONTROLS_PANEL =
  "pointer-events-auto flex flex-col gap-1 rounded-md border border-line bg-deep/90 p-1 backdrop-blur-sm sm:w-80 sm:p-1.5";

/** Legend card: compact on phones, a fixed column from `sm`. */
export const LEGEND_CARD =
  "w-full rounded-md border border-line bg-deep/90 px-2 py-1.5 text-[11px] leading-snug text-white backdrop-blur-sm sm:w-72 sm:p-2 sm:text-xs";

/** Disclosure for the long part of a legend on phones; at least 44 px tall to tap. */
export const LEGEND_SUMMARY =
  "-mb-1.5 flex min-h-11 cursor-pointer items-center font-bold underline underline-offset-2";
