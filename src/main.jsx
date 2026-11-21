import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity, BookOpen, Brain, ChartNoAxesCombined, Check, CircleHelp, Code2,
  Database, GraduationCap, LayoutDashboard, Lightbulb, LogIn, LogOut, RotateCcw,
  Sparkles, Target, X, Zap,
} from 'lucide-react';
import bank from '../questions.json';
import './style.css';

const topics = ['Python', 'SQL', 'Statistics', 'Logic'];
const topicIcons = { Python: Code2, SQL: Database, Statistics: ChartNoAxesCombined, Logic: Brain };
const letters = ['A', 'B', 'C', 'D'];
const key = 'adaptlearn-attempts-v1';

function readGuest() {
  try {
    const saved = JSON.parse(localStorage.getItem(key) || '[]');
    return Array.isArray(saved) ? saved.filter(row => row && topics.includes(row.topic)) : [];
  } catch {
    return [];
  }
}

async function api(path, data) {
  const options = data === undefined ? {} : {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  };
  const response = await fetch('/api/' + path, options);
  const result = await response.json();
  if (!response.ok) {
    throw new Error(typeof result.detail === 'string' ? result.detail : 'Check the information you entered and try again.');
  }
  return result;
}

function measure(rows, topic) {
  const attempts = rows.filter(row => row.topic === topic);
  const misses = attempts.filter(row => !row.correct).length;
  const gap = [...attempts].reverse().reduce((score, row) => score * .65 + Number(!row.correct) * .35, 0);
  return { topic, attempts: attempts.length, misses, gap };
}

function nextQuestion(questions, attempts, topic) {
  const group = topic === 'All topics' ? questions : questions.filter(q => q.topic === topic);
  const latest = new Map();
  for (const row of attempts) {
    if (!latest.has(row.question_id)) latest.set(row.question_id, row);
  }
  const metrics = Object.fromEntries(topics.map(name => [name, measure(attempts, name).gap]));
  const sorted = [...group].sort((a, b) => {
    const score = q => (latest.has(q.id) ? (latest.get(q.id).correct ? 0 : 1) : 2) + metrics[q.topic] / 2;
    return score(b) - score(a);
  });
  return sorted.find(q => q.id !== attempts[0]?.question_id) || sorted[0];
}

