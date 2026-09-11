import { useState } from "react";

/**
 * One phase of the lesson, collapsible.
 *
 * The page is read while teaching, so phases are labelled and ordered the
 * way the lesson runs and open by default — you scroll, you do not hunt.
 * Collapsing exists so a phase you have finished can be folded away rather
 * than competing for attention with the one you are on.
 */
export default function PhaseSection({ label, subtitle, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="border-b border-border pb-6 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-baseline gap-3 text-left"
      >
        <span className="font-display text-xs font-bold uppercase tracking-[0.2em] text-accent">
          {label}
        </span>
        {subtitle && (
          <span className="flex-1 truncate text-xs text-text-secondary">{subtitle}</span>
        )}
        <span className="text-xs text-text-secondary" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>
      {open && <div className="mt-4">{children}</div>}
    </section>
  );
}
