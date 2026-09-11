import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ConfirmDialog from "../components/ConfirmDialog";
import DifficultyBadge from "../components/DifficultyBadge";
import QuestionBlock from "../components/QuestionBlock";
import ReviewedMarker from "../components/ReviewedMarker";
import LoadingNotice from "../components/LoadingNotice";
import {
  exportQuestionsPdf,
  getQuestions,
  getQuestionsStatus,
  getTopic,
  markQuestionsReviewed,
  refreshQuestions,
} from "../api/client";

const DIFFICULTY_TIERS = ["Fluency", "Reasoning", "Problem-solving"];

/** Question display by difficulty tier (CLAUDE.md Questions Page). */
export default function Questions() {
  const { topicId, difficulty } = useParams();
  const navigate = useNavigate();

  const [topic, setTopic] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [reviewStatus, setReviewStatus] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [errorMessage, setErrorMessage] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [confirmRegenerateOpen, setConfirmRegenerateOpen] = useState(false);
  const [markingReviewed, setMarkingReviewed] = useState(false);

  useEffect(() => {
    setStatus("loading");
    Promise.all([getTopic(topicId), getQuestions(topicId, difficulty), getQuestionsStatus(topicId, difficulty)])
      .then(([topicData, questionsData, statusData]) => {
        setTopic(topicData);
        setQuestions(questionsData);
        setReviewStatus(statusData);
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
  }, [topicId, difficulty]);

  const handleRegenerateConfirmed = async () => {
    setConfirmRegenerateOpen(false);
    setRegenerating(true);
    try {
      const fresh = await refreshQuestions(topicId, difficulty);
      setQuestions(fresh);
      setReviewStatus(await getQuestionsStatus(topicId, difficulty));
    } catch {
      window.alert("Regeneration failed — please try again shortly.");
    } finally {
      setRegenerating(false);
    }
  };

  const handleMarkReviewed = async () => {
    setMarkingReviewed(true);
    try {
      const updated = await markQuestionsReviewed(topicId, difficulty);
      setReviewStatus(updated);
    } catch {
      window.alert("Couldn't mark this reviewed — please try again.");
    } finally {
      setMarkingReviewed(false);
    }
  };

  const handleExportPdf = async () => {
    setExporting(true);
    try {
      // Exports all three difficulty tiers in one PDF (CLAUDE.md: GET
      // /api/export/questions/{topic_id}/pdf covers all tiers), regardless
      // of which tier tab is currently active.
      await exportQuestionsPdf(topicId);
    } catch {
      window.alert("PDF export failed — please try again shortly.");
    } finally {
      setExporting(false);
    }
  };

  if (status === "loading") {
    return <LoadingNotice label="Loading questions…" />;
  }

  if (status === "error") {
    return (
      <div className="p-8">
        <Link to={`/lesson/${topicId}`} className="text-sm text-accent hover:underline">
          &larr; Back to Lesson
        </Link>
        <p className="mt-4 text-tier-problem-solving">{errorMessage}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6 md:p-8">
      <Link to={`/lesson/${topicId}`} className="text-sm text-accent hover:underline">
        &larr; Back to Lesson
      </Link>

      <h1 className="mt-4 mb-3 font-display text-2xl font-bold text-text-primary">
        {topic.topic_name}
      </h1>

      {reviewStatus && (
        <div className="mb-4">
          <ReviewedMarker
            reviewed={reviewStatus.reviewed}
            onMarkReviewed={handleMarkReviewed}
            marking={markingReviewed}
          />
        </div>
      )}

      <div className="mb-6 flex flex-wrap gap-2">
        {DIFFICULTY_TIERS.map((tier) => (
          <button
            key={tier}
            onClick={() => navigate(`/questions/${topicId}/${tier}`)}
            className={`rounded-lg border px-3 py-1.5 transition-colors ${
              tier === difficulty ? "border-accent/50 bg-surface" : "border-border hover:border-accent/30"
            }`}
          >
            <DifficultyBadge tier={tier} />
          </button>
        ))}
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <button
          onClick={() => setConfirmRegenerateOpen(true)}
          disabled={regenerating}
          className="rounded border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:text-text-primary disabled:opacity-50"
        >
          {regenerating ? "Regenerating…" : "Regenerate Questions"}
        </button>
        <button
          onClick={handleExportPdf}
          disabled={exporting}
          title="Exports Fluency, Reasoning and Problem-solving in one PDF"
          className="rounded border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:text-text-primary disabled:opacity-50"
        >
          {exporting ? "Exporting…" : "Export to PDF"}
        </button>
      </div>

      <div className="flex flex-col gap-4">
        {questions.map((q) => (
          <QuestionBlock key={q.question_number} question={q} />
        ))}
      </div>

      <ConfirmDialog
        open={confirmRegenerateOpen}
        title="Regenerate questions?"
        message="This will use API credits — continue?"
        confirmLabel="Regenerate"
        onConfirm={handleRegenerateConfirmed}
        onCancel={() => setConfirmRegenerateOpen(false)}
      />
    </div>
  );
}
