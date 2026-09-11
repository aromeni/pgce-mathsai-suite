/**
 * Flags content that needs a diagram drawing before use.
 *
 * The model writes text, so anything genuinely visual — circle theorems,
 * transformations, bearings, box plots — is flagged rather than faked. This
 * is deliberately loud: a question referring to a diagram that does not
 * exist looks fine on screen and is unanswerable once printed, which is the
 * kind of thing you discover in front of a class.
 */
export default function DiagramNotice({ description }) {
  if (!description) return null;

  return (
    <div className="mt-3 rounded-md border border-tier-reasoning/40 bg-tier-reasoning/5 p-3">
      <p className="font-display text-xs font-semibold uppercase tracking-widest text-tier-reasoning">
        Diagram needed
      </p>
      <p className="mt-1 text-sm text-text-primary">{description}</p>
    </div>
  );
}
