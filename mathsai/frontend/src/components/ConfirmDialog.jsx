/**
 * On-brand confirmation modal, replacing the native window.confirm() used
 * for Regenerate buttons through Phase 5–8. CLAUDE.md Production Hardening
 * — Cost guardrails on regeneration: deliberate friction against an
 * accidental double-click costing API credits, not a rate limiter against
 * legitimate use.
 */
export default function ConfirmDialog({ open, title, message, confirmLabel = "Continue", onConfirm, onCancel }) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
    >
      <div className="w-full max-w-sm rounded-lg border border-border bg-surface p-5 shadow-xl shadow-black/40">
        <h2 id="confirm-dialog-title" className="mb-2 font-display text-base font-semibold text-text-primary">
          {title}
        </h2>
        <p className="mb-5 text-sm text-text-secondary">{message}</p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:text-text-primary"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded bg-accent px-3 py-1.5 text-sm font-semibold text-background transition-colors hover:opacity-90"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
