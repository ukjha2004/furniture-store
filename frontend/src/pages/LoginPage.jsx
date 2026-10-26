import { useState } from "react";

// One page with two modes: "login" and "signup".
export default function LoginPage({ auth, onDone }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (key) => (e) => {
    setForm({ ...form, [key]: e.target.value });
    if (error) setError("");
  };

  const submit = async (e) => {
    e.preventDefault(); // stop the browser reloading the page
    setError("");
    if (mode === "signup" && form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "login") await auth.login(form.email, form.password);
      else await auth.signup(form.name, form.email, form.password);
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const switchMode = () => {
    setMode(mode === "login" ? "signup" : "login");
    setError("");
  };

  return (
    <main className="narrow">
      <form className="panel" onSubmit={submit}>
        <h2>{mode === "login" ? "Log in" : "Create an account"}</h2>

        {mode === "signup" && (
          <label>
            Name
            <input value={form.name} onChange={update("name")} autoComplete="name" required minLength={2} />
          </label>
        )}
        <label>
          Email
          <input type="email" value={form.email} onChange={update("email")} autoComplete="email" required />
        </label>
        <label>
          Password
          <input
            type="password"
            value={form.password}
            onChange={update("password")}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
          />
          {mode === "signup" && <small className="muted">At least 8 characters</small>}
        </label>

        {error && <p className="error">{error}</p>}

        <button className="primary wide" type="submit" disabled={busy}>
          {busy ? "Please wait…" : mode === "login" ? "Log in" : "Sign up"}
        </button>

        <p className="muted center">
          {mode === "login" ? "New here?" : "Already have an account?"}{" "}
          <button type="button" className="link" onClick={switchMode}>
            {mode === "login" ? "Create an account" : "Log in"}
          </button>
        </p>
      </form>
    </main>
  );
}
