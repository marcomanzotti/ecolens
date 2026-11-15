import { Skeleton } from "@/components/ui/async-view";

/** Same shape as the verdict panel and the chart below it. */
export function VerdictSkeleton() {
  return (
    <div>
      <div className="rounded-2xl border border-line p-6 sm:p-10">
        <div className="grid gap-10 @3xl:grid-cols-[minmax(0,1fr)_14rem] @3xl:gap-12">
          <div className="space-y-5">
            <Skeleton className="h-3 w-40" />
            <Skeleton className="h-14 w-full max-w-2xl" />
            <Skeleton className="h-14 w-3/4 max-w-xl" />
            <div className="grid gap-5 pt-3 sm:grid-cols-2">
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
            </div>
          </div>
          <div className="space-y-3 @3xl:pt-10">
            <Skeleton className="size-12" />
            <Skeleton className="h-14 w-40" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
      </div>
      <div className="mt-12 grid gap-8 @5xl:grid-cols-[minmax(0,1fr)_18rem]">
        <Skeleton className="h-80" />
        <div className="space-y-3 @5xl:pt-12">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-16" />
          <Skeleton className="h-24" />
        </div>
      </div>
    </div>
  );
}

/** Rows shaped like the line-up. */
export function LineupSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="divide-y divide-line rounded-xl border border-line">
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className="grid grid-cols-[2rem_1fr_auto] items-center gap-4 p-4 @min-[52rem]:grid-cols-[2rem_1fr_8rem_9rem_8rem]"
        >
          <Skeleton className="h-5 w-5" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-72 max-w-full" />
          </div>
          <Skeleton className="hidden h-7 @min-[52rem]:block" />
          <Skeleton className="hidden h-4 @min-[52rem]:block" />
          <Skeleton className="h-6 w-24" />
        </div>
      ))}
    </div>
  );
}

/** Shown while the case address is read from the URL. */
export function CaseSkeleton() {
  return (
    <div className="mx-auto w-full max-w-[90rem] px-5 sm:px-8" role="status" aria-live="polite">
      <span className="sr-only">Opening the case…</span>
      <div className="space-y-3 border-b border-line pt-4 pb-8" aria-hidden="true">
        <Skeleton className="h-12 w-full max-w-xl" />
        <Skeleton className="h-4 w-64" />
      </div>
      <div className="mt-10" aria-hidden="true">
        <VerdictSkeleton />
      </div>
    </div>
  );
}
