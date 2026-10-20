// src/pages/Progress.jsx
// The student's gap score per concept, weakest first.

import { useEffect, useState } from "react";
import { request } from "../api";

// Same thresholds as the backend: 0.7+ = struggling
function level(score) {
  if (score >= 0.7) return "high";
  if (score >= 0.4) return "mid";
  return "low";
}

export default function Progress() {
  const [gaps, setGaps] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    request("/analytics/me/gaps").then(setGaps).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!gaps) return <p className="muted">Loading...</p>;

  return (
    <section className="card">
      <h1>My progress</h1>
      <p className="muted">Gap score per concept: 0 = mastered, 1 = struggling. Practise the top ones first.</p>
      {gaps.length === 0 && <p>No attempts yet. Go to Practice to start.</p>}
      {gaps.map((g) => (
        <div key={g.concept} className="gap-row">
          <span className="gap-name">{g.concept}</span>
          <div className="bar"><div className={`fill ${level(g.score)}`} style={{ width: `${g.score * 100}%` }} /></div>
          <span className="gap-num">{g.score.toFixed(2)}</span>
          <span className="muted small">{g.correct}/{g.attempts} correct</span>
        </div>
      ))}
    </section>
  );
}
