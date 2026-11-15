import { TriangleAlert } from "lucide-react";
import type { TrendStats as Stats } from "@/lib/api";
import { AUTOCORRELATION_WARNING } from "@/lib/caveats";
import { formatInterval, formatNumber, formatP, formatSigned } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Stat {
  term: string;
  value: string;
  note: string;
  /** Marks a value that needs attention (with an icon, never colour alone). */
  warn?: boolean;
}

function significance(p: number, alpha: number): string {
  return p < alpha ? `below ${alpha}: significant` : `not below ${alpha}`;
}

/** Positive memory inflates the tests; negative memory only makes them approximate. */
function memoryNote(trend: Stats, high: boolean): string {
  const lag1 = trend.lag1_autocorrelation;
  if (!high) return `Within ±${AUTOCORRELATION_WARNING}: small effect on the tests`;
  if (trend.autocorrelation_corrected) {
    return lag1 > 0
      ? `Above +${AUTOCORRELATION_WARNING}: alike years, so the Mann-Kendall p-value was corrected`
      : `Below −${AUTOCORRELATION_WARNING}: alternating years, so the Mann-Kendall p-value was corrected`;
  }
  return lag1 > 0
    ? `Above +${AUTOCORRELATION_WARNING}: alike years, the tests are over-confident`
    : `Below −${AUTOCORRELATION_WARNING}: alternating years, p-values approximate`;
}

/** The two Mann-Kendall p-values side by side, saying which one the verdict used. */
function mannKendallStats(trend: Stats): readonly Stat[] {
  const { p_value: plain, p_value_hamed_rao: corrected, tau } = trend.mann_kendall;
  const used = trend.autocorrelation_corrected;
  const usedNote = (isUsed: boolean) =>
    isUsed ? "Used for the verdict" : "Not used for the verdict";
  return [
    {
      term: "Mann-Kendall p",
      value: formatP(plain),
      note: `τ = ${formatNumber(tau, 2)}, ${significance(plain, trend.alpha)}. ${usedNote(!used)}`,
    },
    {
      term: "Mann-Kendall p, corrected for autocorrelation",
      value: formatP(corrected ?? null),
      note:
        corrected === undefined || corrected === null
          ? "Could not be computed for this series"
          : `${significance(corrected, trend.alpha)}. ${usedNote(used)}`,
    },
  ];
}

function buildStats(trend: Stats): readonly Stat[] {
  const unit = trend.unit;
  const memoryHigh = Math.abs(trend.lag1_autocorrelation) > AUTOCORRELATION_WARNING;
  return [
    {
      term: "Trend per decade (Sen's slope)",
      value: `${formatSigned(trend.sen.slope_per_decade)} ${unit}`,
      note: `95% interval ${formatInterval(trend.sen.ci95_low, trend.sen.ci95_high)}`,
    },
    {
      term: "Straight-line fit (least squares)",
      value: `${formatSigned(trend.ols.slope_per_decade)} ${unit}`,
      note: `95% interval ${formatInterval(trend.ols.ci95_low, trend.ols.ci95_high)}, R² ${formatNumber(trend.ols.r_squared, 2)}`,
    },
    {
      term: "t-test on the fit",
      value: formatP(trend.ols.p_value),
      note: `t = ${formatNumber(trend.ols.t_statistic)}, ${significance(trend.ols.p_value, trend.alpha)}`,
    },
    ...mannKendallStats(trend),
    {
      term: "Change over the whole period",
      value: `${formatSigned(trend.total_change)} ${unit}`,
      note:
        trend.percent_change === null
          ? "No percentage: it would not be meaningful for this unit or average"
          : `${formatSigned(trend.percent_change)}% of the average`,
    },
    {
      term: "Year-to-year memory",
      value: formatSigned(trend.lag1_autocorrelation, 3),
      note: memoryNote(trend, memoryHigh),
      warn: memoryHigh,
    },
    {
      term: "Average",
      value: `${formatNumber(trend.mean)} ${unit}`,
      note: `Typical spread ±${formatNumber(trend.std, 2)} ${unit}, ${trend.n} years tested${trend.n_missing > 0 ? `, ${trend.n_missing} missing` : ""}`,
    },
  ];
}

/** Every statistic behind the verdict, with its plain-language label. */
export function TrendStats({ trend }: { trend: Stats }) {
  return (
    <dl className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-line bg-line @md:grid-cols-2 @5xl:grid-cols-4">
      {buildStats(trend).map((stat) => (
        <div key={stat.term} className="bg-deep p-4 sm:p-5">
          <dt className="text-sm text-muted-foreground">{stat.term}</dt>
          <dd className="tabular mt-1.5 font-heading text-2xl leading-tight font-bold">
            {stat.value}
          </dd>
          <dd
            className={cn(
              "mt-1 flex gap-1.5 text-sm",
              stat.warn ? "font-bold" : "text-muted-foreground",
            )}
          >
            {stat.warn ? (
              <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-neon" />
            ) : null}
            {stat.note}
          </dd>
        </div>
      ))}
    </dl>
  );
}
