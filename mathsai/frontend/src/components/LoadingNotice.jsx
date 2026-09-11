import { useEffect, useState } from "react";

/**
 * Loading text that explains itself once the wait runs long.
 *
 * First view of a topic generates content through Claude, which takes
 * 30-45s; a cached view returns in milliseconds. The page can't know which
 * it will be until the request returns, so the explanation is held back
 * until the wait is long enough to warrant it — otherwise every cached load
 * would flash a "this takes a while" message that isn't true for it.
 */
export default function LoadingNotice({ label }) {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 3000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="p-8">
      <p className="text-text-secondary" role="status" aria-live="polite">
        {label}
      </p>
      {slow && (
        <p className="mt-3 max-w-prose text-sm text-text-secondary">
          Generating this for the first time — usually 30–45 seconds. It's
          cached afterwards, so a topic only does this once.
        </p>
      )}
    </div>
  );
}
