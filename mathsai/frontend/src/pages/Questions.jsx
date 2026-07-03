import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import DifficultyBadge from "../components/DifficultyBadge";
import QuestionBlock from "../components/QuestionBlock";
import { getQuestions, getTopic, refreshQuestions } from "../api/client";

const DIFFICULTY_TIERS = ["Foundation", "Developing", "Extending"];

/** Question display by difficulty tier (CLAUDE.md Questions Page). */
export default function Questions() {
  const { topicId, difficulty } = useParams();
  const navigate = useNavigate();

  const [topic, setTopic] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [errorMessage, setErrorMessage] = useState("");
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    setStatus("loading");
    Promise.all([getTopic(topicId), getQuestions(topicId, difficulty)])
      .then(([topicData, questionsData]) => {
        setTopic(topicData);
        setQuestions(questionsData);
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

  const handleRegenerate = async () => {
    if (!window.confirm("This will use API credits — continue?")) return;
    setRegenerating(true);
    try {
      const fresh = await refreshQuestions(topicId, difficulty);
      setQuestions(fresh);
    } catch {
      window.alert("Regeneration failed — please try again shortly.");
    } finally {
      setRegenerating(false);
    }
  };

  if (status === "loading") {
    return <p className="p-8 text-text-secondary">Loading questions…</p>;
  }

  if (status === "error") {
    return (
      <div className="p-8">
        <Link to={`/lesson/${topicId}`} className="text-sm text-accent hover:underline">
          &larr; Back to Lesson
        </Link>
        <p className="mt-4 text-tier-extending">{errorMessage}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6 md:p-8">
      <Link to={`/lesson/${topicId}`} className="text-sm text-accent hover:underline">
        &larr; Back to Lesson
      </Link>

      <h1 className="mt-4 mb-6 font-display text-2xl font-bold text-text-primary">
        {topic.topic_name}
      </h1>

      <div className="mb-6 flex gap-2">
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
          onClick={handleRegenerate}
          disabled={regenerating}
          className="rounded border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:text-text-primary disabled:opacity-50"
        >
          {regenerating ? "Regenerating…" : "Regenerate Questions"}
        </button>
        <button
          disabled
          title="PDF export lands in Phase 7"
          className="rounded border border-border px-3 py-1.5 text-sm text-text-secondary opacity-40"
        >
          Export to PDF
        </button>
      </div>

      <div className="flex flex-col gap-4">
        {questions.map((q) => (
          <QuestionBlock key={q.question_number} question={q} />
        ))}
      </div>
    </div>
  );
}
