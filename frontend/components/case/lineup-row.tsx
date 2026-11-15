import { ArrowRight, CircleCheck, CircleDashed, CircleOff } from "lucide-react";
import type { LineupItem } from "@/lib/api";
import { directionWord, formatP, formatSigned } from "@/lib/format";
import { DirectionIcon } from "@/components/case/direction-icon";
import { cn } from "@/lib/utils";
import { Sparkline } from "@/components/case/sparkline";

export const LINEUP_GRID =
  "grid grid-cols-[2rem_minmax(0,1fr)] items-center gap-x-4 gap-y-2 md:grid-cols-[2rem_minmax(0,1fr)_7.5rem_10rem_7rem_9.5rem]";

function Status({ item }: { item: LineupItem }) {
  if (item.status === "no_data") {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
        <CircleOff aria-hidden="true" className="size-4" />
        No usable data
      </span>
    );
  }
  return item.significant ? (
    <span className="inline-flex items-center gap-1.5 text-sm font-bold">
      <CircleCheck aria-hidden="true" className="size-4 text-neon" />
      Significant
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
      <CircleDashed aria-hidden="true" className="size-4" />
      Not significant
    </span>
  );
}

interface LineupRowProps {
  item: LineupItem;
  isCurrent: boolean;
  onInvestigate: (variableId: string) => void;
}

/** One suspect: rank, what it is, its trend, and whether it survives the correction. */
export function LineupRow({ item, isCurrent, onInvestigate }: LineupRowProps) {
  const { variable } = item;
  const usable = item.status === "ok";
  const slope =
    item.slope_per_decade === null
      ? "–"
      : `${formatSigned(item.slope_per_decade)} ${variable.unit}`;

  const content = (
    <>
      <span className="tabular self-start pt-0.5 font-heading text-lg font-black text-muted-foreground">
        {item.rank ?? "–"}
      </span>
      <span className="min-w-0 self-start">
        <span className="block font-bold">{variable.name}</span>
        <span className="mt-0.5 block max-w-[70ch] text-sm text-muted-foreground">
          {variable.definition}
        </span>
      </span>
      <span className="col-start-2 flex flex-wrap items-center gap-x-5 gap-y-2 md:contents">
        <span>
          <Sparkline values={item.sparkline} direction={item.direction} muted={!item.significant} />
        </span>
        <span className="tabular text-sm">
          <span className="inline-flex items-center gap-1 font-bold">
            <DirectionIcon direction={item.direction} />
            {directionWord(item.direction)}
          </span>
          <span className="block text-muted-foreground">
            {usable ? `${slope} per decade` : "–"}
          </span>
        </span>
        <span className="tabular text-sm">
          {usable ? formatP(item.p_adjusted) : "–"}
          <span className="block text-muted-foreground md:hidden">after correction</span>
        </span>
      </span>
      <span className="col-start-2 flex items-center gap-3 md:col-start-auto md:justify-between">
        <Status item={item} />
        {usable && !isCurrent ? (
          <ArrowRight
            aria-hidden="true"
            className="hidden size-4 opacity-0 transition-[opacity,transform] duration-150 group-hover:translate-x-0.5 group-hover:opacity-100 md:block"
          />
        ) : null}
      </span>
    </>
  );

  if (!usable) {
    return <li className={cn(LINEUP_GRID, "px-4 py-4 opacity-80")}>{content}</li>;
  }

  return (
    <li>
      <button
        type="button"
        onClick={() => onInvestigate(variable.id)}
        aria-current={isCurrent ? "true" : undefined}
        aria-label={`${variable.name}: ${directionWord(item.direction)}, ${item.significant ? "significant" : "not significant"} after correction, ${formatP(item.p_adjusted)}.${isCurrent ? " Under investigation." : " Investigate this variable."}`}
        className={cn(
          LINEUP_GRID,
          "group w-full cursor-pointer px-4 py-4 text-left transition-[background-color] duration-150",
          isCurrent ? "bg-electric" : "hover:bg-white/[0.06]",
        )}
      >
        {content}
      </button>
    </li>
  );
}
