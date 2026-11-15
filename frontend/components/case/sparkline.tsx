import type { Direction } from "@/lib/api";

const WIDTH = 120;
const HEIGHT = 32;
const PAD = 3;

const STROKE: Record<Direction, string> = {
  up: "var(--trend-rising)",
  down: "var(--trend-falling)",
  flat: "var(--muted-foreground)",
};

interface SparklineProps {
  values: readonly (number | null)[];
  direction: Direction | null;
  /** Faded when the trend is not significant. */
  muted: boolean;
}

/** Path with gaps where years are missing. */
function buildPath(values: readonly (number | null)[]): string {
  const present = values.filter((v): v is number => v !== null);
  if (present.length < 2) return "";
  const min = Math.min(...present);
  const max = Math.max(...present);
  const span = max - min || 1;
  const step = (WIDTH - PAD * 2) / Math.max(values.length - 1, 1);
  let pen = false;
  return values
    .map((value, index) => {
      if (value === null) {
        pen = false;
        return "";
      }
      const x = PAD + index * step;
      const y = HEIGHT - PAD - ((value - min) / span) * (HEIGHT - PAD * 2);
      const command = pen ? "L" : "M";
      pen = true;
      return `${command}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join("");
}

/** A tiny picture of the yearly series. Decorative: the row says everything in words. */
export function Sparkline({ values, direction, muted }: SparklineProps) {
  const path = buildPath(values);
  if (!path) return <span aria-hidden="true" className="block h-8 w-[120px]" />;
  return (
    <svg
      aria-hidden="true"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width={WIDTH}
      height={HEIGHT}
      className="block overflow-visible"
    >
      <path
        d={path}
        fill="none"
        stroke={direction ? STROKE[direction] : STROKE.flat}
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity={muted ? 0.55 : 1}
      />
    </svg>
  );
}
