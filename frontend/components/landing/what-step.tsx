"use client";

import type { Catalog, ThemeId } from "@/lib/api";
import { Choice, ChoiceGroup } from "@/components/ui/choice";
import { SelectField } from "@/components/ui/select-field";

interface WhatStepProps {
  catalog: Catalog;
  themes: readonly ThemeId[];
  variableId: string | null;
  onToggleTheme: (theme: ThemeId, on: boolean) => void;
  onVariableChange: (variableId: string | null) => void;
}

const LINEUP_CHOICE = "";

/** Question 1: themes as tiles, then an optional single variable. */
export function WhatStep({
  catalog,
  themes,
  variableId,
  onToggleTheme,
  onVariableChange,
}: WhatStepProps) {
  const variables = catalog.variables;
  const selectedTheme = variables.find((variable) => variable.id === variableId)?.theme;
  // Keep the chosen variable listed even if its theme was switched off afterwards.
  const shownThemes = catalog.themes.filter(
    (theme) => themes.length === 0 || themes.includes(theme.id) || theme.id === selectedTheme,
  );

  return (
    <div className="space-y-5">
      <ChoiceGroup
        legend="What are you investigating?"
        hint="Pick one or more themes, or none to question every variable."
      >
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
          {catalog.themes.map((theme) => (
            <Choice
              key={theme.id}
              type="checkbox"
              name="themes"
              value={theme.id}
              checked={themes.includes(theme.id)}
              onCheckedChange={(on) => onToggleTheme(theme.id, on)}
              description={theme.question}
            >
              {theme.label}
            </Choice>
          ))}
        </div>
      </ChoiceGroup>
      <SelectField
        id="variable"
        label="Main suspect"
        value={variableId ?? LINEUP_CHOICE}
        onChange={(event) => onVariableChange(event.target.value || null)}
      >
        <option value={LINEUP_CHOICE}>Let the line-up pick the strongest trend</option>
        {shownThemes.map((theme) => (
          <optgroup key={theme.id} label={theme.label}>
            {variables
              .filter((variable) => variable.theme === theme.id)
              .map((variable) => (
                <option key={variable.id} value={variable.id}>
                  {variable.name}
                </option>
              ))}
          </optgroup>
        ))}
      </SelectField>
    </div>
  );
}
