// src/pages/Practice.jsx
// Pick a concept, answer a question, get feedback and a hint.

import { useEffect, useState } from "react";
import { request } from "../api";

const LETTERS = ["A", "B", "C", "D"];

export default function Practice() {
  const [concepts, setConcepts] = useState([]);
  const [concept, setConcept] = useState("");
  const [question, setQuestion] = useState(null);
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState(null);     // the API's answer after submitting
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Runs once when the page opens: load the list of concepts
  useEffect(() => {
    request("/questions/concepts").then(setConcepts).catch((e) => setError(e.message));
  }, []);

  async function loadQuestion(name) {
    setConcept(name);
    setSelected("");
    setResult(null);
    setError("");
    try {
      setQuestion(await request(`/questions/next?concept=${encodeURIComponent(name)}`));
    } catch (e) {
      setError(e.message);
    }
  }

  async function submit() {
    setBusy(true);
    setError("");
    try {
      setResult(await request("/attempts", {
        method: "POST",
        body: { question_id: question.id, selected },
      }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="practice">
      <aside className="card">
        <h2>Concepts</h2>
        {concepts.map((c) => (
          <button key={c.concept}
                  className={`concept ${c.concept === concept ? "active" : ""}`}
                  onClick={() => loadQuestion(c.concept)}>
            {c.concept} <span className="muted">{c.questions}</span>
          </button>
        ))}
      </aside>

      <section className="card">
        {error && <p className="error">{error}</p>}
        {!question && <p className="muted">Choose a concept to start practising.</p>}

        {question && (
          <>
            <p className="muted small">{question.concept} · difficulty {question.difficulty}/3</p>
            <h2>{question.text}</h2>
            <div className="options">
              {LETTERS.map((letter) => {
                // After submitting, colour the correct option green and a wrong pick red
                let state = "";
                if (result) {
                  const correct = result.correct_answer ?? selected;
                  if (letter === correct) state = "right";
                  else if (letter === selected) state = "wrong";
                }
                return (
                  <button key={letter}
                          className={`option ${selected === letter ? "chosen" : ""} ${state}`}
                          disabled={!!result}
                          onClick={() => setSelected(letter)}>
                    <b>{letter}</b> {question[`option_${letter.toLowerCase()}`]}
                  </button>
                );
              })}
            </div>

            {!result && <button disabled={!selected || busy} onClick={submit}>
              {busy ? "Checking..." : "Submit answer"}
            </button>}

            {result && (
              <div className={`result ${result.is_correct ? "ok" : "bad"}`}>
                <h3>{result.is_correct ? "Correct!" : `Not quite: the answer is ${result.correct_answer}`}</h3>
                {result.hint && (
                  <p><b>{result.hint_source === "ai" ? "AI hint" : "Hint"}:</b> {result.hint}</p>
                )}
                <p className="muted">Your gap score for {result.concept}: {result.gap_score} (0 = mastered, 1 = struggling)</p>
                <button onClick={() => loadQuestion(concept)}>Next question</button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
