import { MoveDownRight, MoveRight, MoveUpRight, TriangleAlert } from "lucide-react";
import type { CaseResult, Direction } from "@/lib/api";
import { directionWord, formatInterval, formatSigned } from "@/lib/format";
import { EvidenceMeter } from "@/components/case/evidence-meter";

const DIRECTION_ICON: Record<Direction, typeof MoveUpRight> = {
  up: MoveUpRight,
  down: MoveDownRight,
  flat: MoveRight,
};

interface VerdictPanelProps {
  result: CaseResult;
  alpha: number;
  /** Shown when the line-up, not the visitor, chose the variable. */
  pickedByLineup: boolean;
}

/** The verdict as the API words it, with the headline number beside it. */
export function VerdictPanel({ result, alpha, pickedByLineup }: VerdictPanelProps) {
  const { verdict, trend, variable } = result;
  const Icon = trend ? DIRECTION_ICON[trend.direction] : null;

  return (
    <div className="brand-gradient relative isolate overflow-hidden rounded-2xl border border-line p-6 sm:p-10">
      <div aria-hidden="true" className="coordinate-grid absolute inset-0 -z-10" />
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-16">
        <div className="min-w-0">
          <EvidenceMeter evidence={verdict.evidence} alpha={alpha} />
          <p className="reveal mt-6 font-heading text-[clamp(2.1rem,1.3rem+3.4vw,4rem)] leading-[0.98] font-black tracking-[-0.025em]">
            {verdict.headline}
          </p>
          <dl className="mt-8 grid gap-5 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-bold text-white/85">How much</dt>
              <dd className="mt-1 text-lg">{verdict.how_much}</dd>
            </div>
            <div>
              <dt className="text-sm font-bold text-white/85">How sure</dt>
              <dd className="mt-1 text-lg">{verdict.how_sure}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="sr-only">Where and when</dt>
              <dd className="text-white/85">{verdict.where}</dd>
            </div>
          </dl>
          {verdict.caveats.length > 0 ? (
            <ul className="mt-6 space-y-2 border-t border-white/25 pt-5">
              {verdict.caveats.map((caveat) => (
                <li key={caveat} className="flex max-w-[70ch] gap-2.5">
                  <TriangleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-neon" />
                  <span>{caveat}</span>
                </li>
              ))}
            </ul>
          ) : null}
          {pickedByLineup ? (
            <p className="mt-6 text-sm text-white/85">
              You did not name a variable, so the line-up put its strongest trend on the stand. Pick
              another one from the line-up below or the Variable menu above.
            </p>
          ) : null}
        </div>

        {trend && Icon ? (
          <div className="flex flex-col justify-end gap-3 border-t border-white/25 pt-6 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-10">
            <Icon aria-hidden="true" className="size-12 text-neon" strokeWidth={2.5} />
            <p className="sr-only">{directionWord(trend.direction)}</p>
            <p className="tabular font-heading text-6xl leading-none font-black tracking-tight">
              {formatSigned(trend.sen.slope_per_decade)}
            </p>
            <p className="font-bold">{variable.unit} per decade</p>
            <p className="text-sm text-white/85">
              Sen&apos;s slope. 95% interval{" "}
              {formatInterval(trend.sen.ci95_low, trend.sen.ci95_high)}.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
