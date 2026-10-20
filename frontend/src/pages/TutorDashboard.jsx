// src/pages/TutorDashboard.jsx
// Live class overview: stats, concept heatmap, at-risk students, live feed.

import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../api";
import { useLiveFeed } from "../useLiveFeed";

// Error rate -> colour band for the heatmap
function heat(errorRate) {
  if (errorRate >= 60) return "high";
  if (errorRate >= 35) return "mid";
  return "low";
}

export default function TutorDashboard() {
  const [stats, setStats] = useState(null);
  const [concepts, setConcepts] = useState([]);
  const [atRisk, setAtRisk] = useState([]);
  const [error, setError] = useState("");
  const refreshTimer = useRef(null);

  // Load all three panels in parallel
  const refresh = useCallback(async () => {
    try {
      const [s, c, r] = await Promise.all([
        request("/analytics/dashboard"),
        request("/analytics/concepts"),
        request("/analytics/at-risk"),
      ]);
      setStats(s);
      setConcepts(c);
      setAtRisk(r);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // On each live event, refresh the panels. If many answers arrive at once,
  // wait 500 ms and refresh once ("debounce") instead of once per answer.
  const { events, connected } = useLiveFeed(() => {
    clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(refresh, 500);
  });

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p className="muted">Loading...</p>;

  return (
    <div className="dashboard">
      <div className="title-row">
        <h1>Live class dashboard</h1>
        <span className={`status ${connected ? "on" : "off"}`}>{connected ? "Live" : "Reconnecting..."}</span>
      </div>

      <div className="stats">
        <div className="stat"><b>{stats.active_students_24h}</b><span>of {stats.total_students} students active (24 h)</span></div>
        <div className="stat"><b>{stats.attempts_24h}</b><span>answers (24 h)</span></div>
        <div className="stat"><b>{stats.accuracy_24h}%</b><span>accuracy (24 h)</span></div>
        <div className="stat"><b>{stats.at_risk_students}</b><span>students at risk</span></div>
      </div>

      <div className="grid">
        <section className="card">
          <h2>Concept heatmap</h2>
          <p className="muted small">Error rate across all students. Red = reteach this.</p>
          <div className="heatmap">
            {concepts.map((c) => (
              <div key={c.concept} className={`tile ${heat(c.error_rate)}`}>
                <b>{c.concept}</b>
                <span>{c.error_rate}% wrong</span>
                <span className="small">{c.attempts} answers</span>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h2>At-risk students</h2>
          {atRisk.length === 0 && <p className="muted">Nobody above the 0.7 threshold.</p>}
          <ul className="list">
            {atRisk.map((s) => (
              <li key={`${s.student_id}-${s.concept}`}>
                <span>{s.name}</span>
                <span className="muted">{s.concept}</span>
                <b>{s.gap_score.toFixed(2)}</b>
              </li>
            ))}
          </ul>
        </section>

        <section className="card">
          <h2>Live feed</h2>
          {events.length === 0 && <p className="muted">Waiting for students to answer...</p>}
          <ul className="list feed">
            {events.map((e, i) => (
              <li key={`${e.at}-${i}`}>
                <span className={e.is_correct ? "dot ok" : "dot bad"} />
                <span>{e.student}</span>
                <span className="muted">{e.concept}</span>
                <span className="small">{new Date(e.at).toLocaleTimeString()}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
