import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api";
import { SelectField, TextField } from "./Field";

export default function OutfitGenerator({
  meta,
  onItemClick,
  onWatchClick,
  onFragranceClick,
  useAiImages = false,
}) {
  const [occasion, setOccasion] = useState("");
  const [weather, setWeather] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [outfits, setOutfits] = useState(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(false);

  async function generate() {
    setLoading(true);
    setError("");
    setOutfits(null);
    try {
      const result = await api.generateOutfits({ occasion, weather, note, count: 5 });
      setOutfits(result.outfits || []);
      setExpanded(true);
    } catch (err) {
      setError(err.message || "Outfit-Generierung fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setOutfits(null);
    setExpanded(false);
    setError("");
    setWeather("");
  }

// Wetter-Optionen: bewusst kurz und bildlich statt meteorologisch korrekt.
// Der Nutzer soll schnell tippen, nicht einen Wetterbericht eingeben.
const WEATHER_OPTIONS = [
  { value: "heiß (über 28°C)",    icon: "🌡️" },
  { value: "warm und sonnig",      icon: "☀️" },
  { value: "angenehm (ca. 18°C)", icon: "🌤️" },
  { value: "kühl (unter 15°C)",   icon: "🌥️" },
  { value: "kalt (unter 5°C)",    icon: "🧊" },
  { value: "regnerisch",          icon: "🌧️" },
  { value: "windig",              icon: "💨" },
  { value: "Schnee",              icon: "❄️" },
];

  return (
    <div className="mb-8">
      {!expanded && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-clay-500 to-clay-600 rounded-2xl p-5 text-white shadow-lg"
        >
          <div className="flex items-center gap-3 mb-3">
            <span className="text-3xl">✨</span>
            <div>
              <h3 className="font-semibold text-lg">Outfit-Generator</h3>
              <p className="text-sm text-white/80">
                Lass die KI 5 komplette Outfits für dich zusammenstellen
              </p>
            </div>
          </div>
          <button
            onClick={() => setExpanded(true)}
            className="w-full bg-white text-clay-600 font-medium rounded-xl py-2.5 hover:bg-white/95 transition"
          >
            Jetzt ausprobieren
          </button>
        </motion.div>
      )}

      {expanded && !outfits && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-5 shadow-soft space-y-4"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-lg text-ink-900">✨ Outfit-Generator</h3>
            <button
              onClick={() => setExpanded(false)}
              className="text-ink-700/50 hover:text-ink-900 text-2xl leading-none"
            >
              ×
            </button>
          </div>

          <p className="text-sm text-ink-700/70">
            Gib einen Anlass ein und lass die KI 5 verschiedene Outfits aus deiner Garderobe zusammenstellen.
          </p>

          <SelectField
            label="Anlass"
            value={occasion}
            onChange={setOccasion}
            options={meta.occasions}
          />

          {/* Wetter-Chips – optional, ein Tap genügt */}
          <div className="block">
            <div className="flex items-baseline justify-between mb-1.5">
              <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
                Wetter
              </span>
              <span className="text-xs text-ink-700/40">optional</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {WEATHER_OPTIONS.map((w) => {
                const active = weather === w.value;
                return (
                  <button
                    key={w.value}
                    type="button"
                    onClick={() => setWeather(active ? "" : w.value)}
                    className={`rounded-full px-3 py-1.5 text-xs font-medium transition flex items-center gap-1 ${
                      active
                        ? "bg-clay-500 text-white"
                        : "bg-sand-100 text-ink-700/70 hover:bg-sand-200"
                    }`}
                  >
                    <span>{w.icon}</span>
                    <span>{w.value}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <TextField
            label="Zusatzwunsch (optional)"
            value={note}
            onChange={setNote}
            placeholder="z.B. etwas wärmer, elegant, sportlich..."
          />

          {error && (
            <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2">
              {error}
            </div>
          )}

          <button
            onClick={generate}
            disabled={loading}
            className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <motion.span
                  className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                />
                KI generiert Outfits...
              </>
            ) : (
              "✨ 5 Outfits generieren"
            )}
          </button>
        </motion.div>
      )}

      {outfits && outfits.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-5 shadow-soft space-y-5"
        >
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-lg text-ink-900">
              Deine Outfits für {occasion || "heute"}
              {weather ? ` · ${weather.split("(")[0].trim()}` : ""}
            </h3>
            <button
              onClick={reset}
              className="text-sm text-ink-700/60 hover:text-ink-900 transition"
            >
              Neue Outfits
            </button>
          </div>

          <div className="space-y-6">
            {outfits.map((outfit, idx) => (
              <OutfitCard
                key={idx}
                outfit={outfit}
                idx={idx}
                occasion={occasion}
                onItemClick={onItemClick}
                onWatchClick={onWatchClick}
                onFragranceClick={onFragranceClick}
                useAiImages={useAiImages}
              />
            ))}
          </div>
        </motion.div>
      )}

      {outfits && outfits.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-5 shadow-soft text-center"
        >
          <p className="text-ink-700/60 mb-4">
            Die KI konnte keine passenden Outfits aus deiner Garderobe zusammenstellen.
            Vielleicht fehlen noch ein paar Teile?
          </p>
          <button
            onClick={reset}
            className="text-sm text-clay-600 hover:underline"
          >
            Nochmal versuchen
          </button>
        </motion.div>
      )}
    </div>
  );
}

// Vorschau-URL eines Vorschlags. In Outfit-Vorschlägen wird das KI-inszenierte
// Bild bevorzugt: einheitliche Studiofotos lassen eine Kombination als Ganzes
// erkennen, gemischte Handyaufnahmen wirken unruhig.
function suggestionThumb(entry, useAiImages) {
  if (entry.has_ai_image) {
    return entry.ai_thumbnail_url || entry.ai_image_url;
  }
  return entry.thumbnail_url || entry.image_url;
}

// Uhr oder Duft als Zeile unter dem Outfit
function ExtraRow({ label, icon, entry, onClick, useAiImages }) {
  if (!entry) return null;
  return (
    <button
      onClick={() => onClick?.(entry.watch_id ?? entry.fragrance_id)}
      className="w-full flex items-center gap-3 text-left rounded-xl bg-sand-50 p-2.5 hover:bg-sand-100 transition"
    >
      <img
        src={suggestionThumb(entry, useAiImages)}
        alt={entry.name}
        className="w-12 h-12 rounded-lg object-cover flex-shrink-0 bg-white"
      />
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-medium uppercase tracking-wide text-ink-700/40">
          {icon} {label}
        </p>
        <p className="text-sm font-medium text-ink-900 truncate">
          {entry.brand ? `${entry.brand} ${entry.name}` : entry.name}
        </p>
        {entry.reason && (
          <p className="text-xs text-ink-700/60 leading-snug mt-0.5">{entry.reason}</p>
        )}
      </div>
    </button>
  );
}

// Einzelnes Outfit mit optionaler KI-Anprobe
function OutfitCard({
  outfit,
  idx,
  occasion,
  onItemClick,
  onWatchClick,
  onFragranceClick,
  useAiImages,
}) {
  const [tryon, setTryon] = useState(null); // { base64, mime }
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function showTryon() {
    setBusy(true);
    setErr("");
    try {
      const ids = outfit.items.map((it) => it.id);
      const res = await api.outfitTryon(ids, occasion);
      setTryon({ base64: res.image_base64, mime: res.image_mime });
    } catch (e) {
      setErr(e.message || "Anprobe fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.1 }}
      className="border border-sand-200 rounded-2xl p-4 space-y-3"
    >
      <div>
        <h4 className="font-semibold text-ink-900">{outfit.title}</h4>
        <p className="text-sm text-ink-700/70 mt-1">{outfit.why}</p>
      </div>

      {/* KI-Anprobe */}
      <AnimatePresence>
        {tryon && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="relative rounded-2xl overflow-hidden"
          >
            <img
              src={`data:${tryon.mime};base64,${tryon.base64}`}
              alt="KI-Anprobe"
              className="w-full object-cover"
            />
            <span className="absolute top-2 left-2 bg-clay-500/90 text-white text-[10px] font-medium rounded-full px-2 py-0.5 backdrop-blur-md">
              ✨ KI-Anprobe
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
        {outfit.items.map((item) => (
          <button
            key={item.id}
            onClick={() => onItemClick?.(item.id)}
            className="group text-center"
          >
            <div className="aspect-square rounded-xl overflow-hidden bg-sand-50 shadow-sm">
              <img
                src={suggestionThumb(item, useAiImages)}
                alt={item.name}
                className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
              />
            </div>
            <span className="mt-1.5 block text-xs text-ink-700/60 truncate">
              {item.category}
            </span>
          </button>
        ))}
      </div>

      {/* Uhr und Duft zum Look */}
      {(outfit.watch || outfit.fragrance) && (
        <div className="space-y-2">
          <ExtraRow
            label="Passende Uhr"
            icon="⌚"
            entry={outfit.watch}
            onClick={onWatchClick}
            useAiImages={useAiImages}
          />
          <ExtraRow
            label="Passender Duft"
            icon="🧴"
            entry={outfit.fragrance}
            onClick={onFragranceClick}
            useAiImages={useAiImages}
          />
        </div>
      )}

      {err && (
        <div className="rounded-xl bg-clay-500/10 text-clay-600 text-xs px-3 py-2">{err}</div>
      )}

      {/* Anprobe-Button (kostet ~3-4 Cent, daher nur auf Klick) */}
      <button
        onClick={showTryon}
        disabled={busy}
        className="w-full flex items-center justify-center gap-2 rounded-xl border border-clay-400 bg-clay-500/5 text-clay-600 text-sm font-medium py-2.5 hover:bg-clay-500/10 transition disabled:opacity-60"
      >
        {busy ? (
          <>
            <motion.span
              className="inline-block w-4 h-4 border-2 border-clay-500 border-t-transparent rounded-full"
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
            />
            Anprobe wird erstellt …
          </>
        ) : tryon ? (
          "🔄 Neue Anprobe generieren"
        ) : (
          "✨ Anprobe zeigen (KI-Bild)"
        )}
      </button>
    </motion.div>
  );
}
