import Link from "next/link";
import { SiteHeader } from "@/components/site/site-header";
import { DemoCases } from "@/components/landing/demo-cases";
import { Landing } from "@/components/landing/landing";
import { MethodNotes } from "@/components/landing/method-notes";

const navLink =
  "inline-flex min-h-11 items-center rounded-md px-3 text-sm font-bold hover:bg-electric";

export default function Home() {
  return (
    <>
      <SiteHeader>
        <ul className="flex items-center gap-1">
          <li className="hidden sm:block">
            <Link href="#demos-heading" className={navLink}>
              Solved cases
            </Link>
          </li>
          <li>
            <Link href="#method-heading" className={navLink}>
              Method
            </Link>
          </li>
        </ul>
      </SiteHeader>
      <main id="main" className="flex-1">
        <Landing />
        <DemoCases />
        <MethodNotes />
      </main>
    </>
  );
}
