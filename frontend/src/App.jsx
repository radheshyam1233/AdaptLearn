// src/App.jsx
// The navigation bar and the list of pages (routes).

import { Link, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Practice from "./pages/Practice.jsx";
import Progress from "./pages/Progress.jsx";
import TutorDashboard from "./pages/TutorDashboard.jsx";

// Shows the page only to logged-in users with the right role.
// (The backend checks roles too: this only decides what to display.)
function Protected({ role, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return children;
}

// "/" sends each user to their own home page
function Home() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "tutor" ? "/tutor" : "/practice"} replace />;
}

export default function App() {
  const { user, logout } = useAuth();
  return (
    <>
      <header className="nav">
        <Link to="/" className="brand">AdaptLearn</Link>
        {user?.role === "student" && (
          <nav>
            <Link to="/practice">Practice</Link>
            <Link to="/progress">My progress</Link>
          </nav>
        )}
        {user?.role === "tutor" && <nav><Link to="/tutor">Live dashboard</Link></nav>}
        {user && (
          <div className="nav-user">
            <span>{user.name}</span>
            <button className="link" onClick={logout}>Log out</button>
          </div>
        )}
      </header>

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/practice" element={<Protected role="student"><Practice /></Protected>} />
          <Route path="/progress" element={<Protected role="student"><Progress /></Protected>} />
          <Route path="/tutor" element={<Protected role="tutor"><TutorDashboard /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