function Practice({ questions, attempts, record, isGuest, initialTopic }) {
  const [topic, setTopic] = useState(initialTopic);
  const [question, setQuestion] = useState(() => nextQuestion(questions, attempts, topic));
  const [choice, setChoice] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [submission, setSubmission] = useState(null);
  const today = attempts.filter(row => new Date(row.created_at).toDateString() === new Date().toDateString()).length;
  const accuracy = attempts.length ? Math.round(attempts.filter(row => row.correct).length * 100 / attempts.length) + '%' : '—';
  const focus = topics.map(name => measure(attempts, name)).sort((a, b) => b.gap - a.gap)[0];
  const TopicIcon = topicIcons[question.topic];

  function reset(selectedTopic, selectedQuestion) {
    setTopic(selectedTopic);
    setQuestion(selectedQuestion || nextQuestion(questions, attempts, selectedTopic));
    setChoice(null);
    setFeedback(null);
    setSubmission(null);
    setError('');
  }

  async function submit(event) {
    event.preventDefault();
    if (pending || choice === null || feedback) return;
    setPending(true);
    setError('');
    const id = submission || crypto.randomUUID();
    setSubmission(id);
    try {
      setFeedback(await record(question, choice, id));
    } catch (problem) {
      setError(problem.message);
    } finally {
      setPending(false);
    }
  }

  return <>
    <header className="page-heading">
      <div className="eyebrow"><span /> STUDENT WORKSPACE</div>
      <h1>Practice lab<span>.</span></h1>
      <p>Build confidence one concept at a time.</p>
    </header>
    <div className="topic-picker" aria-label="Practice topics">
      {['All topics', ...topics].map(name => {
        const Icon = topicIcons[name] || LayoutDashboard;
        return <button key={name} disabled={pending} className={topic === name ? 'selected' : ''} aria-pressed={topic === name} onClick={() => reset(name)}>
          <Icon size={16} />{name}
        </button>;
      })}
    </div>
    <div className="practice-grid">
      <form className="panel question" onSubmit={submit}>
        <div className="question-top">
          <span className="subject"><TopicIcon size={16} />{question.topic}</span>
          <span className="level">{question.level}</span>
        </div>
        <h2>{question.prompt}</h2>
        {question.code && <pre><code>{question.code}</code></pre>}
        <fieldset aria-label="Answer options">
          {question.options.map((option, index) => <label key={option} className={'answer' + (choice === index ? ' chosen' : '')}>
            <input type="radio" name="choice" checked={choice === index} disabled={pending || Boolean(feedback)} onChange={() => { setChoice(index); setSubmission(null); setError(''); }}/>
            <span className="letter">{letters[index]}</span><span>{option}</span>
            {choice === index && <Check size={17} className="choice-check" />}
          </label>)}
        </fieldset>
        {error && <p className="error" role="alert">{error}</p>}
        {feedback && <div className={'feedback ' + (feedback.correct ? 'right' : '')} aria-live="polite">
          {feedback.correct ? <Check size={19}/> : <Lightbulb size={19}/>}
          <div><strong>{feedback.correct ? 'Correct answer' : feedback.source}</strong><p>{feedback.hint}</p></div>
        </div>}
        <div className="question-actions">
          {feedback
            ? <button type="button" className="primary" onClick={() => reset(topic)}>Next question</button>
            : <button className="primary" type="submit" disabled={choice === null || pending}>{pending ? 'Checking…' : 'Check answer'}</button>}
          <button className="text-button" type="button" disabled={pending} onClick={() => reset(topic, question)}><RotateCcw size={16}/> Restart</button>
        </div>
      </form>
      <aside className="insights" aria-label="Practice insights">
        <section className="panel stats">
          <div className="section-heading"><div className="tile purple"><Activity size={19}/></div><h2>Your session</h2></div>
          <div className="stat"><span>Attempted today</span><strong>{today}</strong></div>
          <div className="stat"><span>Overall accuracy</span><strong>{accuracy}</strong></div>
          <div className="stat"><span>Topics explored</span><strong>{new Set(attempts.map(row => row.topic)).size}<small> / {topics.length}</small></strong></div>
        </section>
        <section className="panel focus">
          <div className="section-heading"><div className="tile amber"><Target size={19}/></div><h2>Focus next</h2></div>
          {focus.gap > 0 ? <>
            <p>Recent mistakes suggest practising <strong>{focus.topic}</strong>.</p>
            <button className="text-button" disabled={pending} onClick={() => reset(focus.topic)}>Practise {focus.topic}</button>
          </> : <p>Answer a few questions to get a practice recommendation.</p>}
        </section>
        <section className="tip"><Sparkles size={18}/><div><strong>Learn from the miss.</strong><p>Read the feedback before moving to the next question.</p></div></section>
        {isGuest && <div className="guest-note">Guest progress is saved in this browser.</div>}
      </aside>
    </div>
  </>;
}

function StudentDashboard({ name, attempts, onPractice, onProgress }) {
  const metrics = topics.map(topic => measure(attempts, topic));
  const focus = metrics.reduce((priority, topic) => topic.gap > priority.gap ? topic : priority);
  const accuracy = attempts.length
    ? Math.round(attempts.filter(row => row.correct).length * 100 / attempts.length) + '%'
    : '—';
  const latestMiss = attempts.find(row => !row.correct);
  const stats = [
    ['Attempts', attempts.length],
    ['Accuracy', accuracy],
    ['Topics explored', metrics.filter(topic => topic.attempts).length + ' / ' + topics.length],
  ];

  return <>
    <header className="page-heading">
      <div className="eyebrow"><span/> STUDENT WORKSPACE</div>
      <h1>Student dashboard<span>.</span></h1>
      <p>{name ? 'Welcome back, ' + name + '.' : 'Try a question to start tracking your progress.'}</p>
    </header>
    <div className="dashboard-stats" aria-label="Your practice totals">
      {stats.map(([label, value]) => <div className="panel" key={label}><span>{label}</span><strong>{value}</strong></div>)}
    </div>
    <div className="practice-grid">
      <section className="panel dashboard-card student-card">
        <div className="section-heading"><div className="tile purple"><Target size={19}/></div><h2>Recommended practice</h2></div>
        <p className="muted">{focus.gap > 0
          ? 'Your recent attempts suggest another round of ' + focus.topic + '.'
          : 'Practise any topic to see what to review next.'}</p>
        <div className="question-actions">
          <button className="primary" onClick={() => onPractice(focus.gap > 0 ? focus.topic : 'All topics')}>
            {focus.gap > 0 ? 'Practise ' + focus.topic : 'Start practice'}
          </button>
          <button className="text-button" onClick={onProgress}>View progress</button>
        </div>
        {latestMiss && <div className="feedback">
          <Lightbulb size={19}/><div><strong>Recent feedback · {latestMiss.topic}</strong><p>{latestMiss.hint}</p></div>
        </div>}
      </section>
      <section className="panel dashboard-card student-card">
        <div className="section-heading"><div className="tile purple"><Activity size={19}/></div><h2>Your recent attempts</h2></div>
        {attempts.length > 0
          ? <ul className="activity-list">{attempts.slice(0, 6).map((row, index) =>
              <li key={row.created_at + index}><strong>{row.topic}</strong><span className={row.correct ? 'good' : 'needs-work'}>{row.correct ? 'Correct' : 'Missed'}</span></li>)}</ul>
          : <p className="muted">Your answers will appear here.</p>}
      </section>
    </div>
  </>;
}

