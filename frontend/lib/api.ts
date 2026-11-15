/**
 * Typed client for the EcoLens API (see docs/API_CONTRACT.md).
 *
 * Types come from lib/api-types.gen.ts, generated from the back-end models by
 * scripts/gen_types.sh. Do not hand-edit them.
 *
 * With NEXT_PUBLIC_USE_FIXTURES=1 every call answers from fixtures/*.json,
 * so the interface can be built without a running back-end.
 */
import type { components } from "./api-types.gen";

type Schemas = components["schemas"];

export type Location = Schemas["Location"];
export type Period = Schemas["Period"];
export type BBox = Schemas["BBox"];
export type Variable = Schemas["Variable"];
export type Theme = Schemas["Theme"];
export type Place = Schemas["Place"];
export type PeriodPreset = Schemas["PeriodPreset"];
export type SeriesPoint = Schemas["SeriesPoint"];
export type FitPoint = Schemas["FitPoint"];
export type TrendStats = Schemas["TrendStats"];
export type Verdict = Schemas["Verdict"];
export type Emergence = Schemas["Emergence"];
export type CaseResult = Schemas["CaseResult"];
export type LineupItem = Schemas["LineupItem"];
export type LineupResult = Schemas["LineupResult"];
export type Witness = Schemas["Witness"];
export type WitnessesResult = Schemas["WitnessesResult"];
export type TrendMapCell = Schemas["TrendMapCell"];
export type TrendMapResult = Schemas["TrendMapResult"];
export type OppositeTwin = Schemas["OppositeTwin"];
export type AskResult = Schemas["AskResult"];
export type Catalog = Schemas["Catalog"];
export type PlacesResult = Schemas["PlacesResult"];
export type DemoSummary = Schemas["DemoSummary"];
export type DemoList = Schemas["DemoList"];
export type DemoCase = Schemas["DemoCase"];
export type Health = Schemas["Health"];
export type ApiErrorBody = Schemas["ApiError"];
export type ErrorCode = ApiErrorBody["code"];

export type CaseRequest = Schemas["CaseRequest"];
export type LineupRequest = Schemas["LineupRequest"];
export type WitnessesRequest = Schemas["WitnessesRequest"];
export type TrendMapRequest = Schemas["TrendMapRequest"];
export type AskRequest = Schemas["AskRequest"];

export type Season = CaseResult["season"];
export type ThemeId = Theme["id"];
export type Direction = TrendStats["direction"];
export type Evidence = TrendStats["evidence"];

export interface Envelope<T> {
  success: boolean;
  data: T | null;
  error: ApiErrorBody | null;
}

/** `network_error` is raised by the client itself when the back-end cannot be reached. */
export type ClientErrorCode = ErrorCode | "network_error";

export class ApiError extends Error {
  readonly code: ClientErrorCode;
  readonly details: readonly string[];

  constructor(code: ClientErrorCode, message: string, details: readonly string[] = []) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
  }
}

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const USE_FIXTURES = process.env.NEXT_PUBLIC_USE_FIXTURES === "1";
const UNREACHABLE_MESSAGE =
  "The investigation service cannot be reached. Check your connection and try again.";
const MALFORMED_MESSAGE = "The investigation service sent an answer that could not be read.";
const HOST_TIMEOUT_MESSAGE = "The investigation took too long to answer. Please try again in a moment.";
const HOST_UNAVAILABLE_MESSAGE =
  "The investigation service is not available right now. Please try again in a moment.";
const HOST_RATE_LIMITED_MESSAGE = "Too many requests. Please wait a moment and try again.";
const HTTP_GATEWAY_TIMEOUT = 504;
const HTTP_TOO_MANY_REQUESTS = 429;
const HTTP_SERVER_ERROR = 500;

/**
 * An answer without our JSON envelope comes from the hosting platform (e.g. a function cut at its
 * time limit), not from the API: say what happened instead of "could not be read".
 */
function errorWithoutEnvelope(status: number): ApiError {
  if (status === HTTP_GATEWAY_TIMEOUT) return new ApiError("upstream_timeout", HOST_TIMEOUT_MESSAGE);
  if (status === HTTP_TOO_MANY_REQUESTS) return new ApiError("rate_limited", HOST_RATE_LIMITED_MESSAGE);
  if (status >= HTTP_SERVER_ERROR) return new ApiError("upstream_unavailable", HOST_UNAVAILABLE_MESSAGE);
  return new ApiError("internal_error", MALFORMED_MESSAGE);
}

const FIXTURES = {
  health: () => import("../fixtures/health.json"),
  catalog: () => import("../fixtures/catalog.json"),
  places: () => import("../fixtures/places.json"),
  case: () => import("../fixtures/case.json"),
  lineup: () => import("../fixtures/lineup.json"),
  witnesses: () => import("../fixtures/witnesses.json"),
  trendmap: () => import("../fixtures/trendmap.json"),
  ask: () => import("../fixtures/ask.json"),
  demo_list: () => import("../fixtures/demo_list.json"),
  demo: () => import("../fixtures/demo.json"),
} as const;

type FixtureName = keyof typeof FIXTURES;

function unwrap<T>(body: Envelope<T>): T {
  if (body.success && body.data !== null) {
    return body.data;
  }
  if (body.error) {
    throw new ApiError(body.error.code, body.error.message, body.error.details ?? []);
  }
  throw new ApiError("internal_error", MALFORMED_MESSAGE);
}

async function fromFixture<T>(name: FixtureName): Promise<T> {
  const fixtureModule = await FIXTURES[name]();
  // JSON imports widen literal unions to `string`, so the cast is needed here.
  return unwrap(fixtureModule.default as unknown as Envelope<T>);
}

async function request<T>(
  fixture: FixtureName,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  if (USE_FIXTURES) {
    return fromFixture<T>(fixture);
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") {
      throw cause;
    }
    throw new ApiError("network_error", UNREACHABLE_MESSAGE);
  }

  let envelope: Envelope<T>;
  try {
    envelope = (await response.json()) as Envelope<T>;
  } catch {
    throw errorWithoutEnvelope(response.status);
  }
  return unwrap(envelope);
}

export const api = {
  health: (signal?: AbortSignal) => request<Health>("health", "/health", undefined, signal),
  catalog: (signal?: AbortSignal) => request<Catalog>("catalog", "/catalog", undefined, signal),
  places: (signal?: AbortSignal) => request<PlacesResult>("places", "/places", undefined, signal),
  openCase: (body: CaseRequest, signal?: AbortSignal) =>
    request<CaseResult>("case", "/case", body, signal),
  lineup: (body: LineupRequest, signal?: AbortSignal) =>
    request<LineupResult>("lineup", "/lineup", body, signal),
  witnesses: (body: WitnessesRequest, signal?: AbortSignal) =>
    request<WitnessesResult>("witnesses", "/witnesses", body, signal),
  trendMap: (body: TrendMapRequest, signal?: AbortSignal) =>
    request<TrendMapResult>("trendmap", "/trendmap", body, signal),
  ask: (body: AskRequest, signal?: AbortSignal) => request<AskResult>("ask", "/ask", body, signal),
  demos: (signal?: AbortSignal) => request<DemoList>("demo_list", "/demo", undefined, signal),
  demo: (id: string, signal?: AbortSignal) =>
    request<DemoCase>("demo", `/demo/${encodeURIComponent(id)}`, undefined, signal),
} as const;
