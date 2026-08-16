import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";
import { SelectField, TextField } from "./Field";

// Bild je nach Präferenz: inszeniert oder eigenes Foto
function pickThumb(entry, useAiImages) {
  if (useAiImages && entry.has_ai_image) {
    return entry.ai_thumbnail_url || entry.ai_image_url;
  }
  return entry.thumbnail_url || entry.image_url;
}

// ── Karte für Uhr oder Duft ──
function CollectionCard({ entry, kind, onSelect, viewMode, useAiImages }) {
  const thumb = pickThumb(entry, useAiImages);

  const title =
    kind === "watch"
      ? entry.name || [entry.brand, entry.model].filter(Boolean).join(" ") || "Uhr"
      : kind === "accessory"
      ? entry.name || [entry.brand, entry.type].filter(Boolean).join(" ") || "Accessoire"
      : entry.name || "Duft";

  const subtitle =
    kind === "watch"
      ? [entry.style, entry.case_diameter ? `${entry.case_diameter} mm` : ""]
          .filter(Boolean)
          .join(" · ")
      : kind === "accessory"
      ? [entry.brand, entry.type].filter(Boolean).join(" · ")
      : [entry.brand, entry.family].filter(Boolean).join(" · ");

  // Warnhinweise, die man auf der Karte sehen will
  const alerts = [];
  if (entry.needs_review) alerts.push({ icon: "🔍", label: "Daten fehlen" });
  if (kind === "watch" && entry.service_due) alerts.push({ icon: "🔧", label: "Service fällig" });
  if (kind === "fragrance" && entry.expired) alerts.push({ icon: "⚠️", label: "Abgelaufen" });
  if (kind === "fragrance" && entry.low_stock && !entry.expired)
    alerts.push({ icon: "🪫", label: "Fast leer" });

  if (viewMode === "grid") {
    return (
      <motion.button
        layout
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        whileTap={{ scale: 0.97 }}
        onClick={() => onSelect(entry)}
        className="group text-left relative"
      >
        {entry.favorite && (
          <div className="absolute top-2 left-2 z-10 bg-amber-400 rounded-full w-6 h-6 flex items-center justify-center shadow-sm">
            <span className="text-sm">⭐</span>
          </div>
        )}
        <div className="relative aspect-square rounded-2xl overflow-hidden bg-white shadow-soft">
          <img
            src={thumb}
            alt={title}
            className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
          />
          {useAiImages && entry.has_ai_image && (
            <span className="absolute bottom-2 left-2 bg-clay-500/90 text-white text-[10px] font-medium rounded-full px-2 py-0.5 backdrop-blur-sm">
              ✨ Inszeniert
            </span>
          )}
          {alerts.length > 0 && (
            <span className="absolute top-2 right-2 bg-ink-900/80 text-white text-[10px] font-medium rounded-full px-2 py-0.5 backdrop-blur-sm">
              {alerts[0].icon}
            </span>
          )}
          {kind === "fragrance" && entry.fill_level !== null && entry.fill_level < 100 && (
            <div className="absolute inset-x-0 bottom-0 h-1 bg-ink-900/10">
              <div
                className={`h-full ${entry.low_stock ? "bg-clay-500" : "bg-clay-400/70"}`}
                style={{ width: `${entry.fill_level}%` }}
              />
            </div>
          )}
        </div>
        <span className="mt-1.5 block text-sm text-ink-800 truncate">{title}</span>
        {subtitle && (
          <span className="block text-xs text-ink-700/50 truncate">{subtitle}</span>
        )}
      </motion.button>
    );
  }

  return (
    <motion.button
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(entry)}
      className="w-full group text-left bg-white rounded-xl p-3 shadow-soft hover:shadow-md transition flex items-center gap-3"
    >
      <div className="relative w-14 h-14 flex-shrink-0 rounded-lg overflow-hidden bg-sand-50">
        <img
          src={thumb}
          alt={title}
          className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
        />
        {entry.favorite && (
          <div className="absolute top-0.5 left-0.5 bg-amber-400 rounded-full w-4 h-4 flex items-center justify-center">
            <span className="text-[10px]">⭐</span>
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <span className="font-medium text-ink-900 truncate block">{title}</span>
        <div className="flex items-center gap-2 mt-0.5 text-xs text-ink-700/50">
          {subtitle && <span className="truncate">{subtitle}</span>}
        </div>
        {alerts.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1">
            {alerts.map((a) => (
              <span
                key={a.label}
                className="text-[10px] rounded-full bg-clay-500/10 text-clay-600 px-2 py-0.5"
              >
                {a.icon} {a.label}
              </span>
            ))}
          </div>
        )}
      </div>
      <span className="text-ink-700/30 group-hover:text-ink-700/60 transition">→</span>
    </motion.button>
  );
}

