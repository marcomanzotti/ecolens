"use client";

import { useApi, type AsyncState } from "@/hooks/use-api";
import {
  api,
  type CaseResult,
  type DemoCase,
  type LineupItem,
  type LineupResult,
  type Location,
  type TrendMapResult,
  type Variable,
  type WitnessesResult,
} from "@/lib/api";
import { boxAround, type CaseQuery } from "@/lib/case-query";

export interface Section<T> {
  state: AsyncState<T>;
  retry: () => void;
}

export interface CaseData {
  /** The place under investigation (from the URL, or from the demo once it loads). */
  location: Location | null;
  /** The variable investigated: from the URL, or the strongest trend of the line-up. */
  variableId: string | null;
  /** True when the line-up chose the variable because the visitor did not. */
  variableFromLineup: boolean;
  demo: AsyncState<DemoCase> | null;
  caseResult: Section<CaseResult>;
  lineup: Section<LineupResult>;
  /** idle with `hasWitnesses === false` means this variable has no witnesses to call. */
  witnesses: Section<WitnessesResult>;
  hasWitnesses: boolean;
  trendMap: Section<TrendMapResult>;
}

const IDLE = { status: "idle" } as const;

/** A fetcher only runs when its key is set, and the key is only set when the body exists. */
function need<T>(body: T | null): T {
  if (body === null) throw new Error("A request was started without its parameters.");
  return body;
}
const noop = () => undefined;

/** The strongest significant trend, else the strongest trend with data. */
export function strongestSuspect(items: readonly LineupItem[]): string | null {
  const ranked = items
    .filter((item) => item.status === "ok" && item.rank !== null)
    .toSorted((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
  return (ranked.find((item) => item.significant) ?? ranked[0])?.variable.id ?? null;
}

function fromDemo<T>(demo: AsyncState<DemoCase>, pick: (d: DemoCase) => T | null): AsyncState<T> {
  if (demo.status !== "success") return demo;
  const value = pick(demo.data);
  return value === null ? IDLE : { status: "success", data: value };
}

/**
 * Loads every block of a case. Each block has its own state, so one failing block never
 * breaks the others. A demo answers all blocks from one saved response.
 */
export function useCaseData(
  query: CaseQuery,
  findVariable: (id: string | null) => Variable | null,
  mapWanted: boolean,
): CaseData {
  const isDemo = query.demoId !== null;
  const { period, season, themes } = query;
  const location = query.location;

  const demo = useApi(isDemo ? `demo:${query.demoId}` : null, (signal) =>
    api.demo(query.demoId ?? "", signal),
  );

  const lineupBody = location
    ? { location, themes: themes.length > 0 ? [...themes] : null, period, season }
    : null;
  const lineup = useApi(
    !isDemo && lineupBody ? `lineup:${JSON.stringify(lineupBody)}` : null,
    (signal) => api.lineup(need(lineupBody), signal),
  );

  const autoVariable =
    lineup.state.status === "success" ? strongestSuspect(lineup.state.data.items) : null;
  const variableId = isDemo
    ? demo.state.status === "success"
      ? demo.state.data.case.variable.id
      : null
    : (query.variableId ?? autoVariable);

  const caseBody =
    location && variableId ? { location, variable_id: variableId, period, season } : null;
  const caseResult = useApi(
    !isDemo && caseBody ? `case:${JSON.stringify(caseBody)}` : null,
    (signal) => api.openCase(need(caseBody), signal),
  );

  const variable = findVariable(variableId);
  const hasWitnesses = isDemo
    ? demo.state.status === "success" && demo.state.data.witnesses !== null
    : Boolean(variable?.witness_group);
  const witnessKey =
    !isDemo && caseBody && hasWitnesses ? `witnesses:${JSON.stringify(caseBody)}` : null;
  const witnesses = useApi(witnessKey, (signal) => api.witnesses(need(caseBody), signal));

  const mapBody =
    location && variableId
      ? { variable_id: variableId, bbox: boxAround(location), period, season }
      : null;
  const mapKey = !isDemo && mapWanted && mapBody ? `map:${JSON.stringify(mapBody)}` : null;
  const trendMap = useApi(mapKey, (signal) => api.trendMap(need(mapBody), signal));

  if (isDemo) {
    const demoLocation = demo.state.status === "success" ? demo.state.data.case.location : null;
    return {
      location: demoLocation,
      variableId,
      variableFromLineup: false,
      demo: demo.state,
      caseResult: { state: fromDemo(demo.state, (d) => d.case), retry: demo.retry },
      lineup: { state: fromDemo(demo.state, (d) => d.lineup), retry: demo.retry },
      witnesses: { state: fromDemo(demo.state, (d) => d.witnesses), retry: demo.retry },
      hasWitnesses,
      trendMap: { state: fromDemo(demo.state, (d) => d.trendmap), retry: demo.retry },
    };
  }

  return {
    location,
    variableId,
    variableFromLineup: query.variableId === null && autoVariable !== null,
    demo: null,
    caseResult: { state: caseResult.state, retry: caseResult.retry },
    lineup: { state: lineup.state, retry: lineup.retry },
    witnesses: hasWitnesses
      ? { state: witnesses.state, retry: witnesses.retry }
      : { state: IDLE, retry: noop },
    hasWitnesses,
    trendMap: { state: trendMap.state, retry: trendMap.retry },
  };
}
