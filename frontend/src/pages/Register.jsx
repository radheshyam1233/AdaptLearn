// src/pages/Register.jsx
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  // One handler for all three inputs: the input's "name" says which field to update
  const update = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register(form.name, form.email, form.password);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card auth" onSubmit={handleSubmit}>
      <h1>Create account</h1>
      <label>Name<input name="name" value={form.name} onChange={update} required minLength={2} /></label>
      <label>Email<input name="email" type="email" value={form.email} onChange={update} required /></label>
      <label>Password (8+ characters)
        <input name="password" type="password" value={form.password} onChange={update} required minLength={8} maxLength={72} />
      </label>
      {error && <p className="error">{error}</p>}
      <button disabled={busy}>{busy ? "Creating..." : "Create account"}</button>
      <p className="muted">Already have an account? <Link to="/login">Log in</Link></p>
    </form>
  );
}
