/**
 * Amber "Not yet checked" marker + Mark reviewed action (CLAUDE.md
 * Production Hardening — the `reviewed` workflow). Self-verification of AI
 * content isn't reliable, so a qualified teacher reviewing before classroom
 * use is the one dependable check — this just makes that step visible and
 * easy to record. Renders nothing once reviewed, to keep the UI quiet.
 */
export default function ReviewedMarker({ reviewed, onMarkReviewed, marking }) {
  if (reviewed) return null;

  return (
    <div className="flex items-center gap-2 rounded border border-tier-developing/40 bg-tier-developing/10 px-3 py-1.5 text-xs text-tier-developing">
      <span>Not yet checked</span>
      <button
        onClick={onMarkReviewed}
        disabled={marking}
        className="font-semibold underline disabled:opacity-50"
      >
        {marking ? "Marking…" : "Mark reviewed"}
      </button>
    </div>
  );
}
