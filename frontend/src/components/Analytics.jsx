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

// Lade-Spinner, in allen drei Auswertungen gleich
function Spinner() {
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

function EmptyState({ icon, title, text }) {
  return (
    <div className="text-center py-20">
      <div className="text-5xl mb-4">{icon}</div>
      <h2 className="text-lg font-semibold text-ink-900">{title}</h2>
      <p className="text-sm text-ink-700/60 mt-1 max-w-xs mx-auto">{text}</p>
    </div>
  );
}

// Rechnerisch erkannte Lücken – identisch für alle Sammlungen
function GapsSection({ gaps, hint }) {
  if (!gaps?.length) return null;
  return (
    <Section title="Das fällt auf" hint={hint}>
      <ul className="space-y-2">
        {gaps.map((g, i) => (
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
  );
}

/**
 * KI-Einschätzung. Wird von allen drei Auswertungen genutzt – der einzige
 * Unterschied ist der Loader und wie das Profil-Feld heißt.
 */
function InsightPanel({ title, hint, button, loadingLabel, loader, profileField }) {
  const [insights, setInsights] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setBusy(true);
    setError("");
    try {
      setInsights(await loader());
    } catch (e) {
      setError(e.message || "Analyse fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Section title={title} hint={hint}>
      {error && (
        <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2 mb-3">
          {error}
        </div>
      )}
      <AnimatePresence mode="wait">
        {!insights ? (
          <motion.button
            key="btn"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={load}
            disabled={busy}
            className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {busy ? (
              <>
                <motion.span
                  className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                />
                {loadingLabel}
              </>
            ) : (
              button
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
              {insights[profileField] && (
                <span className="inline-block mt-2 text-xs bg-sand-100 text-ink-700 rounded-full px-3 py-1">
                  {insights[profileField]}
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
              onClick={load}
              disabled={busy}
              className="w-full rounded-xl border border-sand-200 text-ink-700 font-medium py-2.5 hover:bg-sand-100 transition disabled:opacity-60"
            >
              {busy ? "Analysiere …" : "Neu analysieren"}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </Section>
  );
}

function WardrobeAnalytics() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  if (stats?.empty) {
    return (
      <EmptyState
        icon="📊"
        title="Noch keine Daten"
        text="Sobald du Kleidungsstücke erfasst hast, findest du hier die Auswertung deiner Garderobe."
      />
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

      <GapsSection gaps={stats.gaps} hint="Rechnerisch erkannte Lücken" />

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


      <InsightPanel
        title="KI-Einschätzung"
        hint="Ehrliche Bewertung deiner Garderobe durch Gemini"
        button="✦ Garderobe analysieren"
        loadingLabel="Analysiere deine Garderobe …"
        loader={() => api.getInsights()}
        profileField="style_profile"
      />
    </motion.div>
  );
}

// ══════════════════════════════════════════════════════════════
//  Uhren
// ══════════════════════════════════════════════════════════════

function money(value, currency = "EUR") {
  if (value === null || value === undefined) return "–";
  try {
    return new Intl.NumberFormat("de-DE", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${value} ${currency}`;
  }
}

function formatDate(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

function WatchAnalytics() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getWatchStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  if (stats?.empty) {
    return (
      <EmptyState
        icon="⌚"
        title="Noch keine Uhren"
        text="Sobald du Uhren erfasst hast, siehst du hier Stilverteilung, Sammlungswert und fällige Services."
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {error && (
        <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <StatCard
          label="Uhren in der Sammlung"
          value={stats.total}
          sub={`${stats.diversity.styles} verschiedene Stile`}
          accent
        />
        <StatCard
          label="Sammlungswert"
          value={stats.total_value !== null ? money(stats.total_value) : "–"}
          sub={
            stats.value_change !== null
              ? `${stats.value_change >= 0 ? "+" : ""}${money(stats.value_change)} zum Kaufpreis`
              : "Kaufpreise ergänzen für Vergleich"
          }
        />
        <StatCard
          label="Ø Durchmesser"
          value={stats.avg_diameter ? `${stats.avg_diameter} mm` : "–"}
          sub={
            stats.smallest_diameter && stats.largest_diameter
              ? `${stats.smallest_diameter}–${stats.largest_diameter} mm`
              : null
          }
        />
        <StatCard label="Verschiedene Marken" value={stats.diversity.brands} />
      </div>

      {/* Handgelenk-Einschätzung, sobald das Maß im Profil steht */}
      {stats.wrist_advice && (
        <Section title="An deinem Handgelenk" hint="Rechnerisch, ohne KI">
          <p className="text-sm text-ink-800">{stats.wrist_advice}</p>
        </Section>
      )}

      {/* Service ist der Punkt, an dem eine Sammlung real Geld kostet */}
      {stats.service_soon?.length > 0 && (
        <Section title="Service" hint="Fällig oder in den nächsten sechs Monaten">
          <div className="space-y-2">
            {stats.service_soon.map((s) => (
              <div
                key={s.id}
                className={`flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 ${
                  s.overdue ? "bg-clay-500/10" : "bg-sand-100"
                }`}
              >
                <span className="text-sm text-ink-900 truncate">{s.name}</span>
                <span
                  className={`text-xs flex-shrink-0 ${
                    s.overdue ? "text-clay-600 font-medium" : "text-ink-700/60"
                  }`}
                >
                  {s.overdue ? "überfällig seit " : "fällig "}
                  {formatDate(s.due_date)}
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {stats.warranty_active?.length > 0 && (
        <Section title="Garantie läuft noch">
          <div className="flex flex-wrap gap-2">
            {stats.warranty_active.map((w) => (
              <span
                key={w.id}
                className="text-sm bg-emerald-500/10 text-emerald-700 rounded-full px-3 py-1.5"
              >
                {w.name} · bis {formatDate(w.until)}
              </span>
            ))}
          </div>
        </Section>
      )}

      <GapsSection gaps={stats.gaps} hint="Wo die Sammlung noch Luft hat" />

      <Section title="Uhrentypen" hint="Wie breit die Sammlung aufgestellt ist">
        <BarList data={stats.styles} emptyText="Noch keine Typen erfasst" />
      </Section>

      <Section title="Anlässe" hint="Welche Gelegenheiten abgedeckt sind">
        <BarList data={stats.occasions} emptyText="Noch keine Anlässe erfasst" />
      </Section>

      <div className="grid sm:grid-cols-2 gap-4">
        <Section title="Marken">
          <BarList data={stats.brands} emptyText="Noch keine Marken erfasst" />
        </Section>
        <Section title="Werke">
          <BarList data={stats.movements} emptyText="Noch keine Werke erfasst" />
        </Section>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <Section title="Gehäusematerialien">
          <BarList data={stats.case_materials} emptyText="Noch nichts erfasst" />
        </Section>
        <Section title="Armbänder">
          <BarList data={stats.band_materials} emptyText="Noch nichts erfasst" />
        </Section>
      </div>

      {stats.complications?.length > 0 && (
        <Section title="Funktionen" hint="Was deine Uhren können">
          <BarList data={stats.complications} />
        </Section>
      )}

      <InsightPanel
        title="KI-Einschätzung"
        hint="Ehrliche Bewertung deiner Uhrensammlung durch Gemini"
        button="✦ Sammlung analysieren"
        loadingLabel="Analysiere deine Uhren …"
        loader={() => api.getWatchInsights()}
        profileField="collection_profile"
      />
    </motion.div>
  );
}

// ══════════════════════════════════════════════════════════════
//  Düfte
// ══════════════════════════════════════════════════════════════

function FragranceAnalytics() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getFragranceStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  if (stats?.empty) {
    return (
      <EmptyState
        icon="🧴"
        title="Noch keine Düfte"
        text="Sobald du Düfte erfasst hast, siehst du hier dein Duftprofil, die Saison-Abdeckung und Nachkauf-Hinweise."
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {error && (
        <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <StatCard
          label="Düfte in der Sammlung"
          value={stats.total}
          sub={`${stats.total_bottles} Flakons`}
          accent
        />
        <StatCard
          label="Duftfamilien"
          value={stats.diversity.families}
          sub={`${stats.diversity.notes} verschiedene Noten`}
        />
        <StatCard
          label="Gesamtvolumen"
          value={stats.total_ml ? `${stats.total_ml} ml` : "–"}
        />
        <StatCard
          label="Investiert"
          value={stats.total_spend !== null ? money(stats.total_spend) : "–"}
        />
      </div>

      {/* Nachkauf: das ist der praktische Alltagswert der Sammlung */}
      {stats.low_stock?.length > 0 && (
        <Section title="Wird knapp" hint="Unter 15 Prozent Füllstand">
          <div className="space-y-2">
            {stats.low_stock.map((f) => (
              <div
                key={f.id}
                className="flex items-center gap-3 rounded-xl bg-clay-500/10 px-3 py-2.5"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-ink-900 truncate">{f.name}</p>
                  {f.brand && (
                    <p className="text-xs text-ink-700/50 truncate">{f.brand}</p>
                  )}
                </div>
                <span className="text-xs font-medium text-clay-600 flex-shrink-0 tabular-nums">
                  {f.fill_level} %
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {stats.expiring?.length > 0 && (
        <Section
          title="Haltbarkeit"
          hint="Geöffnete Flakons, die kippen oder bald kippen"
        >
          <div className="space-y-2">
            {stats.expiring.map((f) => (
              <div
                key={f.id}
                className={`flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 ${
                  f.expired ? "bg-clay-500/10" : "bg-sand-100"
                }`}
              >
                <span className="text-sm text-ink-900 truncate">{f.name}</span>
                <span
                  className={`text-xs flex-shrink-0 ${
                    f.expired ? "text-clay-600 font-medium" : "text-ink-700/60"
                  }`}
                >
                  {f.expired ? "überschritten seit " : "bis "}
                  {formatDate(f.expires_at)}
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      <GapsSection gaps={stats.gaps} hint="Lücken und Dopplungen im Duftprofil" />

      <Section title="Saison-Abdeckung" hint="Wie gut jede Jahreszeit versorgt ist">
        <SeasonRings seasons={stats.seasons} totalPieces={stats.total} />
      </Section>

      <Section title="Duftfamilien" hint="Dein Duftprofil auf einen Blick">
        <BarList data={stats.families} emptyText="Noch keine Familien erfasst" />
      </Section>

      <Section title="Häufigste Noten" hint="Über alle Ebenen der Duftpyramide">
        <BarList data={stats.notes} emptyText="Noch keine Noten erfasst" />
      </Section>

      {stats.base_notes?.length > 0 && (
        <Section
          title="Basisnoten"
          hint="Die Basis bestimmt, wie ein Duft in Erinnerung bleibt"
        >
          <BarList data={stats.base_notes} />
        </Section>
      )}

      {/* Dopplungen sind bei Düften der häufigste blinde Fleck */}
      {stats.duplicates?.length > 0 && (
        <Section
          title="Riecht ähnlich"
          hint="Gleiche Familie mit überlappender Basis"
        >
          <div className="space-y-3">
            {stats.duplicates.map((d, i) => (
              <div key={i} className="rounded-xl bg-sand-100 px-3 py-2.5">
                <p className="text-sm text-ink-900">
                  {d.count}× {d.family}
                </p>
                <p className="text-xs text-ink-700/60 mt-0.5">
                  {d.names.join(", ")} — gemeinsam: {d.shared_notes.join(", ")}
                </p>
              </div>
            ))}
          </div>
        </Section>
      )}

      <div className="grid sm:grid-cols-2 gap-4">
        <Section title="Anlässe">
          <BarList data={stats.occasions} emptyText="Noch keine Anlässe erfasst" />
        </Section>
        <Section title="Tageszeiten">
          <BarList data={stats.times} emptyText="Noch nichts erfasst" />
        </Section>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <Section title="Häuser">
          <BarList data={stats.brands} emptyText="Noch keine Häuser erfasst" />
        </Section>
        <Section title="Konzentrationen">
          <BarList data={stats.concentrations} emptyText="Noch nichts erfasst" />
        </Section>
      </div>

      <InsightPanel
        title="KI-Einschätzung"
        hint="Ehrliche Bewertung deiner Duftsammlung durch Gemini"
        button="✦ Sammlung analysieren"
        loadingLabel="Analysiere deine Düfte …"
        loader={() => api.getFragranceInsights()}
        profileField="collection_profile"
      />
    </motion.div>
  );
}

// ══════════════════════════════════════════════════════════════
//  Accessoires
// ══════════════════════════════════════════════════════════════

function AccessoryAnalytics() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getAccessoryStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  if (stats?.empty) {
    return (
      <EmptyState
        icon="💎"
        title="Noch keine Accessoires"
        text="Sobald du Schmuck, Taschen oder Brillen erfasst hast, siehst du hier die Verteilung und Analyse."
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {error && (
        <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3">{error}</div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Accessoires gesamt" value={stats.total} accent />
        <StatCard label="Verschiedene Marken" value={stats.diversity?.brands ?? stats.brands?.length ?? 0} />
      </div>

      {stats.needs_review > 0 && (
        <div className="rounded-2xl bg-amber-400/10 px-4 py-3">
          <p className="text-sm text-ink-800">
            {stats.needs_review} {stats.needs_review === 1 ? "Eintrag wartet" : "Einträge warten"} noch auf die KI-Erfassung.
          </p>
        </div>
      )}

      <Section title="Nach Gruppe">
        <BarList data={stats.groups} emptyText="Noch nichts erfasst" />
      </Section>

      <Section title="Typen" hint="Die häufigsten Arten">
        <BarList data={stats.types} emptyText="Noch nichts erfasst" />
      </Section>

      <div className="grid sm:grid-cols-2 gap-4">
        <Section title="Marken">
          <BarList data={stats.brands} emptyText="Noch keine Marken" />
        </Section>
        <Section title="Materialien">
          <BarList data={stats.materials} emptyText="Noch nichts erfasst" />
        </Section>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <Section title="Stile">
          <BarList data={stats.styles} emptyText="Noch nichts erfasst" />
        </Section>
        <Section title="Anlässe">
          <BarList data={stats.occasions} emptyText="Noch nichts erfasst" />
        </Section>
      </div>
    </motion.div>
  );
}

// ══════════════════════════════════════════════════════════════
//  Umschalter über den drei Auswertungen
// ══════════════════════════════════════════════════════════════

const VIEWS = [
  { id: "wardrobe", label: "Kleidung", icon: "👕" },
  { id: "watches", label: "Uhren", icon: "⌚" },
  { id: "accessories", label: "Accessoires", icon: "💎" },
  { id: "fragrances", label: "Düfte", icon: "🧴" },
];

export default function Analytics({ hasWatches = false, hasFragrances = false, hasAccessories = false }) {
  const [view, setView] = useState("wardrobe");

  const available = VIEWS.filter(
    (v) =>
      v.id === "wardrobe" ||
      (v.id === "watches" && hasWatches) ||
      (v.id === "accessories" && hasAccessories) ||
      (v.id === "fragrances" && hasFragrances)
  );

  return (
    <div>
      {available.length > 1 && (
        <div className="relative flex bg-sand-100 rounded-2xl p-1 mb-5">
          {available.map((v) => {
            const active = view === v.id;
            return (
              <button
                key={v.id}
                onClick={() => setView(v.id)}
                className="relative flex-1 py-2 rounded-xl text-sm font-medium z-10"
              >
                {active && (
                  <motion.div
                    layoutId="analytics-pill"
                    className="absolute inset-0 bg-white rounded-xl shadow-sm"
                    transition={{ type: "spring", stiffness: 400, damping: 32 }}
                  />
                )}
                <span
                  className={`relative flex items-center justify-center gap-1.5 ${
                    active ? "text-ink-900" : "text-ink-700/50"
                  }`}
                >
                  <span className={active ? "" : "grayscale opacity-70"}>{v.icon}</span>
                  {v.label}
                </span>
              </button>
            );
          })}
        </div>
      )}

      <AnimatePresence mode="wait">
        {view === "wardrobe" && <WardrobeAnalytics key="wardrobe" />}
        {view === "watches" && <WatchAnalytics key="watches" />}
        {view === "accessories" && <AccessoryAnalytics key="accessories" />}
        {view === "fragrances" && <FragranceAnalytics key="fragrances" />}
      </AnimatePresence>
    </div>
  );
}
