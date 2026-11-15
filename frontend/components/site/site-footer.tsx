import type { ReactNode } from "react";

/** Fixed id so full-screen views (the tour) can take the footer out of the tab order. */
export const SITE_FOOTER_ID = "site-footer";
const POWER_URL = "https://power.larc.nasa.gov/";
const GEONAMES_URL = "https://www.geonames.org/";
const CC_BY_URL = "https://creativecommons.org/licenses/by/4.0/";
const link = "font-bold text-white underline underline-offset-4 hover:text-neon";

/** A link to another site, opened in a new tab: screen readers hear that before they follow it. */
function ExternalLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} className={link} rel="noopener noreferrer" target="_blank">
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

export function SiteFooter() {
  return (
    <footer id={SITE_FOOTER_ID} className="mt-auto border-t border-line">
      <div className="mx-auto grid w-full max-w-[90rem] gap-6 px-5 py-10 pb-[max(2.5rem,env(safe-area-inset-bottom))] text-sm text-muted-foreground sm:px-8 md:grid-cols-[1fr_auto]">
        <div className="max-w-[62ch] space-y-2">
          <p>
            Data from <ExternalLink href={POWER_URL}>NASA POWER</ExternalLink> (MERRA-2 reanalysis
            and CERES satellite products), fetched when you open a case. EcoLens is an independent
            project for the NASA Space Apps Challenge 2026 and is not endorsed by NASA.
          </p>
          <p>
            Place search: <ExternalLink href={GEONAMES_URL}>GeoNames</ExternalLink> cities above
            15,000 inhabitants, licensed under <ExternalLink href={CC_BY_URL}>CC BY 4.0</ExternalLink>.
          </p>
          <p>Every number and every verdict comes from fixed statistical rules.</p>
        </div>
        <p className="self-end font-heading font-bold text-white">
          The tool finds the trends. You investigate them.
        </p>
      </div>
    </footer>
  );
}
