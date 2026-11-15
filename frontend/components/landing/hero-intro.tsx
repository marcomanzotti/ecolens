import type { Catalog } from "@/lib/api";
import { revealStep } from "@/lib/motion";

function lede(catalog: Catalog | null): string {
  if (!catalog) {
    return "Pick any place on Earth. EcoLens questions decades of satellite and reanalysis data and tells you which changes are statistically significant, and how sure it can be.";
  }
  return `Pick any place on Earth. EcoLens questions ${catalog.variables.length} variables from NASA POWER, ${catalog.min_year} to ${catalog.max_year}, and tells you which changes are statistically significant, and how sure it can be.`;
}

/** The product in one line: set large, one sentence per line on wide screens. */
export function HeroHeading() {
  return (
    <h1
      id="hero-heading"
      className="reveal pt-4 font-heading text-[clamp(2.1rem,1.1rem+3.2vw,4rem)] leading-[0.95] font-black tracking-[-0.025em] lg:pt-[max(2.5rem,8svh)]"
      style={revealStep(0)}
    >
      The tool finds the trends.
      <span className="mt-1 block">You investigate them.</span>
    </h1>
  );
}

interface HeroLedeProps {
  /** Counts come from the catalog; without it the lede stays general. */
  catalog: Catalog | null;
}

export function HeroLede({ catalog }: HeroLedeProps) {
  return (
    <p
      className="reveal mt-6 hidden max-w-[46ch] text-lg leading-relaxed text-muted-foreground sm:block lg:mt-8"
      style={revealStep(1)}
    >
      {lede(catalog)}
    </p>
  );
}
