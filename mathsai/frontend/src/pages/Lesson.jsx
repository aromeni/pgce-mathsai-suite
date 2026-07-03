import { Link, useParams } from "react-router-dom";

/** Lesson view — full UI implemented in Phase 5 (CLAUDE.md Lesson Page). */
export default function Lesson() {
  const { topicId } = useParams();

  return (
    <div className="p-8">
      <Link to="/" className="text-sm text-accent hover:underline">
        &larr; Back to Dashboard
      </Link>
      <p className="mt-4 text-text-secondary">
        Lesson view for topic {topicId} — coming in Phase 5.
      </p>
    </div>
  );
}
