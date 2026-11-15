"use client";

import { CONTRACT_ALPHA } from "@/lib/caveats";
import { useReferenceData } from "@/components/providers/reference-data";

interface Note {
  title: string;
  body: string;
}

function notes(alpha: number): readonly Note[] {
  return [
    {
      title: "Two tests, one verdict",
      body: `Each yearly series is tested twice: a straight-line fit with a t-test, and the rank-based Mann-Kendall test. The evidence is strong only when both find p below ${alpha}.`,
    },
    {
      title: "Corrected for a crowded line-up",
      body: "Testing thirty variables or hundreds of map cells at once produces chance hits. Their p-values are corrected together with the Benjamini-Hochberg method before anything is called significant.",
    },
    {
      title: "Honest about its limits",
      body: "A trend says that a change is unlikely to be chance, not what caused it. Every case ends with the caveats that apply to it, including when years are correlated with each other.",
    },
  ];
}

/** How the verdicts are reached, in three short notes. */
export function MethodNotes() {
  const { catalog } = useReferenceData();
  const alpha = catalog.status === "success" ? catalog.data.alpha : CONTRACT_ALPHA;

  return (
    <section aria-labelledby="method-heading" className="border-t border-line">
      <div className="mx-auto grid w-full max-w-[90rem] gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[minmax(0,22rem)_1fr]">
        <h2
          id="method-heading"
          className="font-heading text-3xl font-black tracking-tight sm:text-4xl"
        >
          How a verdict is reached
        </h2>
        <dl className="grid gap-8 md:grid-cols-3">
          {notes(alpha).map((note) => (
            <div key={note.title} className="border-t border-line-strong pt-4">
              <dt className="font-heading text-lg font-bold">{note.title}</dt>
              <dd className="mt-2 text-muted-foreground">{note.body}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
