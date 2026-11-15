import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import type { Direction } from "@/lib/api";
import { cn } from "@/lib/utils";

const ICONS = { up: ArrowUpRight, down: ArrowDownRight, flat: ArrowRight } as const;

/** Rising in Rocket Red, falling in Blue Yonder: always next to the word, never alone. */
const COLORS: Record<Direction, string> = {
  up: "text-rising",
  down: "text-falling",
  flat: "text-muted-foreground",
};

export function DirectionIcon({
  direction,
  className,
}: {
  direction: Direction | null;
  className?: string;
}) {
  if (direction === null) return null;
  const Icon = ICONS[direction];
  return (
    <Icon
      aria-hidden="true"
      strokeWidth={2.5}
      className={cn("inline size-4 shrink-0", COLORS[direction], className)}
    />
  );
}
