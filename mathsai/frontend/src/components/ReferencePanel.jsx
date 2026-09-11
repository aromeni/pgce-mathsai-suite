/**
 * Vocabulary and misconceptions — reference material, not part of the
 * teaching flow, so it sits behind its own tab where it is not competing for
 * attention mid-lesson.
 */
export default function ReferencePanel({ lesson }) {
  return (
    <div className="flex flex-col gap-8">
      <section>
        <h3 className="mb-3 font-display text-sm uppercase tracking-widest text-text-secondary">
          Key vocabulary
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <tbody>
              {(lesson.key_vocabulary ?? []).map((item, i) => (
                <tr key={i} className="border-b border-border/50 align-top">
                  <td className="py-3 pr-4 font-semibold text-accent">
                    {item.term}
                    {item.notation && (
                      <span className="ml-2 font-mono text-xs text-text-secondary">
                        {item.notation}
                      </span>
                    )}
                  </td>
                  <td className="py-3 text-text-primary">
                    {item.definition}
                    {item.everyday_meaning && (
                      <span className="mt-1 block text-xs text-text-secondary">
                        Everyday meaning: {item.everyday_meaning}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="mb-3 font-display text-sm uppercase tracking-widest text-text-secondary">
          Common misconceptions
        </h3>
        <div className="flex flex-col gap-4">
          {(lesson.common_errors ?? []).map((item, i) => (
            <div
              key={i}
              className="rounded-lg border border-tier-problem-solving/30 bg-tier-problem-solving/5 p-4"
            >
              <p className="text-sm">
                <span className="font-display font-semibold text-tier-problem-solving">
                  Error:{" "}
                </span>
                <span className="text-text-primary">{item.error}</span>
              </p>
              {item.why_it_happens && (
                <p className="mt-2 text-sm text-text-secondary">
                  Why it happens: {item.why_it_happens}
                </p>
              )}
              <p className="mt-2 text-sm">
                <span className="font-display font-semibold text-tier-fluency">
                  Correction:{" "}
                </span>
                <span className="text-text-primary">{item.correction}</span>
              </p>
              {item.address_at && (
                <p className="mt-2 text-xs text-text-secondary">
                  Address at: {item.address_at}
                </p>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
