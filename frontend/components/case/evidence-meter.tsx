import type { Evidence } from "@/lib/api";
import { cn } from "@/lib/utils";

interface EvidenceText {
  label: string;
  detail: (alpha: number) => string;
  /** Filled segments out of three. */
  level: number;
}

/** Wording of the evidence levels, from the rules in docs/API_CONTRACT.md. */
export const EVIDENCE_TEXT: Record<Evidence, EvidenceText> = {
  strong: {
    label: "Strong evidence",
    detail: (alpha) => `Both tests find p below ${alpha}`,
    level: 3,
  },
  mixed: {
    label: "Mixed evidence",
    detail: (alpha) => `Only one of the two tests finds p below ${alpha}`,
    level: 2,
  },
  none: {
    label: "No clear evidence",
    detail: (alpha) => `Neither test finds p below ${alpha}`,
    level: 1,
  },
  insufficient: {
    label: "Not enough data",
    detail: () => "Fewer than 10 usable years, or a series that never changes",
    level: 0,
  },
};

const SEGMENTS = [1, 2, 3] as const;
const SEGMENT_STAGGER_MS = 90;

interface EvidenceMeterProps {
  evidence: Evidence;
  alpha: number;
  className?: string;
}

/** Three segments, filled by strength, always paired with the words. */
export function EvidenceMeter({ evidence, alpha, className }: EvidenceMeterProps) {
  const text = EVIDENCE_TEXT[evidence];
  return (
    <div className={cn("flex flex-wrap items-center gap-x-4 gap-y-2", className)}>
      <div aria-hidden="true" className="flex gap-1.5">
        {SEGMENTS.map((segment) => (
          <span key={segment} className="relative h-2 w-9 overflow-hidden rounded-full bg-white/20">
            {segment <= text.level ? (
              <span
                className="absolute inset-0 origin-left rounded-full bg-neon"
                style={{
                  animation: "meter-fill 480ms var(--ease-out) both",
                  animationDelay: `${segment * SEGMENT_STAGGER_MS}ms`,
                }}
              />
            ) : null}
          </span>
        ))}
      </div>
      <p className="text-sm">
        <span className="font-bold">{text.label}</span>
        <span className="text-white/85">. {text.detail(alpha)}.</span>
      </p>
    </div>
  );
}
