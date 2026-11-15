import type { Variable } from "@/lib/api";

/**
 * Product labels POWER does not declare. Only these three were confirmed against the POWER
 * documentation (checked on 14/11/2026); every other label is shown as provisional.
 */
const CONFIRMED_PRODUCT_IDS: readonly string[] = ["PRECTOTCORR", "TQV", "PW"];

/** Station records and GISTEMP are fetched from their own provider, not through POWER. */
const OWN_PROVIDER_KINDS: readonly Variable["source"]["kind"][] = ["station", "station_grid"];

export function isProductConfirmed(variable: Variable): boolean {
  return (
    CONFIRMED_PRODUCT_IDS.includes(variable.id) || OWN_PROVIDER_KINDS.includes(variable.source.kind)
  );
}

/** Plain-language name of each kind of data source. */
export const SOURCE_KIND_LABEL: Record<Variable["source"]["kind"], string> = {
  reanalysis: "reanalysis (a weather model corrected with observations)",
  satellite: "satellite",
  derived: "derived product",
  station: "weather station",
  station_grid: "gridded stations & ships",
};

/** Significance level fixed by the API contract; used only until the API sends its own. */
export const CONTRACT_ALPHA = 0.05;

/** Above this absolute lag-1 autocorrelation the verdict carries a caveat (API contract). */
export const AUTOCORRELATION_WARNING = 0.3;

/** Caveats about the method itself, true for every case. */
export const METHOD_CAVEATS: readonly string[] = [
  "When consecutive years resemble each other, tests are over-confident. Above ±0.3 year-to-year memory the verdict uses the Mann-Kendall p-value corrected for it (Hamed and Rao, 1998); the t-test p-value is never corrected, and the line-up, map and emergence year use the uncorrected Mann-Kendall p-value.",
  "The number of years needed to detect a trend is a rough estimate adapted from Weatherhead et al. (1998) to yearly data, not a prediction.",
  "Data product names marked “label provisional” are not confirmed: POWER does not state the source product of every variable.",
];
