import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import ConfirmDialog from "../components/ConfirmDialog";
import TeachingSequence from "../components/TeachingSequence.jsx";
import AdaptivePanel from "../components/AdaptivePanel.jsx";
import ReferencePanel from "../components/ReferencePanel.jsx";
import LegacyLessonPanel from "../components/LegacyLessonPanel.jsx";
import OutdatedFormatNotice from "../components/OutdatedFormatNotice.jsx";
import ReviewedMarker from "../components/ReviewedMarker";
import LoadingNotice from "../components/LoadingNotice";
import LessonActions from "../components/LessonActions.jsx";
import {
  exportLessonPdf,
  getLesson,
  getTopic,
  markLessonReviewed,
  refreshLesson,
} from "../api/client";

// Ordered by when you need them: Teach while teaching, Adapt while planning
// against a class list, Reference when you want a definition.
const TABS = [
  { key: "teach", label: "Teach" },
  { key: "adapt", label: "Adapt" },
  { key: "reference", label: "Reference" },
];

const DIFFICULTY_TIERS = ["Fluency", "Reasoning", "Problem-solving"];

export default function Lesson() {
  const { topicId } = useParams();
  const navigate = useNavigate();

  const [topic, setTopic] = useState(null);
  const [lesson, setLesson] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [errorMessage, setErrorMessage] = useState("");
  const [activeTab, setActiveTab] = useState("teach");
  const [regenerating, setRegenerating] = useState(false);
  const [taughtFormOpen, setTaughtFormOpen] = useState(false);
  const [taughtJustLogged, setTaughtJustLogged] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [confirmRegenerateOpen, setConfirmRegenerateOpen] = useState(false);
  const [markingReviewed, setMarkingReviewed] = useState(false);

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

  const handleRegenerateConfirmed = async () => {
    setConfirmRegenerateOpen(false);
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

  const handleMarkReviewed = async () => {
    setMarkingReviewed(true);
    try {
      const updated = await markLessonReviewed(topicId);
      setLesson(updated);
    } catch {
      window.alert("Couldn't mark this reviewed — please try again.");
    } finally {
      setMarkingReviewed(false);
    }
  };

  const handleExportPdf = async () => {
    setExporting(true);
    try {
      await exportLessonPdf(topicId);
    } catch {
      window.alert("PDF export failed — please try again shortly.");
    } finally {
      setExporting(false);
    }
  };

  if (status === "loading") {
    return <LoadingNotice label="Loading lesson…" />;
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
        <div className="mt-3">
          <ReviewedMarker
            reviewed={lesson.reviewed}
            onMarkReviewed={handleMarkReviewed}
            marking={markingReviewed}
          />
        </div>
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

      {lesson.outdated_format ? (
        <>
          <OutdatedFormatNotice onRegenerate={() => setConfirmRegenerateOpen(true)} busy={regenerating} />
          {activeTab === "reference" ? (
            <ReferencePanel lesson={lesson} />
          ) : (
            <LegacyLessonPanel lesson={lesson} />
          )}
        </>
      ) : (
        <>
          {activeTab === "teach" && (
            <TeachingSequence
              lesson={lesson}
              onGoToQuestions={(tier) => navigate(`/questions/${topicId}/${tier}`)}
            />
          )}
          {activeTab === "adapt" && <AdaptivePanel adaptive={lesson.adaptive_teaching} />}
          {activeTab === "reference" && <ReferencePanel lesson={lesson} />}
        </>
      )}

      <LessonActions
        topicId={topicId}
        navigate={navigate}
        regenerating={regenerating}
        onRegenerate={() => setConfirmRegenerateOpen(true)}
        exporting={exporting}
        onExportPdf={handleExportPdf}
        taughtFormOpen={taughtFormOpen}
        setTaughtFormOpen={setTaughtFormOpen}
        taughtJustLogged={taughtJustLogged}
        onTaughtLogged={() => {
          setTaughtFormOpen(false);
          setTaughtJustLogged(true);
        }}
      />

      <ConfirmDialog
        open={confirmRegenerateOpen}
        title="Regenerate lesson?"
        message="This will use API credits — continue?"
        confirmLabel="Regenerate"
        onConfirm={handleRegenerateConfirmed}
        onCancel={() => setConfirmRegenerateOpen(false)}
      />
    </div>
  );
}
