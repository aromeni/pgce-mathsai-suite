import ReactMarkdown from "react-markdown";

function NotesTab({ lesson }) {
  return (
    <div className="flex flex-col gap-8">
      <article className="prose-invert max-w-none font-mono text-sm leading-relaxed text-text-primary [&_h1]:font-display [&_h1]:text-xl [&_h2]:font-display [&_h2]:text-lg [&_h2]:mt-6 [&_h3]:font-display [&_h3]:text-base [&_li]:my-1 [&_p]:my-3 [&_strong]:text-accent">
        <ReactMarkdown>{lesson.lesson_notes}</ReactMarkdown>
      </article>

      {lesson.worked_examples.length > 0 && (
        <section>
          <h3 className="mb-3 font-display text-sm uppercase tracking-widest text-text-secondary">
            Worked Examples
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

function VocabularyTab({ lesson }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-border text-left text-text-secondary">
          <th className="py-2 pr-4 font-display font-normal uppercase tracking-widest">Term</th>
          <th className="py-2 font-display font-normal uppercase tracking-widest">Definition</th>
        </tr>
      </thead>
      <tbody>
        {lesson.key_vocabulary.map((item, i) => (
          <tr key={i} className="border-b border-border/50 align-top">
            <td className="py-3 pr-4 font-semibold text-accent">{item.term}</td>
            <td className="py-3 text-text-primary">{item.definition}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ErrorsTab({ lesson }) {
  return (
    <div className="flex flex-col gap-4">
      {lesson.common_errors.map((item, i) => (
        <div
          key={i}
          className="rounded-lg border border-tier-extending/30 bg-tier-extending/5 p-4"
        >
          <p className="mb-2 text-sm">
            <span className="font-display font-semibold text-tier-extending">Misconception: </span>
            <span className="text-text-primary">{item.error}</span>
          </p>
          <p className="text-sm">
            <span className="font-display font-semibold text-tier-foundation">Correction: </span>
            <span className="text-text-primary">{item.correction}</span>
          </p>
        </div>
      ))}
    </div>
  );
}

/** Lesson notes / worked examples / vocabulary / common errors panel
 * (CLAUDE.md Lesson Page — Tab 1/2/3 content). */
export default function LessonPanel({ lesson, tab }) {
  if (tab === "vocabulary") return <VocabularyTab lesson={lesson} />;
  if (tab === "errors") return <ErrorsTab lesson={lesson} />;
  return <NotesTab lesson={lesson} />;
}
