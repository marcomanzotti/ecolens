import { Info } from "lucide-react";
import type { CaseResult } from "@/lib/api";
import { METHOD_CAVEATS } from "@/lib/caveats";
import { Section } from "@/components/ui/section";

function Caveats({ title, items }: { title: string; items: readonly string[] }) {
  return (
    <div>
      <h3 className="font-heading text-lg font-bold">{title}</h3>
      <ul className="mt-3 space-y-3">
        {items.map((item) => (
          <li key={item} className="flex max-w-[70ch] gap-3">
            <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-yonder" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** What this case can and cannot tell you: the API's list plus the known caveats of the method. */
export function LimitationsSection({ caseResult }: { caseResult: CaseResult | null }) {
  return (
    <Section
      id="limitations"
      title="Limitations"
      lede="What this case cannot tell you. Read these before quoting the verdict."
    >
      <div className="grid gap-10 border-t border-line pt-8 lg:grid-cols-2">
        {caseResult && caseResult.limitations.length > 0 ? (
          <Caveats title="About this case" items={caseResult.limitations} />
        ) : null}
        <Caveats title="About the method" items={METHOD_CAVEATS} />
      </div>
    </Section>
  );
}
