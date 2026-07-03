import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { deleteProgress, getProgress, getTopics } from "../api/client";

/** Teaching history tracker (CLAUDE.md Progress Page). Backend API already
 * complete since Phase 3 — this builds the table + key stage/strand filters
 * on top of it. */
export default function Progress() {
  const [entries, setEntries] = useState([]);
  const [topicsById, setTopicsById] = useState(new Map());
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [keyStage, setKeyStage] = useState("All");
  const [strand, setStrand] = useState("All");

  const load = () => {
    setStatus("loading");
    Promise.all([getProgress(), getTopics()])
      .then(([progressData, topicsData]) => {
        setEntries(progressData);
        setTopicsById(new Map(topicsData.map((t) => [t.id, t])));
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  };

  useEffect(load, []);

  const rows = useMemo(
    () => entries.map((entry) => ({ ...entry, topic: topicsById.get(entry.topic_id) })),
    [entries, topicsById],
  );

  const keyStages = useMemo(
    () => [...new Set(rows.map((r) => r.topic?.key_stage).filter(Boolean))].sort(),
    [rows],
  );

  const strandsForKeyStage = useMemo(
    () => [
      ...new Set(
        rows
          .filter((r) => keyStage === "All" || r.topic?.key_stage === keyStage)
          .map((r) => r.topic?.strand)
          .filter(Boolean),
      ),
    ],
    [rows, keyStage],
  );

  const filteredRows = useMemo(
    () =>
      rows.filter((r) => {
        if (keyStage !== "All" && r.topic?.key_stage !== keyStage) return false;
        if (strand !== "All" && r.topic?.strand !== strand) return false;
        return true;
      }),
    [rows, keyStage, strand],
  );

  const handleKeyStageChange = (value) => {
    setKeyStage(value);
    setStrand("All"); // strand options depend on key stage — reset the filter
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Remove this teaching log entry?")) return;
    try {
      await deleteProgress(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch {
      window.alert("Couldn't delete this entry — please try again.");
    }
  };

  if (status === "loading") {
    return <p className="p-8 text-text-secondary">Loading progress…</p>;
  }

  if (status === "error") {
    return <p className="p-8 text-tier-extending">Couldn't load progress data.</p>;
  }

  return (
    <div className="mx-auto max-w-5xl p-6 md:p-8">
      <h1 className="mb-6 font-display text-2xl font-bold text-text-primary">Teaching Progress</h1>

      <div className="mb-6 flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm text-text-secondary">
          Key Stage
          <select
            value={keyStage}
            onChange={(e) => handleKeyStageChange(e.target.value)}
            className="rounded border border-border bg-surface px-2 py-1 text-text-primary"
          >
            <option>All</option>
            {keyStages.map((ks) => (
              <option key={ks}>{ks}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm text-text-secondary">
          Strand
          <select
            value={strand}
            onChange={(e) => setStrand(e.target.value)}
            className="rounded border border-border bg-surface px-2 py-1 text-text-primary"
          >
            <option>All</option>
            {strandsForKeyStage.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>

      {filteredRows.length === 0 ? (
        <p className="text-text-secondary">No topics logged as taught yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border bg-surface text-left text-text-secondary">
                <th className="px-4 py-3 font-display font-normal uppercase tracking-widest">Date</th>
                <th className="px-4 py-3 font-display font-normal uppercase tracking-widest">Topic</th>
                <th className="px-4 py-3 font-display font-normal uppercase tracking-widest">Key Stage</th>
                <th className="px-4 py-3 font-display font-normal uppercase tracking-widest">Strand</th>
                <th className="px-4 py-3 font-display font-normal uppercase tracking-widest">Class</th>
                <th className="px-4 py-3 font-display font-normal uppercase tracking-widest">Notes</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr key={row.id} className="border-b border-border/50 align-top">
                  <td className="px-4 py-3 text-text-primary">{row.taught_date}</td>
                  <td className="px-4 py-3">
                    {row.topic ? (
                      <Link
                        to={`/lesson/${row.topic.id}`}
                        className="text-accent hover:underline"
                      >
                        {row.topic.topic_name}
                      </Link>
                    ) : (
                      <span className="text-text-secondary">Topic {row.topic_id}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-text-secondary">{row.topic?.key_stage ?? "—"}</td>
                  <td className="px-4 py-3 text-text-secondary">{row.topic?.strand ?? "—"}</td>
                  <td className="px-4 py-3 text-text-secondary">{row.class_label ?? "—"}</td>
                  <td className="px-4 py-3 text-text-secondary">{row.notes ?? "—"}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDelete(row.id)}
                      className="text-xs text-tier-extending hover:underline"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
