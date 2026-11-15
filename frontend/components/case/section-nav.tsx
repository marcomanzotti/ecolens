export const CASE_SECTIONS = [
  { id: "verdict", label: "Verdict" },
  { id: "cracked", label: "When it cracked" },
  { id: "lineup", label: "Line-up" },
  { id: "map", label: "Where it flips" },
  { id: "witnesses", label: "Witnesses" },
  { id: "limitations", label: "Limitations" },
] as const;

/** Sticky table of contents of the case file. Scrolls sideways on phones. */
export function SectionNav() {
  return (
    <nav
      aria-label="Sections of the case"
      className="sticky top-0 z-30 -mx-5 border-b border-line bg-deep/90 px-5 backdrop-blur-md sm:-mx-8 sm:px-8"
    >
      <ul className="scrollbar-none -mx-2 flex gap-1 overflow-x-auto overscroll-x-contain py-2 [mask-image:linear-gradient(to_right,black_85%,transparent)] md:[mask-image:none]">
        {CASE_SECTIONS.map((section) => (
          <li key={section.id} className="shrink-0">
            <a
              href={`#${section.id}`}
              className="inline-flex min-h-10 items-center rounded-md px-3 text-sm font-bold whitespace-nowrap text-muted-foreground transition-[background-color,color] duration-150 hover:bg-electric hover:text-white"
            >
              {section.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
