"use client";

import type { Catalog, Period, Season } from "@/lib/api";
import { seasonLabel } from "@/lib/format";
import { samePeriod } from "@/lib/opener";
import { Choice, ChoiceGroup } from "@/components/ui/choice";

interface WhenStepProps {
  catalog: Catalog;
  period: Period;
  season: Season;
  onPeriodChange: (period: Period) => void;
  onSeasonChange: (season: Season) => void;
}

/** Question 3: which years, and the whole year or one season. */
export function WhenStep({
  catalog,
  period,
  season,
  onPeriodChange,
  onSeasonChange,
}: WhenStepProps) {
  return (
    <div className="space-y-5">
      <ChoiceGroup legend="Which years?">
        <div className="flex flex-wrap gap-2">
          {catalog.period_presets.map((preset) => (
            <Choice
              key={preset.id}
              type="radio"
              name="period"
              value={preset.id}
              checked={samePeriod(preset.period, period)}
              onCheckedChange={() => onPeriodChange(preset.period)}
            >
              {preset.label}
            </Choice>
          ))}
        </div>
      </ChoiceGroup>
      <ChoiceGroup
        legend="Which part of the year?"
        hint="December belongs to the winter of the following January."
      >
        <div className="flex flex-wrap gap-2">
          {catalog.seasons.map((option) => (
            <Choice
              key={option}
              type="radio"
              name="season"
              value={option}
              checked={option === season}
              onCheckedChange={() => onSeasonChange(option)}
            >
              {seasonLabel(option)}
            </Choice>
          ))}
        </div>
      </ChoiceGroup>
    </div>
  );
}
