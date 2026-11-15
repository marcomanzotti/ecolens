import type { ReactNode } from "react";
import { RefreshCw, TriangleAlert } from "lucide-react";
import type { AsyncState } from "@/hooks/use-api";
import type { ApiError, ClientErrorCode } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const ERROR_TITLES: Record<ClientErrorCode, string> = {
  network_error: "The investigation service cannot be reached",
  no_data: "No usable data here",
  validation_error: "This request could not be understood",
  not_found: "Nothing was found",
  rate_limited: "Too many requests",
  upstream_unavailable: "The data source is not answering",
  upstream_timeout: "The data source took too long",
  assistant_unavailable: "The assistant is not available",
  internal_error: "Something went wrong",
};

/** Codes where trying again cannot change the answer. */
const NOT_RETRYABLE: readonly ClientErrorCode[] = ["no_data", "validation_error", "not_found"];

interface ErrorNoticeProps {
  error: ApiError;
  onRetry?: () => void;
  className?: string;
}

export function ErrorNotice({ error, onRetry, className }: ErrorNoticeProps) {
  const canRetry = onRetry !== undefined && !NOT_RETRYABLE.includes(error.code);
  return (
    <div
      role="alert"
      className={cn("flex gap-3 rounded-md border border-rocket p-4", className)}
    >
      <TriangleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-rocket" />
      <div className="min-w-0 space-y-2">
        <p className="font-bold">{ERROR_TITLES[error.code]}</p>
        <p className="text-muted-foreground">{error.message}</p>
        {error.details.length > 0 ? (
          <ul className="list-disc pl-5 text-sm text-muted-foreground">
            {error.details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        ) : null}
        {canRetry ? (
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw aria-hidden="true" />
            Try again
          </Button>
        ) : null}
      </div>
    </div>
  );
}

interface LoadingNoticeProps {
  /** What is being done, in plain words. Announced to screen readers. */
  message: string;
  children?: ReactNode;
}

export function LoadingNotice({ message, children }: LoadingNoticeProps) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <span aria-hidden="true" className="size-2 animate-pulse rounded-full bg-neon" />
        {message}
      </p>
      <div aria-hidden="true">{children}</div>
    </div>
  );
}

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return <div className={cn("skeleton", className)} />;
}

interface AsyncViewProps<T> {
  state: AsyncState<T>;
  onRetry?: () => void;
  loadingMessage: string;
  skeleton?: ReactNode;
  idle?: ReactNode;
  children: (data: T) => ReactNode;
}

/** Renders exactly one of: idle, loading, error, or the data. */
export function AsyncView<T>({
  state,
  onRetry,
  loadingMessage,
  skeleton,
  idle = null,
  children,
}: AsyncViewProps<T>) {
  if (state.status === "idle") return <>{idle}</>;
  if (state.status === "loading") {
    return <LoadingNotice message={loadingMessage}>{skeleton}</LoadingNotice>;
  }
  if (state.status === "error") return <ErrorNotice error={state.error} onRetry={onRetry} />;
  return <>{children(state.data)}</>;
}
