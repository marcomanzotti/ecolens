"use client";

import { useId, useState } from "react";
import { ChevronDown } from "lucide-react";
import type { AskResult, Catalog } from "@/lib/api";
import { AskPanel } from "@/components/landing/ask-panel";
import { cn } from "@/lib/utils";

interface AskToggleProps {
  catalog: Catalog;
  onUse: (result: AskResult) => void;
}

/** The free-text question, folded away under the search so the first screen keeps one action. */
export function AskToggle({ catalog, onUse }: AskToggleProps) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <div className="mt-4">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen(!open)}
        className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-md text-sm font-bold underline decoration-line-strong underline-offset-4 hover:decoration-white"
      >
        Or ask in your own words
        <ChevronDown aria-hidden="true" className={cn("size-4 transition-transform duration-200 ease-out", open && "rotate-180")} />
      </button>
      <div id={panelId} hidden={!open} className="panel mt-3 rounded-xl p-4 sm:p-5">
        {open ? (
          <AskPanel
            catalog={catalog}
            onUse={(result) => {
              onUse(result);
              setOpen(false);
            }}
          />
        ) : null}
      </div>
    </div>
  );
}
