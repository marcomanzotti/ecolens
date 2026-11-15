"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowRight, FolderOpen, Search } from "lucide-react";
import type { DemoCase } from "@/lib/api";
import { caseHref, EMPTY_QUERY } from "@/lib/case-query";
import { formatPeriod, placeName } from "@/lib/format";
import { SeriesChart } from "@/components/charts/series-chart";
import { EVIDENCE_TEXT } from "@/components/case/evidence-meter";
import { buttonVariants } from "@/components/ui/button";
import type { TourBeat } from "@/components/tour/tour-script";

interface BeatCardProps {
  demo: DemoCase;
  beat: TourBeat;
  caseNumber: number;
  caseCount: number;
  onNextCase: (() => void) | null;
}

function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="font-heading text-xs font-bold tracking-[0.16em] text-neon uppercase">{children}</p>;
}

function Row({ term, children }: { term: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 border-t border-line py-3 sm:grid-cols-[7rem_1fr] sm:gap-4">
      <dt className="text-sm font-bold text-muted-foreground">{term}</dt>
      <dd className="tabular text-sm leading-snug">{children}</dd>
    </div>
  );
}

/** What the tour says at each beat. Every number comes from the saved case, never from here. */
export function BeatCard({ demo, beat, caseNumber, caseCount, onNextCase }: BeatCardProps) {
  const result = demo.case;
  const place = placeName(result.location);
  const period = formatPeriod(result.period);
  const twin = demo.trendmap?.opposite_twin ?? null;

  switch (beat) {
    case "arrive":
      return (
        <>
          <Eyebrow>Solved case {caseNumber} of {caseCount}</Eyebrow>
          <h2 className="mt-2 font-heading text-3xl leading-[1.05] font-black tracking-tight sm:text-4xl">{demo.title}</h2>
          <p className="mt-3 text-lg leading-snug">{demo.blurb}</p>
          <p className="mt-4 text-sm text-muted-foreground">
            {place}, {result.variable.name.toLowerCase()}, {period}
          </p>
        </>
      );
    case "planet":
      return (
        <>
          <Eyebrow>First, the whole planet</Eyebrow>
          <h2 className="mt-2 font-heading text-2xl leading-tight font-black sm:text-3xl">Every year since {result.period.start_year}</h2>
          <p className="mt-3 leading-snug">
            The colours are the surface temperature anomaly of each year; the bright border closes
            around the areas where the trend is already statistically significant. The key on the
            globe gives every colour its value.
          </p>
        </>
      );
    case "evidence":
      return (
        <>
          <Eyebrow>The evidence</Eyebrow>
          <h2 className="mt-2 font-heading text-2xl leading-tight font-black">
            {result.variable.name} at {place}
          </h2>
          <div className="mt-3 -mx-1">
            <SeriesChart
              series={result.series}
              fit={result.fit}
              unit={result.variable.unit}
              variableName={result.variable.name}
              summary={result.verdict.how_much}
              height={190}
              crackedYear={result.emergence?.emerged_year ?? null}
            />
          </div>
        </>
      );
    case "verdict":
      return (
        <>
          <Eyebrow>{EVIDENCE_TEXT[result.verdict.evidence].label}</Eyebrow>
          <h2 className="mt-2 font-heading text-3xl leading-[1.05] font-black tracking-tight">{result.verdict.headline}</h2>
          <dl className="mt-4">
            <Row term="How much">{result.verdict.how_much}</Row>
            <Row term="How sure">{result.verdict.how_sure}</Row>
            {result.emergence ? <Row term="When it cracked">{result.emergence.explanation}</Row> : null}
          </dl>
        </>
      );
    case "twin":
      return (
        <>
          <Eyebrow>The opposite twin</Eyebrow>
          <h2 className="mt-2 font-heading text-2xl leading-tight font-black sm:text-3xl">
            {twin ? "A short way off, the trend flips" : "No opposite twin nearby"}
          </h2>
          <p className="tabular mt-3 leading-snug">{twin ? twin.text : (demo.trendmap?.summary.text ?? "")}</p>
          {demo.trendmap ? <p className="tabular mt-3 text-sm text-muted-foreground">{demo.trendmap.summary.text}</p> : null}
        </>
      );
    case "end":
      return (
        <>
          <Eyebrow>Case closed</Eyebrow>
          <h2 className="mt-2 font-heading text-3xl leading-[1.05] font-black tracking-tight">Now pick your own place.</h2>
          <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <Link href={caseHref({ ...EMPTY_QUERY, demoId: demo.id })} className={buttonVariants({ size: "lg" })}>
              <FolderOpen aria-hidden="true" />
              Open the full case file
            </Link>
            {onNextCase ? (
              <button type="button" onClick={onNextCase} className={buttonVariants({ variant: "outline", size: "lg" })}>
                Next solved case
                <ArrowRight aria-hidden="true" />
              </button>
            ) : null}
            <Link href="/#place-search" className={buttonVariants({ variant: "accent", size: "lg" })}>
              <Search aria-hidden="true" />
              Search any place
            </Link>
          </div>
        </>
      );
  }
}
