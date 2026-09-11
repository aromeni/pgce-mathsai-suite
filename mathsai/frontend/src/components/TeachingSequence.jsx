import DiagramNotice from "./DiagramNotice.jsx";
import DifficultyBadge from "./DifficultyBadge.jsx";
import PhaseSection from "./PhaseSection.jsx";

const CARD = "rounded-lg border border-border bg-surface p-4";
const LABEL = "font-display text-xs uppercase tracking-widest text-text-secondary";

function Introduction({ intro }) {
  return (
    <div className="flex flex-col gap-4 text-sm">
      <p className="text-text-primary">{intro.what_it_is}</p>
      <p className="text-text-secondary">{intro.why_it_matters}</p>
      <div className="grid gap-4 md:grid-cols-2">
        <div className={CARD}>
          <p className={LABEL}>Objectives</p>
          <ul className="mt-2 list-disc pl-4 text-text-primary">
            {intro.learning_objectives.map((o, i) => (
              <li key={i} className="my-1">{o}</li>
            ))}
          </ul>
        </div>
        <div className={CARD}>
          <p className={LABEL}>Success criteria</p>
          <ul className="mt-2 list-disc pl-4 text-text-primary">
            {intro.success_criteria.map((c, i) => (
              <li key={i} className="my-1">{c}</li>
            ))}
          </ul>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <p className="text-xs text-text-secondary">
          <span className="text-text-primary">Assumes: </span>
          {intro.prior_knowledge_needed.join(" · ")}
        </p>
        <p className="text-xs text-text-secondary">
          <span className="text-text-primary">Leads to: </span>
          {intro.leads_on_to.join(" · ")}
        </p>
      </div>
    </div>
  );
}

function Starter({ starter }) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-text-secondary">{starter.retrieval_focus}</p>
      <div className="flex flex-col gap-2">
        {starter.questions.map((q, i) => (
          <div key={i} className={`${CARD} flex flex-wrap items-start gap-3`}>
            <span className="flex-1 text-sm text-text-primary">{q.question}</span>
            <DifficultyBadge tier={q.tier} />
            <details className="w-full text-xs">
              <summary className="cursor-pointer text-text-secondary">Answer</summary>
              <p className="mt-1 text-text-primary">{q.answer}</p>
              <p className="mt-1 text-text-secondary">Retrieves: {q.prerequisite}</p>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModelledExample({ example }) {
  return (
    <div className={CARD}>
      <h4 className="font-display text-sm font-semibold text-accent">{example.title}</h4>
      <p className="mt-1 font-mono text-sm text-text-primary">{example.problem}</p>

      {/* Board on the left, script on the right. The split is the whole point:
          narrating the reasoning is what separates modelling from
          demonstrating, so the words you say get equal billing. */}
      <ol className="mt-4 flex flex-col gap-3">
        {example.steps.map((step, i) => (
          <li key={i} className="grid gap-2 md:grid-cols-2">
            <div className="rounded border border-border/60 bg-background px-3 py-2">
              <p className={LABEL}>Board {i + 1}</p>
              <p className="mt-1 whitespace-pre-wrap font-mono text-sm text-text-primary">
                {step.working}
              </p>
            </div>
            <div className="px-3 py-2">
              <p className={LABEL}>Say</p>
              <p className="mt-1 text-sm leading-relaxed text-text-secondary">
                {step.narration}
              </p>
            </div>
          </li>
        ))}
      </ol>

      <p className="mt-3 border-t border-border pt-3 text-sm text-text-primary">
        <span className="text-accent">Key point: </span>
        {example.key_teaching_point}
      </p>
      {example.requires_diagram && <DiagramNotice description={example.diagram_description} />}
    </div>
  );
}

function GuidedExample({ example }) {
  return (
    <div className={CARD}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="font-display text-sm font-semibold text-accent">{example.title}</h4>
        <span className="text-xs text-text-secondary">
          Support stops at step {example.faded_from_step}
        </span>
      </div>
      <p className="mt-1 font-mono text-sm text-text-primary">{example.problem}</p>

      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded border border-border/60 bg-background px-3 py-2 font-mono text-sm text-text-primary">
        {example.scaffolded_working}
      </pre>

      <p className={`mt-3 ${LABEL}`}>Ask the class</p>
      <ul className="mt-1 list-disc pl-4 text-sm text-text-secondary">
        {example.questions_to_ask.map((q, i) => (
          <li key={i} className="my-1">{q}</li>
        ))}
      </ul>

      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-text-secondary">Full solution</summary>
        <pre className="mt-1 overflow-x-auto whitespace-pre-wrap font-mono text-text-primary">
          {example.full_answer}
        </pre>
      </details>
      {example.requires_diagram && <DiagramNotice description={example.diagram_description} />}
    </div>
  );
}

/** The lesson in teaching order: introduction, starter, I do, We do, plenary. */
export default function TeachingSequence({ lesson, onGoToQuestions }) {
  return (
    <div className="flex flex-col gap-6">
      <PhaseSection label="Introduce" subtitle="What, why, and where it fits">
        <Introduction intro={lesson.topic_introduction} />
      </PhaseSection>

      <PhaseSection label="Starter" subtitle="Retrieval — prerequisites, not today's topic">
        <Starter starter={lesson.starter} />
      </PhaseSection>

      <PhaseSection label="I do" subtitle="Modelled — you work, they watch">
        <div className="flex flex-col gap-4">
          {lesson.i_do.map((e, i) => (
            <ModelledExample key={i} example={e} />
          ))}
        </div>
      </PhaseSection>

      <PhaseSection label="We do" subtitle="Guided — support fades across the examples">
        <div className="flex flex-col gap-4">
          {lesson.we_do.map((e, i) => (
            <GuidedExample key={i} example={e} />
          ))}
        </div>
      </PhaseSection>

      <PhaseSection label="You do" subtitle="Independent practice">
        <p className="mb-3 text-sm text-text-secondary">
          Practice is tiered by Assessment Objective. Pick by what the class needs next.
        </p>
        <div className="flex flex-wrap gap-2">
          {["Fluency", "Reasoning", "Problem-solving"].map((tier) => (
            <button
              key={tier}
              type="button"
              onClick={() => onGoToQuestions(tier)}
              className="rounded-lg border border-border bg-surface px-4 py-2 text-sm text-text-primary transition-colors hover:border-accent hover:text-accent"
            >
              {tier} questions
            </button>
          ))}
        </div>
      </PhaseSection>

      <PhaseSection label="Plenary" subtitle="Exit ticket" defaultOpen={false}>
        <div className="flex flex-col gap-2">
          {lesson.plenary.map((q, i) => (
            <div key={i} className={CARD}>
              <p className="text-sm text-text-primary">{q.question}</p>
              <details className="mt-2 text-xs">
                <summary className="cursor-pointer text-text-secondary">Answer</summary>
                <p className="mt-1 text-text-primary">{q.answer}</p>
                <p className="mt-1 text-text-secondary">Checks: {q.checks}</p>
              </details>
            </div>
          ))}
        </div>
      </PhaseSection>
    </div>
  );
}
