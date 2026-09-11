const TIER_STYLES = {
  Fluency: "border-tier-fluency/40 text-tier-fluency bg-tier-fluency/10",
  Reasoning: "border-tier-reasoning/40 text-tier-reasoning bg-tier-reasoning/10",
  "Problem-solving":
    "border-tier-problem-solving/40 text-tier-problem-solving bg-tier-problem-solving/10",
};

/** Practice tier badge (CLAUDE.md Aesthetic — tier colours). */
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
