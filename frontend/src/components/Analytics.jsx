import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";
import { BarList, ColorBar, ScoreRing, SeasonRings, StatCard } from "./charts";

function Section({ title, hint, children }) {
  return (
    <section className="bg-white rounded-2xl shadow-soft p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-ink-900">{title}</h3>
        {hint && <p className="text-xs text-ink-700/50 mt-0.5">{hint}</p>}
      </div>
      {children}
    </section>
  );
}

export default function Analytics() {
  const [stats, setStats] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function loadInsights() {
    setAiLoading(true);
    setError("");
    try {
      setInsights(await api.getInsights());
    } catch (e) {
      setError(e.message || "Analyse fehlgeschlagen.");
    } finally {
      setAiLoading(false);
    }
  }

  if (loading) {
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

  if (stats?.empty) {
    return (
      <div className="text-center py-20">
        <div className="text-5xl mb-4">📊</div>
        <h2 className="text-lg font-semibold text-ink-900">Noch keine Daten</h2>
        <p className="text-sm text-ink-700/60 mt-1 max-w-xs mx-auto">
          Sobald du Kleidungsstücke erfasst hast, findest du hier die Auswertung deiner Garderobe.
        </p>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      {error && (
        <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3">{error}</div>
      )}

      {/* Kennzahlen */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Teile insgesamt" value={stats.total_pieces} sub={`${stats.total_entries} Einträge`} accent />
        <StatCard
          label="Outfit-Kombinationen"
          value={stats.combinations > 999 ? `${(stats.combinations / 1000).toFixed(1)}k` : stats.combinations}
          sub="Oberteil × Unterteil × Schuhe"
        />
        <StatCard label="Verschiedene Kategorien" value={stats.diversity.categories} />
        <StatCard label="Neue Teile (30 Tage)" value={stats.recent_30d} />
      </div>

      {/* Lücken & Empfehlungen */}
      {stats.gaps?.length > 0 && (
        <Section title="Das fällt auf" hint="Rechnerisch erkannte Lücken">
          <ul className="space-y-2">
            {stats.gaps.map((g, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className="flex gap-2.5 text-sm text-ink-800"
              >
                <span className="text-clay-500 shrink-0">•</span>
                {g}
              </motion.li>
            ))}
          </ul>
        </Section>
      )}

      {/* Farbpalette */}
      <Section
        title="Farbpalette"
        hint={`${stats.neutral_share}% deiner Teile sind neutrale Farben`}
      >
        <ColorBar colors={stats.colors} />
      </Section>

      {/* Outfit-Rollen */}
      <Section title="Verteilung nach Outfit-Rolle" hint="Ausgewogenheit zwischen Ober-, Unterteilen und Schuhen">
        <BarList data={stats.slots} />
      </Section>

      {/* Saison */}
      <Section title="Saison-Abdeckung" hint="Wie gut bist du für jede Jahreszeit ausgestattet?">
        <SeasonRings seasons={stats.seasons} totalPieces={stats.total_pieces} />
      </Section>

      {/* Kategorien */}
      <Section title="Top-Kategorien">
        <BarList data={stats.categories} />
      </Section>

      {/* Stil & Anlass */}
      <div className="grid sm:grid-cols-2 gap-4">
        <Section title="Stile">
          <BarList data={stats.styles} emptyText="Noch keine Stile erfasst" />
        </Section>
        <Section title="Anlässe">
          <BarList data={stats.occasions} emptyText="Noch keine Anlässe erfasst" />
        </Section>
      </div>

      {/* Materialien & Marken */}
      <div className="grid sm:grid-cols-2 gap-4">
        <Section title="Materialien">
          <BarList data={stats.materials} emptyText="Noch keine Materialien erfasst" />
        </Section>
        <Section title="Marken">
          <BarList data={stats.brands} emptyText="Noch keine Marken erfasst" />
        </Section>
      </div>

      {/* Duplikate */}
      {stats.duplicates?.length > 0 && (
        <Section title="Häufungen" hint="Davon hast du auffällig viel">
          <div className="flex flex-wrap gap-2">
            {stats.duplicates.map((d, i) => (
              <span
                key={i}
                className="text-sm bg-sand-100 text-ink-800 rounded-full px-3 py-1.5"
              >
                {d.count}× {d.color} {d.category}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Datenqualität */}
      <Section title="Datenqualität" hint="Je vollständiger, desto besser die KI-Empfehlungen">
        <div className="flex items-center gap-4">
          <div className="flex-1 h-2 bg-sand-100 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-clay-500 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${stats.completeness}%` }}
              transition={{ duration: 0.7 }}
            />
          </div>
          <span className="text-sm font-semibold text-ink-900 tabular-nums">
            {stats.completeness}%
          </span>
        </div>
      </Section>

      {/* KI-Einschätzung */}
      <Section title="KI-Einschätzung" hint="Ehrliche Bewertung deiner Garderobe durch Gemini">
        <AnimatePresence mode="wait">
          {!insights ? (
            <motion.button
              key="btn"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={loadInsights}
              disabled={aiLoading}
              className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {aiLoading ? (
                <>
                  <motion.span
                    className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                  />
                  Analysiere deine Garderobe …
                </>
              ) : (
                "✦ Garderobe analysieren"
              )}
            </motion.button>
          ) : (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-5"
            >
              <ScoreRing score={insights.score} label="Ausgewogenheit" />

              <div className="text-center">
                <p className="font-medium text-ink-900">{insights.headline}</p>
                {insights.style_profile && (
                  <span className="inline-block mt-2 text-xs bg-sand-100 text-ink-700 rounded-full px-3 py-1">
                    {insights.style_profile}
                  </span>
                )}
              </div>

              <p className="text-sm text-ink-800 leading-relaxed bg-sand-100 rounded-xl p-4">
                {insights.summary}
              </p>

              {insights.strengths?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-emerald-600 uppercase tracking-wide mb-2">
                    Stärken
                  </h4>
                  <ul className="space-y-1.5">
                    {insights.strengths.map((s, i) => (
                      <li key={i} className="text-sm text-ink-800 flex gap-2">
                        <span className="text-emerald-600 shrink-0">+</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {insights.weaknesses?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-clay-600 uppercase tracking-wide mb-2">
                    Schwächen
                  </h4>
                  <ul className="space-y-1.5">
                    {insights.weaknesses.map((w, i) => (
                      <li key={i} className="text-sm text-ink-800 flex gap-2">
                        <span className="text-clay-600 shrink-0">−</span>
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {insights.next_steps?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-ink-900 uppercase tracking-wide mb-2">
                    Nächste Schritte
                  </h4>
                  <ol className="space-y-1.5">
                    {insights.next_steps.map((n, i) => (
                      <li key={i} className="text-sm text-ink-800 flex gap-2.5">
                        <span className="shrink-0 w-5 h-5 rounded-full bg-clay-500 text-white text-xs flex items-center justify-center font-medium">
                          {i + 1}
                        </span>
                        {n}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              <button
                onClick={loadInsights}
                disabled={aiLoading}
                className="w-full rounded-xl border border-sand-200 text-ink-700 font-medium py-2.5 hover:bg-sand-100 transition disabled:opacity-60"
              >
                {aiLoading ? "Analysiere …" : "Neu analysieren"}
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </Section>
    </motion.div>
  );
}
