import { Link } from "react-router-dom";

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M16.704 5.29a1 1 0 010 1.415l-7.5 7.5a1 1 0 01-1.414 0l-3.5-3.5a1 1 0 111.414-1.414L8.5 12.086l6.79-6.796a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function BoltIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
      <path d="M11.983 1.907a.75.75 0 00-1.292-.657L4.204 9.5a.75.75 0 00.546 1.25h4.033l-1.766 6.343a.75.75 0 001.292.657l6.487-8.25a.75.75 0 00-.546-1.25h-4.033l1.766-6.343z" />
    </svg>
  );
}

/**
 * A single topic in the Dashboard grid. Clicking navigates to the Lesson
 * page for that topic (CLAUDE.md Dashboard spec).
 */
export default function TopicCard({ topic, taught }) {
  return (
    <Link
      to={`/lesson/${topic.id}`}
      className="group flex flex-col gap-3 rounded-lg border border-border bg-surface p-4 transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-lg hover:shadow-black/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="rounded border border-border px-2 py-0.5 text-xs font-medium tracking-wide text-text-secondary">
          {topic.key_stage}
        </span>
        <div className="flex items-center gap-2 text-text-secondary">
          {taught && (
            <span title="Taught" className="text-tier-foundation">
              <CheckIcon />
            </span>
          )}
          {topic.has_cached_lesson && (
            <span title="Lesson cached" className="text-blue-400">
              <BoltIcon />
            </span>
          )}
        </div>
      </div>

      <h3 className="font-display text-base font-semibold leading-snug text-text-primary">
        {topic.topic_name}
      </h3>

      <p className="text-xs text-text-secondary">{topic.strand}</p>
    </Link>
  );
}
