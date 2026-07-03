import { useState } from "react";

const TYPE_LABELS = {
  short_answer: "Short answer",
  multiple_choice: "Multiple choice",
  show_working: "Show working",
  exam_style: "Exam style",
};

/** Single question card with a Show Answer toggle (CLAUDE.md Questions Page). */
export default function QuestionBlock({ question }) {
  const [showAnswer, setShowAnswer] = useState(false);

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="font-display text-sm font-semibold text-text-primary">
          Question {question.question_number}
        </span>
        <div className="flex items-center gap-2">
          <span className="rounded border border-border px-2 py-0.5 text-xs text-text-secondary">
            {TYPE_LABELS[question.type] ?? question.type}
          </span>
          <span className="text-xs text-text-secondary">
            {question.marks} mark{question.marks === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      <p className="whitespace-pre-wrap font-mono text-sm text-text-primary">
        {question.question_text}
      </p>

      {question.options && question.options.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1">
          {question.options.map((option, i) => (
            <li key={i} className="font-mono text-sm text-text-secondary">
              {option}
            </li>
          ))}
        </ul>
      )}

      <button
        onClick={() => setShowAnswer((v) => !v)}
        className="mt-4 text-xs font-semibold text-accent hover:underline"
      >
        {showAnswer ? "Hide Answer" : "Show Answer"}
      </button>

      {showAnswer && (
        <div className="mt-3 rounded border border-border bg-background p-3">
          <p className="mb-2 whitespace-pre-wrap font-mono text-sm text-text-primary">
            <span className="text-text-secondary">Answer: </span>
            {question.answer}
          </p>
          <p className="whitespace-pre-wrap font-mono text-xs text-text-secondary">
            Mark scheme: {question.mark_scheme}
          </p>
        </div>
      )}
    </div>
  );
}