// ── Umschalter für Bildquelle und Ansicht ──
function ViewToggles({ viewMode, setViewMode, useAiImages, setUseAiImages }) {
  return (
    <div className="flex items-center justify-between gap-2 mb-4">
      <div className="inline-flex items-center gap-1 bg-sand-100 rounded-xl p-1">
        <button
          onClick={() => setUseAiImages(false)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            !useAiImages ? "bg-white text-ink-900 shadow-sm" : "text-ink-700/60"
          }`}
        >
          <span className="mr-1">📷</span> Eigene
        </button>
        <button
          onClick={() => setUseAiImages(true)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            useAiImages ? "bg-white text-ink-900 shadow-sm" : "text-ink-700/60"
          }`}
        >
          <span className="mr-1">✨</span> Inszeniert
        </button>
      </div>

      <div className="inline-flex items-center gap-1 bg-sand-100 rounded-xl p-1">
        <button
          onClick={() => setViewMode("grid")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            viewMode === "grid" ? "bg-white text-ink-900 shadow-sm" : "text-ink-700/60"
          }`}
        >
          <span className="mr-1">▦</span> Grid
        </button>
        <button
          onClick={() => setViewMode("list")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            viewMode === "list" ? "bg-white text-ink-900 shadow-sm" : "text-ink-700/60"
          }`}
        >
          <span className="mr-1">☰</span> Liste
        </button>
      </div>
    </div>
  );
}