function Progress({ attempts }) {
  return <>
    <header className="page-heading"><div className="eyebrow"><span/> STUDENT WORKSPACE</div><h1>Your progress<span>.</span></h1><p>See which topics need another round of practice.</p></header>
    <div className="progress-grid">
      {topics.map(topic => {
        const { attempts: count, misses, gap } = measure(attempts, topic);
        const Icon = topicIcons[topic];
        const percent = Math.round(gap * 100);
        return <section className="panel progress-card" key={topic}>
          <div className="section-heading"><div className="tile purple"><Icon size={19}/></div><h2>{topic}</h2></div>
          <p>{count ? count - misses + ' correct of ' + count + ' attempts' : 'No attempts yet'}</p>
          <div className="progress-track" role="meter" aria-label={topic + ' review priority'} aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
            <span style={{ width: percent + '%' }}/>
          </div>
          <div className="measure-label">{count ? percent + '% review priority' : 'Review priority appears after practice'}</div>
        </section>;
      })}
    </div>
  </>;
}

function Tutor({ user, rows }) {
  const authenticated = user?.role === 'tutor';
  const [dashboard, setDashboard] = useState(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!authenticated) return;
    let socket;
    let alive = true;
    let timer;
    async function refresh() {
      try {
        const data = await api('dashboard');
        if (alive) { setDashboard(data); setError(''); }
      } catch (problem) {
        if (alive) setError(problem.message);
      }
    }
    function connect() {
      if (!alive) return;
      const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(scheme + '//' + location.host + '/api/live');
      socket.onopen = () => { if (alive) { setLive(true); refresh(); } };
      socket.onmessage = event => { if (JSON.parse(event.data).type === 'attempt') refresh(); };
      socket.onclose = () => {
        if (!alive) return;
        setLive(false);
        timer = setTimeout(connect, 3500);
      };
    }
    refresh();
    connect();
    return () => { alive = false; clearTimeout(timer); socket?.close(); };
  }, [authenticated]);

  const data = authenticated ? dashboard : {
    topics: topics.map(topic => measure(rows, topic)),
    recent: rows.slice(0, 10).map(row => ({ ...row, student: 'Guest learner' })),
    students: Number(rows.length > 0), attempts: rows.length, correct: rows.filter(row => row.correct).length,
    needs_review: topics.map(topic => measure(rows, topic)).filter(row => row.misses >= 2 && row.misses * 2 >= row.attempts).map(row => ({ ...row, student: 'Guest learner' })),
  };

  return <>
    <header className="page-heading"><div className="eyebrow"><span/> TUTOR WORKSPACE</div><h1>Tutor dashboard<span>.</span></h1>
      <p>{authenticated ? 'Classroom activity from the latest 1,000 submissions.' : 'Preview the tutor dashboard using this browser’s guest attempts.'}</p>
    </header>
    {authenticated && <p className="connection"><span className={live ? 'online' : ''}/>{live ? 'Live connection active' : 'Connecting to live activity…'}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {data && <>
      <div className="dashboard-stats">
        {[['Learners', data.students], ['Attempts', data.attempts], ['Accuracy', data.attempts ? Math.round(data.correct * 100 / data.attempts) + '%' : '—']].map(([label, value]) => <div className="panel" key={label}><span>{label}</span><strong>{value}</strong></div>)}
      </div>
      <div className="practice-grid tutor-grid">
        <section className="panel dashboard-card"><h2>Errors by concept</h2>
          {data.topics.map(({ topic, attempts, misses }) => <div className="heat-row" key={topic}>
            <div><strong>{topic}</strong><span>{attempts ? Math.round(misses * 100 / attempts) + '% missed' : 'No attempts'}</span></div>
            <div className="progress-track"><span style={{ width: (attempts ? misses * 100 / attempts : 0) + '%' }}/></div>
          </div>)}
          <h2 className="review-title">Needs review</h2>
          {data.needs_review.length > 0
            ? data.needs_review.map(row => <p className="review" key={row.student + row.topic}>{row.student} · {row.topic} · {row.misses}/{row.attempts} missed</p>)
            : <p className="muted">No learners meet the review threshold yet.</p>}
        </section>
        <section className="panel dashboard-card"><h2>Recent activity</h2>
          {data.recent.length > 0 ? <ul className="activity-list">
            {data.recent.map((row, index) => <li key={row.created_at + index}><div><strong>{row.student}</strong><span>{row.topic}</span></div><span className={row.correct ? 'good' : 'needs-work'}>{row.correct ? 'Correct' : 'Missed'}</span></li>)}
          </ul> : <p className="muted">Submitted answers will appear here.</p>}
        </section>
      </div>
    </>}
    {!data && !error && <p role="status">Loading classroom activity…</p>}
  </>;
}

