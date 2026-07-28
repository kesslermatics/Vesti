import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";

export default function Profile({ user, onUpdated }) {
  const [fields, setFields] = useState(null);
  const [name, setName] = useState(user.name || "");
  const [measurements, setMeasurements] = useState(user.measurements || {});
  const [sizes, setSizes] = useState(user.sizes || {});
  const [fitPreference, setFitPreference] = useState(user.fit_preference || "");
  const [bodyType, setBodyType] = useState(user.body_type || "");
  const [styleNotes, setStyleNotes] = useState(user.style_notes || "");
  const [openHelp, setOpenHelp] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getProfileFields().then(setFields).catch((e) => setError(e.message));
  }, []);

  // Messfelder nach Gruppe bündeln
  const grouped = useMemo(() => {
    if (!fields) return [];
    const map = new Map();
    for (const f of fields.measurements) {
      if (!map.has(f.group)) map.set(f.group, []);
      map.get(f.group).push(f);
    }
    return [...map.entries()].map(([group, items]) => ({ group, items }));
  }, [fields]);

  const filledCount = useMemo(
    () => Object.values(measurements).filter((v) => v !== "" && v != null).length,
    [measurements]
  );
  const totalCount = fields?.measurements.length || 0;

  async function save() {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      // Leere Werte rauswerfen, Zahlen konvertieren
      const cleanM = {};
      for (const [k, v] of Object.entries(measurements)) {
        if (v !== "" && v != null) {
          const num = Number(v);
          cleanM[k] = Number.isFinite(num) ? num : v;
        }
      }
      const cleanS = {};
      for (const [k, v] of Object.entries(sizes)) {
        if (v !== "" && v != null) cleanS[k] = v;
      }

      const updated = await api.updateProfile({
        name,
        measurements: cleanM,
        sizes: cleanS,
        fit_preference: fitPreference,
        body_type: bodyType,
        style_notes: styleNotes,
      });
      onUpdated(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(err.message || "Speichern fehlgeschlagen.");
    } finally {
      setSaving(false);
    }
  }

  if (!fields) {
    return (
      <div className="flex justify-center py-20">
        <motion.span
          className="inline-block w-6 h-6 border-2 border-clay-500 border-t-transparent rounded-full"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
        />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {error && (
        <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3">{error}</div>
      )}

      {/* Fortschritt */}
      <div className="bg-white rounded-2xl shadow-soft p-5">
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="text-sm font-semibold text-ink-900 uppercase tracking-wide">
            Dein Profil
          </h2>
          <span className="text-xs text-ink-700/50">
            {filledCount}/{totalCount} Maße
          </span>
        </div>
        <div className="h-1.5 bg-sand-100 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-clay-500"
            animate={{ width: `${totalCount ? (filledCount / totalCount) * 100 : 0}%` }}
            transition={{ type: "spring", stiffness: 200, damping: 30 }}
          />
        </div>
        <p className="text-xs text-ink-700/50 mt-3">
          Je vollständiger dein Profil, desto präziser die Empfehlungen beim Shopping.
        </p>
      </div>

      {/* Name */}
      <section className="bg-white rounded-2xl shadow-soft p-5 space-y-3">
        <h3 className="text-sm font-semibold text-ink-900">Name</h3>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Dein Name"
          className="w-full rounded-xl border border-sand-200 px-4 py-2.5 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
        />
      </section>

      {/* Körpermaße mit Anleitung */}
      {grouped.map((grp) => (
        <section key={grp.group} className="bg-white rounded-2xl shadow-soft p-5">
          <h3 className="text-sm font-semibold text-ink-900 mb-4">{grp.group}</h3>
          <div className="space-y-3">
            {grp.items.map((f) => (
              <div key={f.key}>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm text-ink-800">{f.label}</label>
                  <button
                    onClick={() => setOpenHelp(openHelp === f.key ? null : f.key)}
                    aria-label={`Anleitung für ${f.label}`}
                    className={`shrink-0 w-5 h-5 rounded-full text-xs font-medium transition ${
                      openHelp === f.key
                        ? "bg-clay-500 text-white"
                        : "bg-sand-100 text-ink-700/60 hover:bg-sand-200"
                    }`}
                  >
                    ?
                  </button>
                </div>
                <div className="mt-1.5 relative">
                  <input
                    type="number"
                    inputMode="decimal"
                    value={measurements[f.key] ?? ""}
                    onChange={(e) =>
                      setMeasurements((m) => ({ ...m, [f.key]: e.target.value }))
                    }
                    placeholder="–"
                    className="w-full rounded-xl border border-sand-200 px-4 py-2.5 pr-12 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-ink-700/40">
                    {f.unit}
                  </span>
                </div>

                <AnimatePresence>
                  {openHelp === f.key && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-2 rounded-xl bg-sand-100 p-3 space-y-2">
                        <p className="text-xs text-ink-800 leading-relaxed">
                          <span className="font-medium">So misst du: </span>
                          {f.how}
                        </p>
                        {f.tip && (
                          <p className="text-xs text-clay-600 leading-relaxed">
                            <span className="font-medium">Tipp: </span>
                            {f.tip}
                          </p>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </section>
      ))}

      {/* Konfektionsgrößen */}
      <section className="bg-white rounded-2xl shadow-soft p-5">
        <h3 className="text-sm font-semibold text-ink-900 mb-4">Konfektionsgrößen</h3>
        <div className="grid grid-cols-2 gap-3">
          {fields.sizes.map((f) => (
            <label key={f.key} className="block">
              <span className="text-xs font-medium text-ink-700/70">{f.label}</span>
              {f.options ? (
                <select
                  value={sizes[f.key] ?? ""}
                  onChange={(e) => setSizes((s) => ({ ...s, [f.key]: e.target.value }))}
                  className="mt-1 w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
                >
                  <option value="">–</option>
                  {f.options.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={sizes[f.key] ?? ""}
                  onChange={(e) => setSizes((s) => ({ ...s, [f.key]: e.target.value }))}
                  placeholder={f.placeholder || ""}
                  className="mt-1 w-full rounded-xl border border-sand-200 px-3 py-2.5 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
                />
              )}
            </label>
          ))}
        </div>
      </section>

      {/* Vorlieben */}
      <section className="bg-white rounded-2xl shadow-soft p-5 space-y-4">
        <h3 className="text-sm font-semibold text-ink-900">Vorlieben</h3>

        <div>
          <span className="text-xs font-medium text-ink-700/70">Bevorzugte Passform</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {fields.fit_preferences.map((p) => (
              <button
                key={p}
                onClick={() => setFitPreference(fitPreference === p ? "" : p)}
                className={`px-3 py-1.5 rounded-full text-sm transition ${
                  fitPreference === p
                    ? "bg-clay-500 text-white"
                    : "bg-sand-100 text-ink-700 hover:bg-sand-200"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div>
          <span className="text-xs font-medium text-ink-700/70">Körpertyp</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {fields.body_types.map((b) => (
              <button
                key={b}
                onClick={() => setBodyType(bodyType === b ? "" : b)}
                className={`px-3 py-1.5 rounded-full text-sm transition ${
                  bodyType === b
                    ? "bg-clay-500 text-white"
                    : "bg-sand-100 text-ink-700 hover:bg-sand-200"
                }`}
              >
                {b}
              </button>
            ))}
          </div>
        </div>

        <label className="block">
          <span className="text-xs font-medium text-ink-700/70">Stil-Notizen</span>
          <textarea
            value={styleNotes}
            onChange={(e) => setStyleNotes(e.target.value)}
            rows={3}
            placeholder="z.B. Ich mag gedeckte Farben, trage kein Pink, bevorzuge Naturmaterialien"
            className="mt-1 w-full rounded-xl border border-sand-200 px-4 py-2.5 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition resize-none"
          />
        </label>
      </section>

      {/* Speichern */}
      <button
        onClick={save}
        disabled={saving}
        className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60"
      >
        {saving ? "Speichern …" : saved ? "✓ Gespeichert" : "Profil speichern"}
      </button>
    </motion.div>
  );
}
