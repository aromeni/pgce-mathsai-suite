import { useState } from "react";
import DiagramNotice from "./DiagramNotice.jsx";

/**
 * One practice question with a Show answer toggle.
 *
 * The mark scheme is in Edexcel notation (M1/A1/B1), and where the question
 * was built to expose a specific misconception that is named alongside the
 * answer — a wrong answer tells you more when you know which misconception
 * it maps to.
 */
export default function QuestionBlock({ question }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <article className="rounded-lg border border-border bg-surface p-4 transition-colors hover:border-border/80">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="font-display text-sm font-bold text-accent">
          {question.question_number}
        </span>
        <span className="rounded border border-border px-2 py-0.5 text-xs text-text-secondary">
          {question.type.replace(/_/g, " ")}
        </span>
        {question.command_word && (
          <span className="rounded border border-accent/30 bg-accent/10 px-2 py-0.5 text-xs text-accent">
            {question.command_word}
          </span>
        )}
        {question.calculator_allowed === false && (
          <span className="rounded border border-border px-2 py-0.5 text-xs text-text-secondary">
            non-calculator
          </span>
        )}
        <span className="ml-auto text-xs text-text-secondary">
          {question.marks} {question.marks === 1 ? "mark" : "marks"}
        </span>
      </div>

      <p className="whitespace-pre-wrap text-sm text-text-primary">
        {question.question_text}
      </p>

      {question.options?.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1">
          {question.options.map((option, i) => (
            <li key={i} className="font-mono text-sm text-text-secondary">
              {option}
            </li>
          ))}
        </ul>
      )}

      {question.requires_diagram && <DiagramNotice description={question.diagram_description} />}

      <button
        type="button"
        onClick={() => setRevealed(!revealed)}
        aria-expanded={revealed}
        className="mt-3 text-xs text-text-secondary underline transition-colors hover:text-accent"
      >
        {revealed ? "Hide answer" : "Show answer"}
      </button>

      {revealed && (
        <div className="mt-3 border-t border-border pt-3">
          <p className="text-sm">
            <span className="text-text-secondary">Answer: </span>
            <span className="whitespace-pre-wrap text-text-primary">{question.answer}</span>
          </p>
          <p className="mt-2 text-sm">
            <span className="text-text-secondary">Mark scheme: </span>
            <span className="whitespace-pre-wrap text-text-primary">
              {question.mark_scheme}
            </span>
          </p>
          {question.misconception_targeted && (
            <p className="mt-2 text-xs text-tier-reasoning">
              Diagnoses: {question.misconception_targeted}
            </p>
          )}
        </div>
      )}
    </article>
  );
}
