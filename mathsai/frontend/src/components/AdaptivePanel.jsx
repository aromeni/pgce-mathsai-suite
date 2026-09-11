import PhaseSection from "./PhaseSection.jsx";

const CARD = "rounded-lg border border-border bg-surface p-4";
const LABEL = "font-display text-xs uppercase tracking-widest text-text-secondary";

/**
 * Adaptive teaching (Teachers' Standard 5).
 *
 * Kept on its own tab rather than threaded through the sequence: it is read
 * while planning, against a class list, not while teaching. Everything here
 * is a different route to the same learning goal — never a lower one.
 */
export default function AdaptivePanel({ adaptive }) {
  const language = adaptive.language_support;

  return (
    <div className="flex flex-col gap-6">
      <p className="rounded-lg border border-accent/30 bg-accent/5 p-3 text-sm text-text-primary">
        Same learning goal for every pupil — different routes in. Reduce the reading
        demand, the memory demand or the abstraction, never the mathematics.
      </p>

      <PhaseSection label="Scaffolds" subtitle="Each with the point it comes off">
        <div className="flex flex-col gap-3">
          {adaptive.scaffolds.map((s, i) => (
            <div key={i} className={CARD}>
              <p className="text-sm text-text-secondary">
                <span className="text-tier-problem-solving">Barrier: </span>
                {s.barrier}
              </p>
              <p className="mt-2 text-sm text-text-primary">
                <span className="text-accent">Scaffold: </span>
                {s.scaffold}
              </p>
              <p className="mt-2 text-sm text-text-secondary">
                <span className="text-tier-fluency">Remove when: </span>
                {s.remove_when}
              </p>
            </div>
          ))}
        </div>
      </PhaseSection>

      <PhaseSection label="Concrete" subtitle="Concrete → pictorial → abstract">
        <div className="flex flex-col gap-3">
          {adaptive.concrete_representations.map((r, i) => (
            <div key={i} className={CARD}>
              <p className="font-display text-sm font-semibold text-accent">{r.resource}</p>
              <p className="mt-1 text-sm text-text-primary">{r.how_to_use}</p>
              <p className="mt-2 text-sm text-text-secondary">
                Bridge to abstract: {r.bridge_to_abstract}
              </p>
            </div>
          ))}
        </div>
      </PhaseSection>

      <PhaseSection label="Language" subtitle="EAL and reading-demand support">
        <div className="flex flex-col gap-5">
          {language.false_friends.length > 0 && (
            <div>
              <p className={LABEL}>Words that mean something else in maths</p>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <tbody>
                    {language.false_friends.map((f, i) => (
                      <tr key={i} className="border-b border-border/50 align-top">
                        <td className="py-2 pr-4 font-semibold text-accent">{f.word}</td>
                        <td className="py-2 pr-4 text-text-secondary">{f.everyday_meaning}</td>
                        <td className="py-2 text-text-primary">{f.maths_meaning}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {language.tier_2_vocabulary.length > 0 && (
            <div>
              <p className={LABEL}>Academic vocabulary in word problems</p>
              <ul className="mt-2 flex flex-col gap-1 text-sm">
                {language.tier_2_vocabulary.map((w, i) => (
                  <li key={i}>
                    <span className="text-accent">{w.word}</span>
                    <span className="text-text-secondary"> — {w.meaning_in_context}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {language.sentence_stems.length > 0 && (
            <div>
              <p className={LABEL}>Sentence stems for explaining reasoning</p>
              <ul className="mt-2 list-disc pl-4 text-sm text-text-primary">
                {language.sentence_stems.map((s, i) => (
                  <li key={i} className="my-1">{s}</li>
                ))}
              </ul>
            </div>
          )}

          {language.reduced_language_versions.length > 0 && (
            <div>
              <p className={LABEL}>Same maths, less English</p>
              <div className="mt-2 flex flex-col gap-3">
                {language.reduced_language_versions.map((r, i) => (
                  <div key={i} className={CARD}>
                    <p className="text-sm text-text-secondary line-through decoration-text-secondary/40">
                      {r.original}
                    </p>
                    <p className="mt-2 text-sm text-text-primary">{r.reworded}</p>
                    {r.same_maths_because && (
                      <p className="mt-2 border-t border-border pt-2 text-xs text-tier-fluency">
                        Demand unchanged: {r.same_maths_because}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </PhaseSection>

      <PhaseSection label="Stretch" subtitle="Depth on the same content, not acceleration">
        <ul className="list-disc pl-4 text-sm text-text-primary">
          {adaptive.stretch.map((s, i) => (
            <li key={i} className="my-1">{s}</li>
          ))}
        </ul>
      </PhaseSection>
    </div>
  );
}
