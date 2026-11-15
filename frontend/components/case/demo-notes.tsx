import { FolderOpen } from "lucide-react";
import type { AsyncState } from "@/hooks/use-api";
import type { DemoCase } from "@/lib/api";
import { ErrorNotice, Skeleton } from "@/components/ui/async-view";

/** The guided story of a solved case: a real sequence, so it is numbered. */
export function DemoNotes({ demo }: { demo: AsyncState<DemoCase> }) {
  if (demo.status === "error") return <ErrorNotice error={demo.error} className="my-6" />;
  if (demo.status !== "success") return <Skeleton className="my-6 h-28 w-full" />;

  return (
    <aside aria-labelledby="demo-heading" className="panel my-6 rounded-xl p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <FolderOpen aria-hidden="true" className="mt-1 size-5 shrink-0 text-neon" />
        <div className="min-w-0">
          <h2 id="demo-heading" className="font-heading text-xl font-black">
            Solved case: {demo.data.title}
          </h2>
          <p className="mt-1 text-muted-foreground">{demo.data.blurb}</p>
        </div>
      </div>
      <ol className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {demo.data.narrative.map((line, index) => (
          <li key={line} className="flex gap-3 border-t border-line pt-3 text-sm">
            <span aria-hidden="true" className="tabular font-heading font-black text-neon">
              {index + 1}
            </span>
            <span>{line}</span>
          </li>
        ))}
      </ol>
      <p className="mt-4 text-sm text-muted-foreground">
        This case was saved in advance and opens without asking NASA POWER. Change the variable,
        years or season above to reopen it with live data.
      </p>
    </aside>
  );
}
