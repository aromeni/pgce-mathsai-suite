const TIER_STYLES = {
  Foundation: "border-tier-foundation/40 text-tier-foundation bg-tier-foundation/10",
  Developing: "border-tier-developing/40 text-tier-developing bg-tier-developing/10",
  Extending: "border-tier-extending/40 text-tier-extending bg-tier-extending/10",
};

/** Difficulty tier badge (CLAUDE.md Aesthetic — tier colours). */
export default function DifficultyBadge({ tier }) {
  const styles = TIER_STYLES[tier] ?? "border-border text-text-secondary";

  return (
    <span
      className={`rounded border px-2 py-0.5 text-xs font-medium tracking-wide ${styles}`}
    >
      {tier}
    </span>
  );
}
