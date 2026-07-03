import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import LessonPanel from "../components/LessonPanel";
import { getLesson, getTopic, logTaught, refreshLesson } from "../api/client";

const TABS = [
  { key: "notes", label: "Lesson Notes" },
  { key: "vocabulary", label: "Key Vocabulary" },
  { key: "errors", label: "Common Errors" },
];

const DIFFICULTY_TIERS = ["Foundation", "Developing", "Extending"];

function todayISODate() {
  return new Date().toISOString().slice(0, 10);
}

function MarkAsTaughtForm({ topicId, onDone }) {
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
      {error && <p className="w-full text-xs text-tier-extending">{error}</p>}
    </form>
  );
}

/** Lesson view — full lesson package for a selected topic (CLAUDE.md Lesson Page). */
export default function Lesson() {
  const { topicId } = useParams();
  const navigate = useNavigate();

  const [topic, setTopic] = useState(null);
  const [lesson, setLesson] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [errorMessage, setErrorMessage] = useState("");
  const [activeTab, setActiveTab] = useState("notes");
  const [regenerating, setRegenerating] = useState(false);
  const [taughtFormOpen, setTaughtFormOpen] = useState(false);
  const [taughtJustLogged, setTaughtJustLogged] = useState(false);

  const load = () => {
    setStatus("loading");
    Promise.all([getTopic(topicId), getLesson(topicId)])
      .then(([topicData, lessonData]) => {
        setTopic(topicData);
        setLesson(lessonData);
        setStatus("ready");
      })
      .catch((err) => {
        setErrorMessage(
          err.response?.status === 404
            ? "Topic not found."
            : "Generation temporarily unavailable — please try again shortly.",
        );
        setStatus("error");
      });
  };

  useEffect(load, [topicId]);

  const handleRegenerate = async () => {
    if (!window.confirm("This will use API credits — continue?")) return;
    setRegenerating(true);
    try {
      const fresh = await refreshLesson(topicId);
      setLesson(fresh);
    } catch {
      // refreshLesson raises on failure without a stale fallback being possible
      // here (get_lesson already returns stale content instead of raising when
      // a stale row exists) — a raised error means there was nothing to fall
      // back to.
      window.alert("Regeneration failed — please try again shortly.");
    } finally {
      setRegenerating(false);
    }
  };

  if (status === "loading") {
    return <p className="p-8 text-text-secondary">Loading lesson…</p>;
  }

  if (status === "error") {
    return (
      <div className="p-8">
        <Link to="/" className="text-sm text-accent hover:underline">
          &larr; Back to Dashboard
        </Link>
        <p className="mt-4 text-tier-extending">{errorMessage}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6 md:p-8">
      <Link to="/" className="text-sm text-accent hover:underline">
        &larr; Back to Dashboard
      </Link>

      <div className="mt-4 mb-6">
        <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-text-secondary">
          <span className="rounded border border-border px-2 py-0.5">{topic.key_stage}</span>
          <span>{topic.strand}</span>
          {topic.edexcel_ref && <span>&middot; {topic.edexcel_ref}</span>}
        </div>
        <h1 className="font-display text-2xl font-bold text-text-primary">{topic.topic_name}</h1>
        {lesson.stale && (
          <p className="mt-2 text-xs text-tier-developing">
            Last generated {new Date(lesson.generated_at).toLocaleDateString()} — refresh failed,
            showing previous version.
          </p>
        )}
      </div>

      <div className="mb-6 flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 text-sm font-display transition-colors ${
              activeTab === t.key
                ? "border-b-2 border-accent text-accent"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <LessonPanel lesson={lesson} tab={activeTab} />

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
            onClick={handleRegenerate}
            disabled={regenerating}
            className="rounded border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:text-text-primary disabled:opacity-50"
          >
            {regenerating ? "Regenerating…" : "Regenerate"}
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
    </div>
  );
}
