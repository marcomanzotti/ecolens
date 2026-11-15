import type { ReactNode } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChoiceGroupProps {
  legend: ReactNode;
  /** Short help under the legend. */
  hint?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** A labelled group of choices: a fieldset, so screen readers announce the question. */
export function ChoiceGroup({ legend, hint, className, children }: ChoiceGroupProps) {
  return (
    <fieldset className={cn("min-w-0", className)}>
      <legend className="mb-1 font-heading text-base font-bold">{legend}</legend>
      {hint ? <p className="mb-3 text-sm text-muted-foreground">{hint}</p> : null}
      {children}
    </fieldset>
  );
}

interface ChoiceProps {
  type: "radio" | "checkbox";
  name: string;
  value: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  /** Second line under the label, for tiles. */
  description?: string;
  className?: string;
  children: ReactNode;
}

/**
 * A native radio or checkbox drawn as a chip. Checked chips turn white with Deep Blue text and
 * show a tick, so the state never depends on colour alone.
 */
export function Choice({
  type,
  name,
  value,
  checked,
  onCheckedChange,
  description,
  className,
  children,
}: ChoiceProps) {
  return (
    <label
      data-checked={checked ? "" : undefined}
      className={cn(
        "group relative flex min-h-11 cursor-pointer items-start gap-2 rounded-lg border border-line-strong px-3 py-2.5 select-none",
        "transition-[background-color,border-color,color,transform] duration-150 ease-out active:scale-[0.98]",
        "hover:border-white data-checked:border-white data-checked:bg-white data-checked:text-deep",
        "has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-neon",
        className,
      )}
    >
      <input
        type={type}
        name={name}
        value={value}
        checked={checked}
        onChange={(event) => onCheckedChange(event.target.checked)}
        className="sr-only"
      />
      <span
        aria-hidden="true"
        className={cn(
          "mt-0.5 grid size-4 shrink-0 place-items-center border border-current",
          type === "radio" ? "rounded-full" : "rounded-[4px]",
        )}
      >
        <Check
          className="size-3 scale-50 opacity-0 transition-[opacity,transform] duration-150 group-data-checked:scale-100 group-data-checked:opacity-100"
          strokeWidth={3.5}
        />
      </span>
      <span className="min-w-0 leading-tight">
        <span className="block text-sm font-bold">{children}</span>
        {description ? (
          <span className="mt-1 block text-sm leading-snug text-muted-foreground group-data-checked:text-deep">
            {description}
          </span>
        ) : null}
      </span>
    </label>
  );
}
