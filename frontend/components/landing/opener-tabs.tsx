"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export type OpenerMode = "guided" | "ask";

const TABS: readonly { mode: OpenerMode; label: string }[] = [
  { mode: "guided", label: "Guided questions" },
  { mode: "ask", label: "Ask in your own words" },
];

interface OpenerTabsProps {
  mode: OpenerMode;
  onModeChange: (mode: OpenerMode) => void;
  children: ReactNode;
}

/** Two tabs following the ARIA tabs pattern (arrow keys move between tabs). */
export function OpenerTabs({ mode, onModeChange, children }: OpenerTabsProps) {
  const baseId = useId();
  const refs = useRef<Record<OpenerMode, HTMLButtonElement | null>>({ guided: null, ask: null });

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const next: OpenerMode = mode === "guided" ? "ask" : "guided";
    onModeChange(next);
    refs.current[next]?.focus();
  };

  return (
    <div>
      <div
        role="tablist"
        aria-label="How to open a case"
        onKeyDown={handleKeyDown}
        className="mb-7 inline-flex rounded-lg border border-line-strong p-1"
      >
        {TABS.map((tab) => {
          const selected = tab.mode === mode;
          return (
            <button
              key={tab.mode}
              ref={(node) => {
                refs.current[tab.mode] = node;
              }}
              type="button"
              role="tab"
              id={`${baseId}-${tab.mode}-tab`}
              aria-selected={selected}
              aria-controls={`${baseId}-panel`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onModeChange(tab.mode)}
              className={cn(
                "min-h-10 cursor-pointer rounded-md px-3 text-sm font-bold transition-[background-color,color] duration-150",
                selected ? "bg-white text-deep" : "text-white hover:bg-electric",
              )}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" id={`${baseId}-panel`} aria-labelledby={`${baseId}-${mode}-tab`}>
        {children}
      </div>
    </div>
  );
}
