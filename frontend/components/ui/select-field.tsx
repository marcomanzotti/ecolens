import type { ComponentProps, ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface SelectFieldProps extends Omit<ComponentProps<"select">, "className"> {
  label: ReactNode;
  /** Hide the label visually (it stays available to screen readers). */
  labelHidden?: boolean;
  className?: string;
}

/** A native select: the most robust picker on phones, styled to match the chips. */
export function SelectField({
  label,
  labelHidden,
  className,
  id,
  children,
  ...props
}: SelectFieldProps) {
  return (
    <div className={cn("min-w-0", className)}>
      <label
        htmlFor={id}
        className={cn("mb-1.5 block text-sm font-bold", labelHidden && "sr-only")}
      >
        {label}
      </label>
      <div className="relative">
        <select
          id={id}
          className="min-h-11 w-full cursor-pointer appearance-none truncate rounded-lg border border-line-strong bg-deep py-2 pr-10 pl-3 font-sans text-base text-white transition-[border-color] duration-150 hover:border-white"
          {...props}
        >
          {children}
        </select>
        <ChevronDown
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2"
        />
      </div>
    </div>
  );
}
