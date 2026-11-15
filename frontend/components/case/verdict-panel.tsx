import { ArrowDown, MoveDownRight, MoveRight, MoveUpRight, TriangleAlert } from "lucide-react";
import type { AsyncState } from "@/hooks/use-api";
import type { CaseResult, Direction, WitnessesResult } from "@/lib/api";
import { directionWord, formatInterval, formatPeriod, formatSigned } from "@/lib/format";
import { EvidenceMeter } from "@/components/case/evidence-meter";
import { emergenceHeadline, type Headline } from "@/components/case/emergence-section";
import { AGREEMENT } from "@/components/case/witnesses-section";

const DIRECTION_ICON: Record<Direction, typeof MoveUpRight> = {
  up: MoveUpRight,
  down: MoveDownRight,
  flat: MoveRight,
};

export interface WitnessSignal {
  /** False when no second dataset measures this quantity. */
  available: boolean;
  state: AsyncState<WitnessesResult>;
}

interface VerdictPanelProps {
  result: CaseResult;
  alpha: number;
  /** Shown when the line-up, not the visitor, chose the variable. */
  pickedByLineup: boolean;
  witnesses: WitnessSignal;
}

/** The witnesses' answer in two lines, with the same labels as the Witnesses block. */
function witnessHeadline(signal: WitnessSignal, variableName: string): Headline {
  if (!signal.available) {
    return {
      big: "Single source",
      small: `No second dataset measures ${variableName.toLowerCase()} here yet`,
    };
  }
  const { state } = signal;
  if (state.status === "success") {
    const { agreement, quantity, witnesses, common_period: period } = state.data;
    return {
      big: AGREEMENT[agreement.level].label,
      small: `${quantity}: ${witnesses.length} datasets compared over ${formatPeriod(period)}`,
    };
  }
  if (state.status === "error") {
    return { big: "Not available", small: "The witnesses could not be called" };
  }
  return {
    big: "Being called…",
    small: "Fetching every dataset for the same quantity",
  };
}

/** One signal of the card: a short answer that jumps to the block explaining it. */
function SignalLink({ href, label, text }: { href: string; label: string; text: Headline }) {
  return (
    <a
      href={href}
      className="group flex min-h-11 min-w-0 flex-col gap-1 rounded-xl border border-white/25 p-4 transition-[background-color,border-color] duration-150 hover:border-white/60 hover:bg-white/[0.07]"
    >
      <span className="flex items-center justify-between gap-2 text-sm font-bold text-white/85">
        {label}
        <ArrowDown
          aria-hidden="true"
          className="size-4 shrink-0 transition-transform duration-150 group-hover:translate-y-0.5"
        />
      </span>
      <span className="tabular font-heading text-2xl leading-tight font-black text-balance">
        {text.big}
      </span>
      <span className="text-sm text-white/85">{text.small}</span>
    </a>
  );
}

/** The verdict as the API words it: headline, the number behind it, and the other signals. */
export function VerdictPanel({ result, alpha, pickedByLineup, witnesses }: VerdictPanelProps) {
  const { verdict, trend, variable } = result;
  const Icon = trend ? DIRECTION_ICON[trend.direction] : null;

  return (
    <article
      aria-label="Verdict"
      className="brand-gradient relative isolate overflow-hidden rounded-2xl border border-line p-5 shadow-[0_24px_60px_-30px_rgb(0_0_0/0.7)] sm:p-8 @4xl:p-10"
    >
      <div aria-hidden="true" className="coordinate-grid absolute inset-0 -z-10" />
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <p className="text-sm font-bold tracking-[0.12em] text-neon uppercase">Verdict</p>
        <EvidenceMeter evidence={verdict.evidence} alpha={alpha} />
      </div>

      <div className="mt-5 grid gap-6 @3xl:grid-cols-[minmax(0,1fr)_auto] @3xl:items-end @3xl:gap-10">
        <p className="reveal font-heading text-[clamp(2rem,1.4rem+2.6vw,3.5rem)] leading-[0.98] font-black tracking-[-0.025em] text-balance">
          {verdict.headline}
        </p>
        {trend && Icon ? (
          <div className="flex items-end gap-3 border-t border-white/25 pt-5 @3xl:flex-col @3xl:items-start @3xl:gap-1 @3xl:border-t-0 @3xl:border-l @3xl:pt-0 @3xl:pl-8">
            <Icon aria-hidden="true" className="size-10 shrink-0 text-neon" strokeWidth={2.5} />
            <p className="sr-only">{directionWord(trend.direction)}</p>
            <div>
              <p className="tabular font-heading text-[clamp(2.75rem,2.2rem+2vw,3.75rem)] leading-none font-black tracking-tight">
                {formatSigned(trend.sen.slope_per_decade)}
              </p>
              <p className="mt-1 font-bold">{variable.unit} per decade</p>
            </div>
          </div>
        ) : null}
      </div>
      {trend ? (
        <p className="mt-3 text-sm text-white/85 @3xl:text-right">
          Sen&apos;s slope. 95% interval {formatInterval(trend.sen.ci95_low, trend.sen.ci95_high)}.
        </p>
      ) : null}

      <div className="mt-7 grid gap-3 @xl:grid-cols-2">
        <SignalLink
          href="#cracked"
          label="When it cracked"
          text={emergenceHeadline(result.emergence)}
        />
        <SignalLink
          href="#witnesses"
          label="Witnesses"
          text={witnessHeadline(witnesses, variable.name)}
        />
      </div>

      <dl className="mt-7 grid gap-5 @2xl:grid-cols-2">
        <div>
          <dt className="text-sm font-bold text-white/85">How much</dt>
          <dd className="mt-1 text-pretty">{verdict.how_much}</dd>
        </div>
        <div>
          <dt className="text-sm font-bold text-white/85">How sure</dt>
          <dd className="mt-1 text-pretty">{verdict.how_sure}</dd>
        </div>
        <div className="@2xl:col-span-2">
          <dt className="sr-only">Where and when</dt>
          <dd className="text-sm text-white/85">{verdict.where}</dd>
        </div>
      </dl>
      {verdict.caveats.length > 0 ? (
        <ul className="mt-5 space-y-2 border-t border-white/25 pt-5">
          {verdict.caveats.map((caveat) => (
            <li key={caveat} className="flex max-w-[70ch] gap-2.5 text-sm">
              <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-neon" />
              <span>{caveat}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {pickedByLineup ? (
        <p className="mt-5 text-sm text-white/85">
          You did not name a variable, so the line-up put its strongest trend on the stand. Pick
          another one from the line-up below or the Variable menu above.
        </p>
      ) : null}
    </article>
  );
}
