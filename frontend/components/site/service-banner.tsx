"use client";

import { RefreshCw, TriangleAlert } from "lucide-react";
import { useReferenceData } from "@/components/providers/reference-data";
import { Button } from "@/components/ui/button";

/** True when the reference data says the back-end cannot be reached at all. */
export function useServiceUnreachable(): boolean {
  const { health, catalog } = useReferenceData();
  return [health, catalog].some(
    (state) => state.status === "error" && state.error.code === "network_error",
  );
}

interface ServiceBannerProps {
  /** What cannot be done while the service is down, in one sentence. */
  consequence: string;
  /** Extra retries to run besides the reference data (e.g. the case blocks). */
  onRetry?: () => void;
}

/** One clear message when the investigation service is down, instead of an error per block. */
export function ServiceBanner({ consequence, onRetry }: ServiceBannerProps) {
  const { retryAll } = useReferenceData();
  return (
    <div
      role="alert"
      className="flex flex-col gap-4 rounded-xl border border-rocket p-5 sm:flex-row sm:items-center"
    >
      <TriangleAlert aria-hidden="true" className="size-6 shrink-0 text-rocket" />
      <div className="min-w-0 flex-1">
        <p className="font-bold">The investigation service cannot be reached.</p>
        <p className="text-muted-foreground">
          {consequence} Check your connection, then try again in a moment.
        </p>
      </div>
      <Button
        variant="outline"
        onClick={() => {
          retryAll();
          onRetry?.();
        }}
      >
        <RefreshCw aria-hidden="true" />
        Try again
      </Button>
    </div>
  );
}
