import type { Variable } from "@/lib/api";

/**
 * Product labels POWER does not declare. Only these three were confirmed against the POWER
 * documentation (docs/STATUS.md, 14/11/2026); every other label is shown as provisional.
 */
const CONFIRMED_PRODUCT_IDS: readonly string[] = ["PRECTOTCORR", "TQV", "PW"];

export function isProductConfirmed(variable: Variable): boolean {
  return CONFIRMED_PRODUCT_IDS.includes(variable.id);
}

/** Significance level fixed by the API contract; used only until the API sends its own. */
export const CONTRACT_ALPHA = 0.05;

/** Above this absolute lag-1 autocorrelation the verdict carries a caveat (API contract). */
export const AUTOCORRELATION_WARNING = 0.3;

/** Caveats about the method itself, true for every case. */
export const METHOD_CAVEATS: readonly string[] = [
  "The p-values are not corrected for autocorrelation (no pre-whitening). When consecutive years resemble each other, the tests are over-confident; the year-to-year memory is shown with every case so you can judge it.",
  "The number of years needed to detect a trend is a rough estimate adapted from Weatherhead et al. (1998) to yearly data, not a prediction.",
  "Data product names marked “label provisional” are not confirmed: POWER does not state the source product of every variable.",
];
