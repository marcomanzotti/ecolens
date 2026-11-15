"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";
import { ApiError } from "@/lib/api";

export type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: ApiError };

export interface AsyncResult<T> {
  state: AsyncState<T>;
  retry: () => void;
}

interface Settled<T> {
  id: string;
  state: AsyncState<T>;
}

const UNEXPECTED_MESSAGE = "Something unexpected went wrong while loading this part of the case.";

export function toApiError(cause: unknown): ApiError {
  if (cause instanceof ApiError) return cause;
  return new ApiError("internal_error", UNEXPECTED_MESSAGE);
}

export function successState<T>(data: T | null): AsyncState<T> {
  return data === null ? { status: "idle" } : { status: "success", data };
}

/**
 * Runs `fetcher` whenever `key` changes and aborts the previous request.
 * `key === null` means "do not fetch" (idle). The state is derived from the key,
 * so a stale answer is never shown for a new question.
 */
export function useApi<T>(
  key: string | null,
  fetcher: (signal: AbortSignal) => Promise<T>,
): AsyncResult<T> {
  const [attempt, setAttempt] = useState(0);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const run = useEffectEvent(fetcher);
  const id = key === null ? null : `${key}#${attempt}`;

  useEffect(() => {
    if (id === null) return;
    const controller = new AbortController();
    run(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setSettled({ id, state: { status: "success", data } });
      },
      (cause: unknown) => {
        if (controller.signal.aborted) return;
        setSettled({ id, state: { status: "error", error: toApiError(cause) } });
      },
    );
    return () => controller.abort();
  }, [id]);

  const retry = useCallback(() => setAttempt((current) => current + 1), []);

  if (id === null) return { state: { status: "idle" }, retry };
  if (settled?.id === id) return { state: settled.state, retry };
  return { state: { status: "loading" }, retry };
}
