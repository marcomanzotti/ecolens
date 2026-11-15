import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/site/site-header";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Page not found",
};

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="flex-1">
        <div className="mx-auto max-w-xl px-5 py-24 text-center">
          <h1 className="font-heading text-4xl font-black">No case at this address</h1>
          <p className="mt-3 text-muted-foreground">
            The page you are looking for does not exist. Open a new case and pick any place on
            Earth.
          </p>
          <Button className="mt-6" render={<Link href="/" />} nativeButton={false}>
            Open a new case
          </Button>
        </div>
      </main>
    </>
  );
}
