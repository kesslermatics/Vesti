import { useState } from "react";
import { motion } from "framer-motion";
import { api, auth } from "../api";

export default function Auth({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isRegister = mode === "register";

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = isRegister
        ? await api.register({ email, password, name })
        : await api.login({ email, password });
      auth.set(res.access_token);
      onAuth(res.user);
    } catch (err) {
      setError(err.message || "Etwas ist schiefgelaufen.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center px-5 py-12">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-sm"
      >
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-ink-900">Vesti</h1>
          <p className="text-sm text-ink-700/60 mt-1">Deine digitale Garderobe</p>
        </div>

        <div className="bg-white rounded-3xl shadow-soft p-6">
          <div className="flex bg-sand-100 rounded-xl p-1 mb-6">
            {["login", "register"].map((m) => (
              <button
                key={m}
                onClick={() => {
                  setMode(m);
                  setError("");
                }}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                  mode === m ? "bg-white text-ink-900 shadow-sm" : "text-ink-700/60"
                }`}
              >
                {m === "login" ? "Anmelden" : "Registrieren"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            {isRegister && (
              <input
                type="text"
                placeholder="Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-sand-200 px-4 py-3 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
              />
            )}
            <input
              type="email"
              required
              placeholder="E-Mail"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-sand-200 px-4 py-3 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
            />
            <input
              type="password"
              required
              placeholder="Passwort"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-sand-200 px-4 py-3 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
            />

            {error && (
              <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60"
            >
              {loading ? "Bitte warten …" : isRegister ? "Konto erstellen" : "Anmelden"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-ink-700/40 mt-6">
          Deine Garderobe, privat und nur für dich.
        </p>
      </motion.div>
    </div>
  );
}
