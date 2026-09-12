/**
 * When and by what a lesson was generated, and in which content format.
 *
 * Added because content now comes from more than one model and more than one
 * schema version, and from the page alone you could not tell which you were
 * looking at — an older lesson simply looked thinner than a newer one, with
 * no way to know why.
 */
export default function ContentProvenance({ generatedAt, modelUsed, schemaVersion, outdated }) {
  if (!generatedAt) return null;

  const when = new Date(generatedAt).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return (
    <p className="mt-1 font-mono text-xs text-text-secondary">
      Generated {when}
      {modelUsed ? ` · ${modelUsed}` : ""}
      {" · format v"}
      {schemaVersion ?? 1}
      {outdated && <span className="text-tier-reasoning"> · superseded</span>}
    </p>
  );
}
