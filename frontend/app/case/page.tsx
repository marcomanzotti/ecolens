import { Suspense } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Plus } from "lucide-react";
import { SiteHeader } from "@/components/site/site-header";
import { CaseView } from "@/components/case/case-view";
import { CaseSkeleton } from "@/components/case/case-skeleton";

export const metadata: Metadata = {
  title: "Case file",
};

export default function CasePage() {
  return (
    <>
      <SiteHeader>
        <Link
          href="/"
          className="inline-flex min-h-11 items-center gap-1.5 rounded-md border border-line-strong px-3 text-sm font-bold transition-[background-color,border-color] duration-150 hover:border-white hover:bg-electric"
        >
          <Plus aria-hidden="true" className="size-4" />
          New case
        </Link>
      </SiteHeader>
      <main id="main" className="flex-1">
        {/* The case lives in the URL: reading it needs the browser, behind this boundary. */}
        <Suspense fallback={<CaseSkeleton />}>
          <CaseView />
        </Suspense>
      </main>
    </>
  );
}
