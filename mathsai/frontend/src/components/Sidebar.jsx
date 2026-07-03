const KEY_STAGES = ["KS3", "KS4"];

/**
 * KS3/KS4 toggle + strand filter. `strands` is the list of strand names
 * actually present for the current key stage (derived from loaded topics,
 * not hardcoded) so the filter never silently mismatches the taxonomy.
 */
export default function Sidebar({ keyStage, onKeyStageChange, strand, onStrandChange, strands }) {
  return (
    <nav
      aria-label="Topic filters"
      className="w-full shrink-0 md:w-56 md:border-r md:border-border md:pr-6"
    >
      <section className="mb-8">
        <h2 className="mb-3 text-xs font-display uppercase tracking-widest text-text-secondary">
          Key Stage
        </h2>
        <div
          role="radiogroup"
          aria-label="Key stage"
          className="flex rounded-lg border border-border bg-surface p-1"
        >
          {KEY_STAGES.map((ks) => (
            <button
              key={ks}
              type="button"
              role="radio"
              aria-checked={keyStage === ks}
              onClick={() => onKeyStageChange(ks)}
              className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150 ${
                keyStage === ks
                  ? "bg-accent text-background"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {ks}
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-xs font-display uppercase tracking-widest text-text-secondary">
          Strand
        </h2>
        <ul className="flex flex-col gap-1" role="listbox" aria-label="Strand filter">
          <li>
            <button
              type="button"
              role="option"
              aria-selected={strand === null}
              onClick={() => onStrandChange(null)}
              className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors duration-150 ${
                strand === null
                  ? "bg-surface text-accent"
                  : "text-text-secondary hover:bg-surface hover:text-text-primary"
              }`}
            >
              All strands
            </button>
          </li>
          {strands.map((s) => (
            <li key={s}>
              <button
                type="button"
                role="option"
                aria-selected={strand === s}
                onClick={() => onStrandChange(s)}
                className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors duration-150 ${
                  strand === s
                    ? "bg-surface text-accent"
                    : "text-text-secondary hover:bg-surface hover:text-text-primary"
                }`}
              >
                {s}
              </button>
            </li>
          ))}
        </ul>
      </section>
    </nav>
  );
}
