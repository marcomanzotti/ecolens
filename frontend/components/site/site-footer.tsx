const POWER_URL = "https://power.larc.nasa.gov/";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-line">
      <div className="mx-auto grid w-full max-w-[90rem] gap-6 px-5 py-10 pb-[max(2.5rem,env(safe-area-inset-bottom))] text-sm text-muted-foreground sm:px-8 md:grid-cols-[1fr_auto]">
        <div className="max-w-[62ch] space-y-2">
          <p>
            Data from{" "}
            <a
              href={POWER_URL}
              className="font-bold text-white underline underline-offset-4 hover:text-neon"
              rel="noopener noreferrer"
              target="_blank"
            >
              NASA POWER
            </a>{" "}
            (MERRA-2 reanalysis and CERES satellite products), fetched when you open a case. Trend
            Detective is an independent project for the NASA Space Apps Challenge 2026 and is not
            endorsed by NASA.
          </p>
          <p>
            The assistant only reads your question to pick a place and variables. Every number and
            every verdict comes from fixed statistical rules.
          </p>
        </div>
        <p className="self-end font-heading font-bold text-white">
          The tool finds the trends. You investigate them.
        </p>
      </div>
    </footer>
  );
}
