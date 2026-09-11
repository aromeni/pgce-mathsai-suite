import ReactMarkdown from "react-markdown";

/**
 * Renders lessons cached under schema version 1 — flat markdown notes plus
 * worked examples, before the teaching sequence existed.
 *
 * Kept rather than dropped because those rows hold real, usable content that
 * cost money to generate. They are served as they are, with the page
 * offering regeneration; nothing is rewritten automatically.
 */
export default function LegacyLessonPanel({ lesson }) {
  return (
    <div className="flex flex-col gap-8">
      <article className="prose-invert max-w-none font-mono text-sm leading-relaxed text-text-primary [&_h1]:font-display [&_h1]:text-xl [&_h2]:font-display [&_h2]:text-lg [&_h2]:mt-6 [&_h3]:font-display [&_h3]:text-base [&_li]:my-1 [&_p]:my-3 [&_strong]:text-accent">
        <ReactMarkdown>{lesson.lesson_notes ?? ""}</ReactMarkdown>
      </article>

      {(lesson.worked_examples ?? []).length > 0 && (
        <section>
          <h3 className="mb-3 font-display text-sm uppercase tracking-widest text-text-secondary">
            Worked examples
          </h3>
          <div className="flex flex-col gap-4">
            {lesson.worked_examples.map((example, i) => (
              <div key={i} className="rounded-lg border border-border bg-surface p-4">
                <h4 className="mb-2 font-display text-sm font-semibold text-accent">
                  {example.title}
                </h4>
                <p className="mb-2 whitespace-pre-wrap font-mono text-sm text-text-primary">
                  <span className="text-text-secondary">Problem: </span>
                  {example.problem}
                </p>
                <p className="mb-2 whitespace-pre-wrap font-mono text-sm text-text-primary">
                  <span className="text-text-secondary">Solution: </span>
                  {example.solution}
                </p>
                <p className="whitespace-pre-wrap font-mono text-xs text-text-secondary">
                  Teaching note: {example.teaching_note}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
