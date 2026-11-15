"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export const CASE_SECTIONS = [
  { id: "verdict", label: "Verdict" },
  { id: "future", label: "The future" },
  { id: "cracked", label: "When it cracked" },
  { id: "lineup", label: "Line-up" },
  { id: "map", label: "Where it flips" },
  { id: "witnesses", label: "Witnesses" },
  { id: "limitations", label: "Limitations" },
] as const;

type SectionId = (typeof CASE_SECTIONS)[number]["id"];

/** A section is "being read" once its top passes this share of the viewport height. */
const READING_LINE = 0.3;

function sectionUnderLine(): SectionId {
  const line = window.innerHeight * READING_LINE;
  let current: SectionId = CASE_SECTIONS[0].id;
  for (const section of CASE_SECTIONS) {
    const node = document.getElementById(section.id);
    if (node && node.getBoundingClientRect().top <= line) current = section.id;
  }
  return current;
}

/** Follows which section is on screen, so the bar can mark it. */
function useCurrentSection(): SectionId {
  const [current, setCurrent] = useState<SectionId>(CASE_SECTIONS[0].id);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setCurrent(sectionUnderLine()));
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);
  return current;
}

/** Sticky table of contents of the case file. Scrolls sideways on phones, following the reader. */
export function SectionNav() {
  const current = useCurrentSection();
  const listRef = useRef<HTMLUListElement>(null);

  // Keep the current link in view inside the sideways-scrolling bar (phones).
  useEffect(() => {
    const list = listRef.current;
    const link = list?.querySelector<HTMLElement>(`[data-section="${current}"]`);
    if (!list || !link) return;
    const left = link.offsetLeft - (list.clientWidth - link.offsetWidth) / 2;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    list.scrollTo({ left: Math.max(0, left), behavior: still ? "auto" : "smooth" });
  }, [current]);

  return (
    <nav
      aria-label="Sections of the case"
      className="sticky top-0 z-30 -mx-5 border-b border-line bg-deep/90 px-5 backdrop-blur-md sm:-mx-8 sm:px-8"
    >
      <ul
        ref={listRef}
        className="scrollbar-none relative -mx-2 flex gap-1 overflow-x-auto overscroll-x-contain py-1.5 [mask-image:linear-gradient(to_right,black_85%,transparent)] md:[mask-image:none]"
      >
        {CASE_SECTIONS.map((section) => {
          const isCurrent = section.id === current;
          return (
            <li key={section.id} className="shrink-0">
              <a
                href={`#${section.id}`}
                data-section={section.id}
                aria-current={isCurrent ? "location" : undefined}
                className={cn(
                  "relative inline-flex min-h-11 items-center rounded-md px-3 text-sm font-bold whitespace-nowrap transition-[background-color,color] duration-150 hover:bg-electric hover:text-white",
                  isCurrent ? "text-white" : "text-muted-foreground",
                )}
              >
                {section.label}
                <span
                  aria-hidden="true"
                  className={cn(
                    "absolute inset-x-3 bottom-1 h-0.5 origin-left rounded-full bg-neon transition-transform duration-200 ease-[var(--ease-out)]",
                    isCurrent ? "scale-x-100" : "scale-x-0",
                  )}
                />
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
