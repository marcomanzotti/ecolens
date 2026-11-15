import type { ReactNode, Ref } from "react";
import { cn } from "@/lib/utils";

interface SectionProps {
  id: string;
  title: string;
  lede?: ReactNode;
  actions?: ReactNode;
  className?: string;
  ref?: Ref<HTMLElement>;
  children: ReactNode;
}

/** One block of the case file: a labelled region with a heading and an optional lede. */
export function Section({ id, title, lede, actions, className, ref, children }: SectionProps) {
  const headingId = `${id}-heading`;
  return (
    <section
      ref={ref}
      id={id}
      aria-labelledby={headingId}
      className={cn("scroll-mt-24", className)}
    >
      <header className="mb-8 flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="min-w-0 max-w-[68ch]">
          <h2
            id={headingId}
            className="font-heading text-[clamp(1.75rem,1.3rem+1.6vw,2.5rem)] leading-[1.05] font-black tracking-[-0.015em]"
          >
            {title}
          </h2>
          {lede ? <div className="mt-3 text-muted-foreground">{lede}</div> : null}
        </div>
        {actions}
      </header>
      {children}
    </section>
  );
}
