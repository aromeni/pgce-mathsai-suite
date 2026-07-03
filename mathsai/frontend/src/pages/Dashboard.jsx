import { useEffect, useMemo, useState } from "react";
import Sidebar from "../components/Sidebar";
import TopicCard from "../components/TopicCard";
import { getProgress, getTopics } from "../api/client";

/** Topic browser — main entry point (CLAUDE.md Dashboard Page). */
export default function Dashboard() {
  const [topics, setTopics] = useState([]);
  const [taughtTopicIds, setTaughtTopicIds] = useState(new Set());
  const [keyStage, setKeyStage] = useState("KS3");
  const [strand, setStrand] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error

  useEffect(() => {
    let cancelled = false;
    Promise.all([getTopics(), getProgress()])
      .then(([topicsData, progressData]) => {
        if (cancelled) return;
        setTopics(topicsData);
        setTaughtTopicIds(new Set(progressData.map((entry) => entry.topic_id)));
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const topicsForKeyStage = useMemo(
    () => topics.filter((t) => t.key_stage === keyStage),
    [topics, keyStage],
  );

  // Strand options are derived from loaded data, not hardcoded, since the
  // real taxonomy's strand names (e.g. "Geometry and Measures") don't match
  // CLAUDE.md's shorthand sidebar example ("Number, Algebra, Geometry...").
  const strands = useMemo(
    () => [...new Set(topicsForKeyStage.map((t) => t.strand))],
    [topicsForKeyStage],
  );

  const filteredTopics = useMemo(
    () => (strand ? topicsForKeyStage.filter((t) => t.strand === strand) : topicsForKeyStage),
    [topicsForKeyStage, strand],
  );

  const groupedByStrand = useMemo(() => {
    const groups = new Map();
    for (const topic of filteredTopics) {
      if (!groups.has(topic.strand)) groups.set(topic.strand, []);
      groups.get(topic.strand).push(topic);
    }
    return groups;
  }, [filteredTopics]);

  const handleKeyStageChange = (ks) => {
    setKeyStage(ks);
    setStrand(null); // strand options change per key stage — reset the filter
  };

  if (status === "loading") {
    return <p className="p-8 text-text-secondary">Loading curriculum…</p>;
  }

  if (status === "error") {
    return (
      <p className="p-8 text-tier-extending">
        Couldn't load topics. Is the backend running on port 8000?
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-8 p-6 md:flex-row md:p-8">
      <Sidebar
        keyStage={keyStage}
        onKeyStageChange={handleKeyStageChange}
        strand={strand}
        onStrandChange={setStrand}
        strands={strands}
      />

      <main className="flex-1">
        <h1 className="mb-6 font-display text-2xl font-bold text-text-primary">
          {keyStage} Topics
        </h1>

        {[...groupedByStrand.entries()].map(([strandName, strandTopics]) => (
          <section key={strandName} className="mb-8">
            <h2 className="mb-3 text-sm font-display uppercase tracking-widest text-text-secondary">
              {strandName}
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {strandTopics.map((topic) => (
                <TopicCard key={topic.id} topic={topic} taught={taughtTopicIds.has(topic.id)} />
              ))}
            </div>
          </section>
        ))}
      </main>
    </div>
  );
}