// ── Duftberatung aus dem eigenen Bestand ──
function FragranceAdvice({ meta, onSelectId }) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [occasion, setOccasion] = useState("");
  const [season, setSeason] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await api.fragranceAdvice({ question, occasion, season }));
    } catch (err) {
      setError(err.message || "Beratung fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 bg-gradient-to-br from-clay-500 to-clay-600 rounded-2xl p-5 text-white shadow-lg"
      >
        <div className="flex items-center gap-3 mb-3">
          <span className="text-3xl">🧴</span>
          <div>
            <h3 className="font-semibold text-lg">Welchen Duft heute?</h3>
            <p className="text-sm text-white/80">
              Empfehlung aus deiner eigenen Sammlung, passend zu Anlass und Jahreszeit
            </p>
          </div>
        </div>
        <button
          onClick={() => setOpen(true)}
          className="w-full bg-white text-clay-600 font-medium rounded-xl py-2.5 hover:bg-white/95 transition"
        >
          Beraten lassen
        </button>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-8 bg-white rounded-2xl p-5 shadow-soft space-y-4"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg text-ink-900">🧴 Duftberatung</h3>
        <button
          onClick={() => {
            setOpen(false);
            setResult(null);
          }}
          className="text-ink-700/50 hover:text-ink-900 text-2xl leading-none"
        >
          ×
        </button>
      </div>

      {!result && (
        <>
          <TextField
            label="Deine Frage"
            value={question}
            onChange={setQuestion}
            placeholder="z.B. Was nehme ich zum Vorstellungsgespräch?"
          />
          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Anlass"
              value={occasion}
              onChange={setOccasion}
              options={meta?.fragrances?.occasions || []}
            />
            <SelectField
              label="Jahreszeit"
              value={season}
              onChange={setSeason}
              options={meta?.fragrances?.seasons || []}
            />
          </div>

          {error && (
            <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2">
              {error}
            </div>
          )}

          <button
            onClick={ask}
            disabled={loading}
            className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 transition disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <motion.span
                  className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                />
                Wird geprüft …
              </>
            ) : (
              "Empfehlung holen"
            )}
          </button>
        </>
      )}

      {result && (
        <div className="space-y-4">
          {result.pick ? (
            <button
              onClick={() => onSelectId?.(result.pick.id)}
              className="w-full flex items-center gap-3 text-left rounded-2xl bg-clay-500/8 p-3 hover:bg-clay-500/12 transition"
            >
              <img
                src={result.pick.thumbnail_url}
                alt={result.pick.name}
                className="w-16 h-16 rounded-xl object-cover flex-shrink-0"
              />
              <div className="min-w-0">
                <p className="text-[11px] font-medium uppercase tracking-wide text-clay-600">
                  Empfehlung
                </p>
                <p className="font-semibold text-ink-900 truncate">{result.pick.name}</p>
                <p className="text-xs text-ink-700/60 truncate">{result.pick.brand}</p>
              </div>
            </button>
          ) : (
            <div className="rounded-2xl bg-amber-400/10 px-4 py-3">
              <p className="text-sm text-ink-800">
                Kein Duft aus deiner Sammlung passt hier wirklich.
              </p>
            </div>
          )}

          {result.reason && (
            <p className="text-sm text-ink-800 leading-relaxed">{result.reason}</p>
          )}

          {result.application && (
            <div className="rounded-xl bg-sand-100 px-3 py-2">
              <p className="text-xs text-ink-700/70">
                <span className="font-medium">Dosierung:</span> {result.application}
              </p>
            </div>
          )}

          {result.alternative && (
            <button
              onClick={() => onSelectId?.(result.alternative.id)}
              className="w-full flex items-center gap-3 text-left rounded-xl border border-sand-200 p-2.5 hover:bg-sand-50 transition"
            >
              <img
                src={result.alternative.thumbnail_url}
                alt={result.alternative.name}
                className="w-11 h-11 rounded-lg object-cover flex-shrink-0"
              />
              <div className="min-w-0">
                <p className="text-[11px] text-ink-700/50">Alternative</p>
                <p className="text-sm font-medium text-ink-900 truncate">
                  {result.alternative.name}
                </p>
              </div>
            </button>
          )}

          {result.gap && (
            <div className="rounded-xl bg-sand-100 px-3 py-2">
              <p className="text-xs text-ink-700/70">
                <span className="font-medium">Was fehlt:</span> {result.gap}
              </p>
            </div>
          )}

          <button
            onClick={() => setResult(null)}
            className="w-full text-sm text-ink-700/60 hover:text-ink-900 transition"
          >
            Neue Frage
          </button>
        </div>
      )}
    </motion.div>
  );
}

// ══════════════════════════════════════════════════════════════
//  Sammlungs-Ansicht
// ══════════════════════════════════════════════════════════════

const GROUPERS = {
  watch: {
    key: (w) => w.style || "Ohne Typ",
    order: (meta) => meta?.watches?.styles || [],
    emptyIcon: "⌚",
    emptyTitle: "Noch keine Uhren erfasst",
    emptyText:
      "Füge deine erste Uhr hinzu. Ein Foto vom Zifferblatt genügt – steht die Referenznummer auf dem Gehäuseboden, erkennt die KI das exakte Modell.",
  },
  accessory: {
    key: (a) => {
      // Nach Gruppe (Schmuck/Taschen/Brillen/Sonstiges) gruppieren
      const type = a.type || "Sonstiges Accessoire";
      const groups = {
        Schmuck: ["Ring","Ehering","Verlobungsring","Halskette","Kette","Anhänger","Armband","Armreif","Armkette","Ohrringe","Ohrring (einzeln)","Ohrstecker","Creolen","Brosche","Anstecker","Manschettenknöpfe","Krawattennadel","Krawattenklammer","Körperschmuck","Haarschmuck","Haarreif","Haarspange"],
        Taschen: ["Handtasche","Umhängetasche","Schultertasche","Crossbody-Bag","Tote Bag","Clutch","Abendtasche","Minibag","Bucket Bag","Hobo Bag","Shopper","Rucksack","Laptoprucksack","Daypack","Gürteltasche / Fanny Pack","Bauchtasche","Aktentasche","Dokumententasche","Brieftasche","Portemonnaie","Kartenetui","Schlüsseletui","Kulturbeutel","Weekender","Duffle Bag","Sporttasche"],
        Brillen: ["Sonnenbrille","Lesebrille","Computerbrille","Korrektionsbrille","Sportbrille","Skibrille","Pilotenbrille","Aviatorbrille","Retro-Brille","Cat-Eye-Brille","Browline-Brille","Hornbrille","Clubmaster","Wayfarer"],
      };
      for (const [group, types] of Object.entries(groups)) {
        if (types.includes(type)) return group;
      }
      return "Sonstiges";
    },
    order: () => ["Schmuck", "Taschen", "Brillen", "Sonstiges"],
    emptyIcon: "💎",
    emptyTitle: "Noch keine Accessoires erfasst",
    emptyText:
      "Füge dein erstes Accessoire hinzu – Schmuck, Tasche oder Brille. Die KI liest Logo und Prägungen und kennt dann oft Marke und Materialien.",
  },
  fragrance: {
    key: (f) => f.family || "Ohne Familie",
    order: (meta) => meta?.fragrances?.families || [],
    emptyIcon: "🧴",
    emptyTitle: "Noch keine Düfte erfasst",
    emptyText:
      "Füge deinen ersten Duft hinzu. Die KI liest Name und Konzentration vom Flakon und kennt dann meist auch die Duftpyramide.",
  },
};

