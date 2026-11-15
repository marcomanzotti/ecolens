"use client";

import { useState } from "react";
import { Check, Link2 } from "lucide-react";
import type { Catalog, Location, Variable } from "@/lib/api";
import { isSeason, type CaseQuery } from "@/lib/case-query";
import { formatCoordinates, formatPeriod, placeName, seasonLabel } from "@/lib/format";
import { samePeriod } from "@/lib/opener";
import { Button } from "@/components/ui/button";
import { SelectField } from "@/components/ui/select-field";
import { Skeleton } from "@/components/ui/async-view";

const COPIED_FOR_MS = 2000;

interface CaseHeaderProps {
  query: CaseQuery;
  location: Location | null;
  variable: Variable | null;
  catalog: Catalog | null;
  onChange: (next: Partial<CaseQuery>) => void;
}

function CopyLink() {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      window.setTimeout(() => setCopied(false), COPIED_FOR_MS);
    } catch {
      setCopied(false);
    }
  };
  return (
    <Button variant="outline" onClick={copy} aria-live="polite">
      {copied ? <Check aria-hidden="true" /> : <Link2 aria-hidden="true" />}
      {copied ? "Link copied" : "Copy link to this case"}
    </Button>
  );
}

/** Title of the case and the three controls that reopen it with other choices. */
export function CaseHeader({ query, location, variable, catalog, onChange }: CaseHeaderProps) {
  const title =
    variable && location
      ? `${variable.name} around ${placeName(location)}`
      : location
        ? `Case file: ${placeName(location)}`
        : null;
  const presetId =
    catalog?.period_presets.find((p) => samePeriod(p.period, query.period))?.id ?? "";

  return (
    <header className="grid gap-6 border-b border-line pt-4 pb-8 lg:grid-cols-[1fr_auto] lg:items-end">
      <div className="min-w-0">
        {title ? (
          <h1 className="font-heading text-[clamp(2rem,1.4rem+2.4vw,3.25rem)] leading-[1.02] font-black tracking-[-0.02em]">
            {title}
          </h1>
        ) : (
          <>
            <h1 className="sr-only">Case file</h1>
            <Skeleton className="h-12 w-full max-w-xl" />
          </>
        )}
        <p className="tabular mt-3 flex flex-wrap gap-x-5 gap-y-1 text-muted-foreground">
          {location ? <span>{formatCoordinates(location.lat, location.lon)}</span> : null}
          <span>{formatPeriod(query.period)}</span>
          <span>{seasonLabel(query.season)}</span>
          {variable ? <span>{variable.unit}</span> : null}
        </p>
      </div>

      {catalog ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:flex lg:items-end">
          <SelectField
            id="case-variable"
            label="Variable"
            value={variable?.id ?? ""}
            onChange={(event) => onChange({ variableId: event.target.value })}
            className="col-span-2 sm:col-span-1 lg:w-60"
          >
            {variable ? null : <option value="">Choosing…</option>}
            {catalog.themes.map((theme) => (
              <optgroup key={theme.id} label={theme.label}>
                {catalog.variables
                  .filter((v) => v.theme === theme.id)
                  .map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                    </option>
                  ))}
              </optgroup>
            ))}
          </SelectField>
          <SelectField
            id="case-period"
            label="Years"
            value={presetId}
            onChange={(event) => {
              const preset = catalog.period_presets.find((p) => p.id === event.target.value);
              if (preset) onChange({ period: preset.period });
            }}
            className="lg:w-56"
          >
            {presetId === "" ? <option value="">{formatPeriod(query.period)}</option> : null}
            {catalog.period_presets.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.label}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="case-season"
            label="Part of the year"
            value={query.season}
            onChange={(event) => {
              if (isSeason(event.target.value)) onChange({ season: event.target.value });
            }}
            className="lg:w-40"
          >
            {catalog.seasons.map((season) => (
              <option key={season} value={season}>
                {seasonLabel(season)}
              </option>
            ))}
          </SelectField>
          <div className="col-span-2 sm:col-span-3 lg:col-span-1">
            <CopyLink />
          </div>
        </div>
      ) : null}
    </header>
  );
}
