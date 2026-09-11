/**
 * Shown on lessons generated before the teaching sequence existed.
 *
 * Deliberately an offer, not an automatic upgrade: regenerating every
 * previously generated topic on a schema bump would spend Anthropic credits
 * across the whole curriculum without anyone asking for it.
 */
export default function OutdatedFormatNotice({ onRegenerate, busy }) {
  return (
    <div className="mb-6 rounded-lg border border-tier-reasoning/40 bg-tier-reasoning/5 p-4">
      <p className="font-display text-xs font-semibold uppercase tracking-widest text-tier-reasoning">
        Earlier lesson format
      </p>
      <p className="mt-1 text-sm text-text-primary">
        This was generated before the teaching sequence, so it has no starter,
        modelled examples, guided practice or adaptive teaching. It is still
        usable as it stands.
      </p>
      <button
        type="button"
        onClick={onRegenerate}
        disabled={busy}
        className="mt-3 rounded-lg border border-tier-reasoning/50 px-3 py-1.5 text-sm text-tier-reasoning transition-colors hover:bg-tier-reasoning/10 disabled:opacity-50"
      >
        {busy ? "Regenerating…" : "Regenerate with the full sequence"}
      </button>
    </div>
  );
}