function Login({ onClose, onSuccess }) {
  const [signup, setSignup] = useState(false);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setPending(true);
    setError('');
    try {
      const user = await api(signup ? 'register' : 'login', Object.fromEntries(new FormData(event.currentTarget)));
      await onSuccess(user);
    } catch (problem) {
      setError(problem.message);
    } finally {
      setPending(false);
    }
  }
  useEffect(() => {
    function close(event) { if (event.key === 'Escape') onClose(); }
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [onClose]);

  return <div className="modal-backdrop"><section className="panel modal" role="dialog" aria-modal="true" aria-labelledby="login-title">
    <div className="modal-top"><h2 id="login-title">{signup ? 'Create student account' : 'Sign in'}</h2><button type="button" className="icon-button" aria-label="Close" onClick={onClose}><X size={20}/></button></div>
    <form onSubmit={submit}>
      {signup && <label>Name<input name="name" autoComplete="name" minLength="2" maxLength="60" required autoFocus/></label>}
      <label>Email<input name="email" type="email" autoComplete="email" required autoFocus={!signup}/></label>
      <label>Password<input name="password" type="password" autoComplete={signup ? 'new-password' : 'current-password'} minLength="10" maxLength="128" required/></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary" disabled={pending}>{pending ? 'Please wait…' : signup ? 'Create account' : 'Sign in'}</button>
    </form>
    <button className="text-button" onClick={() => { setSignup(!signup); setError(''); }}>{signup ? 'Use an existing account' : 'Create a student account'}</button>
  </section></div>;
}

