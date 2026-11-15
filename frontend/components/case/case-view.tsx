"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useSeenOnce } from "@/hooks/use-in-view";
import { useCaseData } from "@/hooks/use-case-data";
import type { Location } from "@/lib/api";
import { caseHref, parseCaseQuery, type CaseQuery } from "@/lib/case-query";
import { useReferenceData } from "@/components/providers/reference-data";
import { Button } from "@/components/ui/button";
import { CaseHeader } from "@/components/case/case-header";
import { DemoNotes } from "@/components/case/demo-notes";
import { EmergenceSection } from "@/components/case/emergence-section";
import { LimitationsSection } from "@/components/case/limitations-section";
import { LineupSection } from "@/components/case/lineup-section";
import { MapSection } from "@/components/case/map-section";
import { SectionNav } from "@/components/case/section-nav";
import { VerdictSection } from "@/components/case/verdict-section";
import { WitnessesSection } from "@/components/case/witnesses-section";
import { ServiceBanner, useServiceUnreachable } from "@/components/site/service-banner";

function NoPlace() {
  return (
    <div className="mx-auto max-w-xl px-5 py-24 text-center">
      <h1 className="font-heading text-4xl font-black">This case has no place yet</h1>
      <p className="mt-3 text-muted-foreground">
        The link is missing a place, or its coordinates could not be read. Open a new case and pick
        a place on the globe.
      </p>
      <Button className="mt-6" render={<Link href="/" />} nativeButton={false}>
        Open a new case
      </Button>
    </div>
  );
}

/** The case file: every block of the investigation, each loading on its own. */
export function CaseView() {
  const router = useRouter();
  const query = parseCaseQuery(useSearchParams());
  const { findVariable, catalog } = useReferenceData();
  const [mapRef, mapSeen] = useSeenOnce<HTMLElement>();
  const data = useCaseData(query, findVariable, mapSeen);
  const caseState = data.demo ?? data.caseResult.state;
  const unreachable =
    useServiceUnreachable() ||
    (caseState.status === "error" && caseState.error.code === "network_error");

  if (query.demoId === null && query.location === null) return <NoPlace />;

  /** Every change leaves the demo and becomes a live case that can be shared. */
  const open = (next: Partial<CaseQuery>) =>
    router.push(
      caseHref({
        ...query,
        location: data.location,
        variableId: data.variableId,
        demoId: null,
        ...next,
      }),
    );
  const openVariable = (variableId: string) => open({ variableId });
  const openPlace = (location: Location) => open({ location });

  const variable = findVariable(data.variableId);
  const caseData = data.caseResult.state.status === "success" ? data.caseResult.state.data : null;

  return (
    <div className="mx-auto w-full max-w-[90rem] px-5 pb-20 sm:px-8">
      <CaseHeader
        query={query}
        location={data.location}
        variable={caseData?.variable ?? variable}
        catalog={catalog.status === "success" ? catalog.data : null}
        onChange={open}
      />
      {unreachable ? (
        <div className="mt-10">
          <ServiceBanner
            consequence="This case needs it to fetch the data and run the tests."
            onRetry={() => {
              data.caseResult.retry();
              data.lineup.retry();
            }}
          />
        </div>
      ) : (
        <>
          {data.demo ? <DemoNotes demo={data.demo} /> : null}
          <SectionNav />
          <div className="mt-10 space-y-24">
            <VerdictSection
              section={data.caseResult}
              variableFromLineup={data.variableFromLineup}
              waitingForLineup={data.variableId === null}
              lineupState={data.lineup.state}
            />
            <EmergenceSection section={data.caseResult} />
            <LineupSection
              section={data.lineup}
              currentVariableId={data.variableId}
              onInvestigate={openVariable}
            />
            <MapSection
              ref={mapRef}
              section={data.trendMap}
              location={data.location}
              variableName={variable?.name ?? caseData?.variable.name ?? null}
              onOpenPlace={openPlace}
            />
            <WitnessesSection
              section={data.witnesses}
              hasWitnesses={data.hasWitnesses}
              variable={caseData?.variable ?? variable}
              catalog={catalog.status === "success" ? catalog.data : null}
              onInvestigate={openVariable}
            />
            <LimitationsSection caseResult={caseData} />
          </div>
        </>
      )}
    </div>
  );
}