export default function CollectionView({
  kind,
  entries,
  meta,
  loading,
  viewMode,
  setViewMode,
  useAiImages,
  setUseAiImages,
  onSelect,
  onSelectId,
}) {
  const config = GROUPERS[kind];

  const grouped = useMemo(() => {
    const sorted = [...entries].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );
    const favorites = sorted.filter((e) => e.favorite);
    const rest = sorted.filter((e) => !e.favorite);

    const map = new Map();
    for (const entry of rest) {
      const key = config.key(entry);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(entry);
    }

    // Reihenfolge aus dem Vokabular, alles Unbekannte hinten
    const known = config.order(meta);
    const groups = [
      ...known.filter((k) => map.has(k)).map((k) => ({ group: k, items: map.get(k) })),
      ...[...map.keys()]
        .filter((k) => !known.includes(k))
        .map((k) => ({ group: k, items: map.get(k) })),
    ];

    return { favorites, groups };
  }, [entries, meta, config]);

  if (loading) {
    return (
      <div className="flex justify-center py-20 text-ink-700/50">
        <motion.span
          className="inline-block w-6 h-6 border-2 border-clay-500 border-t-transparent rounded-full"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
        />
      </div>
    );
  }

  if (!entries.length) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center py-20"
      >
        <div className="text-5xl mb-4">{config.emptyIcon}</div>
        <h2 className="text-lg font-semibold text-ink-900">{config.emptyTitle}</h2>
        <p className="text-sm text-ink-700/60 mt-1 max-w-xs mx-auto">
          {config.emptyText}
        </p>
      </motion.div>
    );
  }

  function renderSection(label, items, count) {
    return (
      <section key={label}>
        <div className="flex items-center gap-3 mb-3">
          <h2 className="text-sm font-semibold text-ink-900 uppercase tracking-wide">
            {label}
          </h2>
          <span className="text-xs text-ink-700/40">{count ?? items.length}</span>
          <div className="flex-1 h-px bg-sand-100" />
        </div>
        {viewMode === "grid" ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <AnimatePresence>
              {items.map((entry) => (
                <CollectionCard
                  key={entry.id}
                  entry={entry}
                  kind={kind}
                  onSelect={onSelect}
                  viewMode="grid"
                  useAiImages={useAiImages}
                />
              ))}
            </AnimatePresence>
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence>
              {items.map((entry) => (
                <CollectionCard
                  key={entry.id}
                  entry={entry}
                  kind={kind}
                  onSelect={onSelect}
                  viewMode="list"
                  useAiImages={useAiImages}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </section>
    );
  }

  return (
    <div>
      {kind === "fragrance" && (
        <FragranceAdvice meta={meta} onSelectId={onSelectId} />
      )}

      <ViewToggles
        viewMode={viewMode}
        setViewMode={setViewMode}
        useAiImages={useAiImages}
        setUseAiImages={setUseAiImages}
      />

      <div className="space-y-8">
        {grouped.favorites.length > 0 &&
          renderSection("⭐ Favoriten", grouped.favorites)}
        {grouped.groups.map((g) => renderSection(g.group, g.items))}
      </div>
    </div>
  );
}