function App() {
  const [guest, setGuest] = useState(readGuest);
  const [rows, setRows] = useState([]);
  const [questions, setQuestions] = useState(bank);
  const [user, setUser] = useState(null);
  const [page, setPage] = useState('Student dashboard');
  const [practiceTopic, setPracticeTopic] = useState('All topics');
  const [accounts, setAccounts] = useState(false);
  const [login, setLogin] = useState(false);
  const [error, setError] = useState('');
  const isTutor = user?.role === 'tutor';
  const currentRows = user ? rows : guest;

  async function begin(user) {
    if (user.role === 'student') {
      const [items, attempts] = await Promise.all([api('questions'), api('attempts')]);
      setQuestions(items);
      setRows(attempts);
    }
    setUser(user);
    setPracticeTopic('All topics');
    setPage(user.role === 'tutor' ? 'Tutor dashboard' : 'Student dashboard');
    setLogin(false);
    setError('');
  }

  useEffect(() => {
    if (__SITES_PREVIEW__) return;
    api('status').then(data => setAccounts(data.accounts)).catch(() => {});
    api('me').then(begin).catch(() => {});
  }, []);

  useEffect(() => {
    try { localStorage.setItem(key, JSON.stringify(guest)); } catch { /* Storage may be unavailable. */ }
  }, [guest]);

  async function record(question, choice, submissionId) {
    if (user) {
      const row = await api('attempts', { question_id: question.id, choice, submission_id: submissionId });
      setRows(previous => [row, ...previous].slice(0, 500));
      return row;
    }
    const correct = question.correct === choice;
    const row = { question_id: question.id, topic: question.topic, choice, correct,
      hint: correct ? 'Good work. You applied the concept correctly.' : question.hints[choice],
      source: correct ? 'Feedback' : 'Concept hint', created_at: new Date().toISOString() };
    setGuest(previous => [row, ...previous].slice(0, 500));
    return row;
  }

  async function signOut() {
    try {
      await api('logout', {});
      setUser(null);
      setQuestions(bank);
      setRows([]);
      setPracticeTopic('All topics');
      setPage('Student dashboard');
    } catch (problem) {
      setError(problem.message);
    }
  }

  function openPractice(topic = 'All topics') {
    setPracticeTopic(topic);
    setPage('Practice');
  }

  const studentLinks = [['Student dashboard', LayoutDashboard], ['Practice', BookOpen], ['My progress', ChartNoAxesCombined]];
  const links = isTutor ? [['Tutor dashboard', LayoutDashboard]] : studentLinks;
  const navigation = user ? links : [...links, ['Tutor preview', GraduationCap]];

  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><span className="brand-icon"><GraduationCap size={24}/></span><div>AdaptLearn</div></div>
      <nav aria-label="Workspace">
        <div className="nav-label">WORKSPACE</div>
        {navigation.map(([label, Icon]) =>
          <button key={label} className={page === label ? 'active' : ''} aria-current={page === label ? 'page' : undefined} onClick={() => label === 'Practice' ? openPractice() : setPage(label)}>
            <Icon size={19}/><span>{label}</span>
          </button>
        )}
      </nav>
      <div className="sidebar-bottom">
        <div className="profile"><span className="avatar">{user ? user.name[0].toUpperCase() : <Zap size={16}/>}</span><div><strong>{user?.name || 'Guest learner'}</strong><small>{isTutor ? 'Tutor account' : user ? 'Student account' : 'Demo workspace'}</small></div></div>
      </div>
    </aside>
    <div className="workspace">
      <div className="topbar">
        <div className="breadcrumb">Workspace <span>/</span> <strong>{page}</strong></div>
        {user
          ? <button className="outline" onClick={signOut}><LogOut size={16}/> Sign out</button>
          : accounts
            ? <button className="outline" onClick={() => setLogin(true)}><LogIn size={16}/> Sign in</button>
            : <div className="demo"><CircleHelp size={16}/> Guest demo</div>}
      </div>
      <main className="content">
        {error && <p role="alert" className="error">{error}</p>}
        {!isTutor && page === 'Student dashboard' && <StudentDashboard name={user?.name} attempts={currentRows} onPractice={openPractice} onProgress={() => setPage('My progress')}/>}
        {!isTutor && page === 'Practice' && <Practice key={(user ? 'student-' : 'guest-') + practiceTopic} questions={questions} attempts={currentRows} record={record} isGuest={!user} initialTopic={practiceTopic}/>}
        {!isTutor && page === 'My progress' && <Progress attempts={currentRows}/>}
        {((isTutor && page === 'Tutor dashboard') || (!user && page === 'Tutor preview')) && <Tutor user={user} rows={guest}/>}
        <footer>AdaptLearn <span>·</span> Inspired by tutoring students at Chegg India <a href="https://github.com/radheshyam1233/AdaptLearn" target="_blank" rel="noreferrer" aria-label="AdaptLearn source on GitHub">GitHub</a></footer>
      </main>
    </div>
    {login && <Login onClose={() => setLogin(false)} onSuccess={begin}/>}
  </div>;
}

createRoot(document.getElementById('root')).render(<App/>);
