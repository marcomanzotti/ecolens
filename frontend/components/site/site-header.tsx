import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** The app's own mark: a lens with a trend line crossing it. Not a NASA or Space Apps logo. */
export function DetectiveMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cn("size-8", className)}>
      <circle cx="14" cy="14" r="10" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <path d="M21.5 21.5 29 29" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path
        d="M7 18.5 11 15l3 2 6-7"
        fill="none"
        stroke="var(--brand-neon-yellow)"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface SiteHeaderProps {
  /** Extra navigation on the right (links or actions). */
  children?: ReactNode;
  className?: string;
}

export function SiteHeader({ children, className }: SiteHeaderProps) {
  return (
    <header
      className={cn(
        "mx-auto flex w-full max-w-[90rem] items-center justify-between gap-4 px-5 pt-[max(1rem,env(safe-area-inset-top))] pb-4 sm:px-8",
        className,
      )}
    >
      <Link
        href="/"
        className="group flex items-center gap-2.5 rounded-md py-1 pr-2 font-heading text-lg leading-none font-black tracking-tight"
      >
        <DetectiveMark className="transition-transform duration-200 ease-out group-hover:-rotate-6" />
        <span translate="no">Trend Detective</span>
      </Link>
      {children ? <nav aria-label="Main">{children}</nav> : null}
    </header>
  );
}
