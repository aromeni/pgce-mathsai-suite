import { Link, useParams } from "react-router-dom";

/** Question display by difficulty tier — full UI implemented in Phase 5
 * (CLAUDE.md Questions Page). */
export default function Questions() {
  const { topicId, difficulty } = useParams();

  return (
    <div className="p-8">
      <Link to="/" className="text-sm text-accent hover:underline">
        &larr; Back to Dashboard
      </Link>
      <p className="mt-4 text-text-secondary">
        {difficulty} questions for topic {topicId} — coming in Phase 5.
      </p>
    </div>
  );
}
