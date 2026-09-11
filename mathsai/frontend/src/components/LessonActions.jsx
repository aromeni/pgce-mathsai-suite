import MarkAsTaughtForm from "./MarkAsTaughtForm.jsx";

const DIFFICULTY_TIERS = ["Fluency", "Reasoning", "Problem-solving"];

/** The action bar under the lesson: practice tiers, regenerate, export, log taught. */
export default function LessonActions({
  topicId,
  navigate,
  regenerating,
  onRegenerate,
  exporting,
  onExportPdf,
  taughtFormOpen,
  setTaughtFormOpen,
  taughtJustLogged,
  onTaughtLogged,
}) {
  return (
      <div className="mt-10 flex flex-col gap-4 border-t border-border pt-6">
          <div className="flex flex-wrap gap-2">
            {DIFFICULTY_TIERS.map((tier) => (
              <button
                key={tier}
                onClick={() => navigate(`/questions/${topicId}/${tier}`)}
                className="rounded-lg border border-border bg-surface px-4 py-2 text-sm font-semibold text-text-primary transition-colors hover:border-accent/40"
              >
                {tier} Questions
              </button>
            ))}
          </div>
  
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setConfirmRegenerateOpen(true)}
              disabled={regenerating}
              className="rounded border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:text-text-primary disabled:opacity-50"
            >
              {regenerating ? "Regenerating…" : "Regenerate"}
            </button>
  
            <button
              onClick={handleExportPdf}
              disabled={exporting}
              className="rounded border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:text-text-primary disabled:opacity-50"
            >
              {exporting ? "Exporting…" : "Export to PDF"}
            </button>
  
            {!taughtFormOpen && !taughtJustLogged && (
              <button
                onClick={() => setTaughtFormOpen(true)}
                className="rounded bg-tier-foundation/10 px-3 py-1.5 text-sm font-semibold text-tier-foundation transition-colors hover:bg-tier-foundation/20"
              >
                Mark as Taught
              </button>
            )}
            {taughtJustLogged && (
              <span className="text-sm text-tier-foundation">Logged &#x2713;</span>
            )}
          </div>
  
          {taughtFormOpen && (
            <MarkAsTaughtForm
              topicId={topicId}
              onDone={() => {
                setTaughtFormOpen(false);
                setTaughtJustLogged(true);
              }}
            />
          )}
        </div>
  );
}
