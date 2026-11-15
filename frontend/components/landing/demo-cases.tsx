"use client";

import Link from "next/link";
import { ArrowRight, FolderOpen } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import { api, type DemoSummary } from "@/lib/api";
import { caseHref, EMPTY_QUERY } from "@/lib/case-query";
import { useReferenceData } from "@/components/providers/reference-data";
import { AsyncView, Skeleton } from "@/components/ui/async-view";
import { cn } from "@/lib/utils";

const fetchDemos = async (signal: AbortSignal) => (await api.demos(signal)).demos;

function DemoCard({ demo, variableName }: { demo: DemoSummary; variableName: string | null }) {
  return (
    <li>
      <Link
        href={caseHref({ ...EMPTY_QUERY, demoId: demo.id })}
        className="panel group relative flex h-full flex-col gap-4 rounded-xl p-6 transition-[border-color,transform] duration-200 ease-out hover:border-line-strong active:scale-[0.99]"
      >
        <FolderOpen aria-hidden="true" className="size-6 text-neon" />
        <div className="space-y-2">
          <h3 className="font-heading text-2xl leading-tight font-black">{demo.title}</h3>
          <p className="text-muted-foreground">{demo.blurb}</p>
        </div>
        <p className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-line pt-4 text-sm">
          <span>
            {demo.place_name}
            {variableName ? (
              <span className="text-muted-foreground">, {variableName.toLowerCase()}</span>
            ) : null}
          </span>
          <span className="inline-flex items-center gap-1 font-bold">
            Open the case file
            <ArrowRight
              aria-hidden="true"
              className="size-4 transition-transform duration-150 ease-out group-hover:translate-x-0.5"
            />
          </span>
        </p>
      </Link>
    </li>
  );
}

/** Ready-made cases that open instantly, with no live data call. */
export function DemoCases() {
  const { state, retry } = useApi("demos", fetchDemos);
  const { findVariable } = useReferenceData();

  return (
    <section
      aria-labelledby="demos-heading"
      className="mx-auto w-full max-w-[90rem] px-5 py-16 sm:px-8"
    >
      <div className="mb-8 max-w-[60ch]">
        <h2
          id="demos-heading"
          className="font-heading text-3xl font-black tracking-tight sm:text-4xl"
        >
          Solved cases to start from
        </h2>
        <p className="mt-2 text-muted-foreground">
          Each one is a full investigation with its evidence, line-up and map, saved so it opens at
          once.
        </p>
      </div>
      <AsyncView
        state={state}
        onRetry={retry}
        loadingMessage="Loading the solved cases…"
        skeleton={<Skeleton className="h-56 max-w-md rounded-xl" />}
      >
        {(demos) =>
          demos.length === 0 ? (
            <p className="text-muted-foreground">No solved cases are available right now.</p>
          ) : (
            <ul className={cn("grid gap-4 sm:grid-cols-2", demos.length % 3 === 0 && "xl:grid-cols-3")}>
              {demos.map((demo) => (
                <DemoCard
                  key={demo.id}
                  demo={demo}
                  variableName={findVariable(demo.variable_id)?.name ?? null}
                />
              ))}
            </ul>
          )
        }
      </AsyncView>
    </section>
  );
}
