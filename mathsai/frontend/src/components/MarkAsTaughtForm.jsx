import { useState } from "react";
import { logTaught } from "../api/client";

function todayISODate() {
  return new Date().toISOString().slice(0, 10);
}

/** Logs a topic as taught against a class and date. */
export default function MarkAsTaughtForm({ topicId, onDone }) {
  const [classLabel, setClassLabel] = useState("");
  const [taughtDate, setTaughtDate] = useState(todayISODate());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await logTaught({
        topic_id: Number(topicId),
        taught_date: taughtDate,
        class_label: classLabel || null,
      });
      onDone();
    } catch {
      setError("Couldn't log this — please try again.");
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface p-3"
    >
      <input
        type="date"
        value={taughtDate}
        onChange={(e) => setTaughtDate(e.target.value)}
        className="rounded border border-border bg-background px-2 py-1 text-sm text-text-primary"
        required
      />
      <input
        type="text"
        value={classLabel}
        onChange={(e) => setClassLabel(e.target.value)}
        placeholder="Class label (e.g. Year 9 Set 2)"
        className="min-w-[10rem] flex-1 rounded border border-border bg-background px-2 py-1 text-sm text-text-primary placeholder:text-text-secondary"
      />
      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-accent px-3 py-1 text-sm font-semibold text-background disabled:opacity-50"
      >
        {submitting ? "Logging…" : "Log"}
      </button>
      {error && <p className="w-full text-xs text-tier-problem-solving">{error}</p>}
    </form>
  );
}

/** Lesson view — full lesson package for a selected topic (CLAUDE.md Lesson Page). */
