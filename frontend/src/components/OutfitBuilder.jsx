/**
 * OutfitBuilder – Outfit manuell zusammenstellen oder aus einem Vorschlag importieren.
 * Wird als Fullscreen-Overlay geöffnet.
 *
 * Props:
 *   open          – boolean
 *   onClose       – () => void
 *   onSaved       – (outfit) => void  – nach erfolgreichem Speichern
 *   items         – ClothingItem[]    – alle Kleidungsstücke des Nutzers
 *   watches       – Watch[]
 *   fragrances    – Fragrance[]
 *   accessories   – Accessory[]
 *   meta          – API-Meta-Objekt (occasions, seasons, …)
 *   useAiImages   – boolean
 *   prefill       – optional: { item_ids, watch_id, fragrance_id, accessory_id, occasion, season, weather, title, why }
 *                   Befüllt den Builder mit einem Vorschlag vom Outfit-Generator
 */

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";

// ── Hilfsfunktionen ──────────────────────────────────────────────────

function pickThumb(item, useAiImages) {
  if (useAiImages && item?.has_ai_image) {
    return item.ai_thumbnail_url || item.ai_image_url || item.thumbnail_url;
  }
  return item?.thumbnail_url || item?.image_url || "";
}

function Spinner({ className = "w-4 h-4 border-clay-500" }) {
  return (
    <motion.span
      className={`inline-block border-2 border-t-transparent rounded-full ${className}`}
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
    />
  );
}

// ── KI-Bewertungs-Popup ──────────────────────────────────────────────

function RatingPopup({ rating, onClose }) {
  const score = rating?.score ?? 0;
  const color =
    score >= 75 ? "text-emerald-600" : score >= 50 ? "text-amber-500" : "text-clay-500";
  const ring =
    score >= 75 ? "stroke-emerald-500" : score >= 50 ? "stroke-amber-400" : "stroke-clay-500";

  const circumference = 2 * Math.PI * 22;
  const dash = (score / 100) * circumference;

  return (
    <motion.div
      className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="absolute inset-0 bg-ink-900/50 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        className="relative w-full sm:max-w-sm bg-white rounded-t-3xl sm:rounded-3xl shadow-xl p-6 space-y-5"
        style={{ paddingBottom: "max(env(safe-area-inset-bottom), 1.5rem)" }}
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", stiffness: 320, damping: 32 }}
      >
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-ink-900 text-lg">KI-Bewertung</h3>
          <button onClick={onClose} className="text-ink-700/40 hover:text-ink-900 text-2xl leading-none">×</button>
        </div>

        {/* Score Ring */}
        <div className="flex flex-col items-center gap-2">
          <div className="relative w-20 h-20">
            <svg className="w-20 h-20 -rotate-90" viewBox="0 0 50 50">
              <circle cx="25" cy="25" r="22" fill="none" stroke="#f0ece8" strokeWidth="4" />
              <motion.circle
                cx="25" cy="25" r="22" fill="none" strokeWidth="4"
                className={ring}
                strokeLinecap="round"
                strokeDasharray={`${circumference}`}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset: circumference - dash }}
                transition={{ duration: 0.8, ease: "easeOut" }}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`text-xl font-bold tabular-nums ${color}`}>{score}</span>
            </div>
          </div>
          <p className="text-sm font-medium text-ink-900 text-center">{rating?.verdict}</p>
        </div>

        {/* Stärken */}
        {rating?.strengths?.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600">Was gut funktioniert</p>
            {rating.strengths.map((s, i) => (
              <div key={i} className="flex gap-2 text-sm text-ink-800">
                <span className="text-emerald-500 shrink-0">✓</span>
                <span>{s}</span>
              </div>
            ))}
          </div>
        )}

        {/* Hinweise */}
        {rating?.suggestions?.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-500">Hinweise</p>
            {rating.suggestions.map((s, i) => (
              <div key={i} className="flex gap-2 text-sm text-ink-800">
                <span className="text-amber-400 shrink-0">→</span>
                <span>{s}</span>
              </div>
            ))}
          </div>
        )}

        {/* Summary */}
        {rating?.summary && (
          <p className="text-sm text-ink-700/70 leading-relaxed border-t border-sand-100 pt-4">
            {rating.summary}
          </p>
        )}
      </motion.div>
    </motion.div>
  );
}

// ── Item-Auswahl-Sheet ───────────────────────────────────────────────

function ItemPickerSheet({ open, onClose, items, selectedIds, onToggle, useAiImages }) {
  const [q, setQ] = useState("");
  const filtered = q.trim()
    ? items.filter((it) => {
        const s = [it.name, it.category, it.color, it.brand, it.material]
          .filter(Boolean).join(" ").toLowerCase();
        return q.toLowerCase().split(/\s+/).every((t) => s.includes(t));
      })
    : items;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[55] flex flex-col bg-white"
          style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
          initial={{ y: "100%" }}
          animate={{ y: 0 }}
          exit={{ y: "100%" }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
          {/* Header */}
          <div className="flex-shrink-0 px-5 pt-5 pb-3 border-b border-sand-100 flex items-center gap-3">
            <button onClick={onClose} className="text-ink-700/50 hover:text-ink-900 text-2xl leading-none">×</button>
            <h2 className="font-semibold text-ink-900">Kleidung auswählen</h2>
            <span className="ml-auto text-xs text-ink-700/40">{selectedIds.length} gewählt</span>
          </div>
          {/* Suche */}
          <div className="flex-shrink-0 px-5 py-3">
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Suchen…"
              className="w-full rounded-xl border border-sand-200 px-4 py-2.5 text-sm focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none"
            />
          </div>
          {/* Grid */}
          <div className="flex-1 overflow-y-auto px-5 pb-4">
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
              {filtered.map((item) => {
                const selected = selectedIds.includes(item.id);
                return (
                  <button
                    key={item.id}
                    onClick={() => onToggle(item.id)}
                    className={`relative rounded-2xl overflow-hidden aspect-square border-2 transition ${
                      selected ? "border-clay-500 ring-2 ring-clay-500/30" : "border-transparent"
                    }`}
                  >
                    <img
                      src={pickThumb(item, useAiImages)}
                      alt={item.name}
                      className="w-full h-full object-cover"
                    />
                    {selected && (
                      <div className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-clay-500 flex items-center justify-center shadow">
                        <svg viewBox="0 0 16 16" fill="white" className="w-3 h-3">
                          <path fillRule="evenodd" d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z" clipRule="evenodd" />
                        </svg>
                      </div>
                    )}
                    <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/60 to-transparent px-1.5 py-1">
                      <p className="text-[10px] text-white truncate leading-tight">{item.name || item.category}</p>
                    </div>
                  </button>
                );
              })}
            </div>
            {filtered.length === 0 && (
              <p className="text-center text-sm text-ink-700/40 py-10">Keine Treffer</p>
            )}
          </div>
          {/* Confirm */}
          <div className="flex-shrink-0 px-5 py-4 border-t border-sand-100">
            <button
              onClick={onClose}
              className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 transition"
            >
              {selectedIds.length} Teil{selectedIds.length !== 1 ? "e" : ""} übernehmen
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ── Haupt-Komponente ─────────────────────────────────────────────────

export default function OutfitBuilder({
  open,
  onClose,
  onSaved,
  items = [],
  watches = [],
  fragrances = [],
  accessories = [],
  meta,
  useAiImages = false,
  prefill = null,
}) {
  // Outfit-Daten
  const [selectedItemIds, setSelectedItemIds] = useState([]);
  const [selectedWatchId, setSelectedWatchId] = useState(null);
  const [selectedFragranceId, setSelectedFragranceId] = useState(null);
  const [selectedAccessoryId, setSelectedAccessoryId] = useState(null);
  const [occasion, setOccasion] = useState("");
  const [season, setSeason] = useState("");
  const [weather, setWeather] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  // UI-State
  const [pickerOpen, setPickerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [rating, setRating] = useState(null);
  const [ratingOpen, setRatingOpen] = useState(false);
  const [rating_loading, setRatingLoading] = useState(false);
  const [error, setError] = useState("");
  const [savedId, setSavedId] = useState(null); // ID des bereits gespeicherten Outfits (für Rate-Call)

  // Prefill wenn ein Vorschlag exportiert wird
  useEffect(() => {
    if (!open) return;
    if (prefill) {
      setSelectedItemIds(prefill.item_ids || []);
      setSelectedWatchId(prefill.watch_id || null);
      setSelectedFragranceId(prefill.fragrance_id || null);
      setSelectedAccessoryId(prefill.accessory_id || null);
      setOccasion(prefill.occasion || "");
      setSeason(prefill.season || "");
      setWeather(prefill.weather || "");
      setTitle(prefill.title || "");
      setDescription(prefill.why || prefill.description || "");
      // Bei Bearbeitung: bekannte ID vorausfüllen damit save() kein Duplikat erzeugt
      setSavedId(prefill._editId || null);
    } else {
      // Reset
      setSelectedItemIds([]);
      setSelectedWatchId(null);
      setSelectedFragranceId(null);
      setSelectedAccessoryId(null);
      setOccasion("");
      setSeason("");
      setWeather("");
      setTitle("");
      setDescription("");
    }
    setRating(null);
    setSavedId(null);
    setError("");
  }, [open, prefill]);

  function toggleItem(id) {
    setSelectedItemIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  }

  const selectedItems = selectedItemIds
    .map((id) => items.find((it) => it.id === id))
    .filter(Boolean);

  const currentWatch = watches.find((w) => w.id === selectedWatchId) || null;
  const currentFragrance = fragrances.find((f) => f.id === selectedFragranceId) || null;
  const currentAccessory = accessories.find((a) => a.id === selectedAccessoryId) || null;

  const payload = {
    item_ids: selectedItemIds,
    watch_id: selectedWatchId,
    fragrance_id: selectedFragranceId,
    accessory_id: selectedAccessoryId,
    occasion,
    season,
    weather,
    title: title.trim(),
    description: description.trim(),
  };

  async function save() {
    if (selectedItemIds.length === 0) {
      setError("Wähle mindestens ein Kleidungsstück aus.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const saved = savedId
        ? await api.updateSavedOutfit(savedId, payload)
        : await api.createSavedOutfit(payload);
      setSavedId(saved.id);
      if (!title) setTitle(saved.title);
      if (!description) setDescription(saved.description || "");
      onSaved(saved);
      onClose();
    } catch (e) {
      setError(e.message || "Speichern fehlgeschlagen.");
    } finally {
      setSaving(false);
    }
  }

  async function rateOutfit() {
    // Zuerst speichern/updaten falls nötig
    let idToRate = savedId;
    if (!idToRate) {
      if (selectedItemIds.length === 0) {
        setError("Wähle mindestens ein Kleidungsstück aus.");
        return;
      }
      setSaving(true);
      setError("");
      try {
        const saved = await api.createSavedOutfit(payload);
        idToRate = saved.id;
        setSavedId(saved.id);
        if (!title) setTitle(saved.title);
        if (!description) setDescription(saved.description || "");
        onSaved(saved);
      } catch (e) {
        setError(e.message || "Speichern fehlgeschlagen.");
        setSaving(false);
        return;
      } finally {
        setSaving(false);
      }
    }

    setRatingLoading(true);
    try {
      const result = await api.rateSavedOutfit(idToRate);
      setRating(result);
      setRatingOpen(true);
    } catch (e) {
      setError(e.message || "Bewertung fehlgeschlagen.");
    } finally {
      setRatingLoading(false);
    }
  }

  const occasions = meta?.occasions || [];
  const seasons = meta?.seasons || [];

  const WEATHER_OPTIONS = [
    { value: "warm und sonnig", icon: "☀️" },
    { value: "angenehm", icon: "🌤️" },
    { value: "kühl", icon: "🌥️" },
    { value: "kalt", icon: "🧊" },
    { value: "regnerisch", icon: "🌧️" },
  ];

  return (
    <>
      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-50 flex flex-col bg-sand-50"
            style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={{ duration: 0.22 }}
          >
            {/* Header */}
            <div
              className="flex-shrink-0 px-5 pb-4 border-b border-sand-100 bg-sand-50/90 backdrop-blur-md flex items-center gap-3"
              style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
            >
              <button onClick={onClose} className="text-ink-700/50 hover:text-ink-900 text-2xl leading-none mr-1">×</button>
              <h2 className="font-bold text-ink-900 text-lg flex-1">Outfit zusammenstellen</h2>
              <button
                onClick={save}
                disabled={saving || selectedItemIds.length === 0}
                className="rounded-xl bg-clay-500 text-white text-sm font-medium px-4 py-2 hover:bg-clay-600 transition disabled:opacity-40 flex items-center gap-1.5"
              >
                {saving ? <Spinner className="w-3.5 h-3.5 border-white" /> : null}
                Speichern
              </button>
            </div>

            {/* Scroll-Content */}
            <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">

              {error && (
                <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3">{error}</div>
              )}

              {/* ── Kleidung ── */}
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-ink-900">Kleidung</h3>
                  <button
                    onClick={() => setPickerOpen(true)}
                    className="text-sm text-clay-500 font-medium hover:text-clay-600 transition"
                  >
                    + Teile auswählen
                  </button>
                </div>

                {selectedItems.length === 0 ? (
                  <button
                    onClick={() => setPickerOpen(true)}
                    className="w-full rounded-2xl border-2 border-dashed border-sand-200 py-10 flex flex-col items-center gap-2 text-ink-700/40 hover:border-clay-400 hover:text-clay-500 transition"
                  >
                    <span className="text-3xl">👕</span>
                    <span className="text-sm">Teile antippen zum Hinzufügen</span>
                  </button>
                ) : (
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                    {selectedItems.map((item) => (
                      <div key={item.id} className="relative">
                        <button
                          onClick={() => setPickerOpen(true)}
                          className="w-full aspect-square rounded-2xl overflow-hidden bg-sand-100"
                        >
                          <img
                            src={pickThumb(item, useAiImages)}
                            alt={item.name}
                            className="w-full h-full object-cover"
                          />
                        </button>
                        <button
                          onClick={() => toggleItem(item.id)}
                          className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-ink-900 text-white text-xs leading-none flex items-center justify-center shadow"
                        >
                          ×
                        </button>
                        <p className="text-[10px] text-ink-700/60 truncate mt-1 text-center">
                          {item.name || item.category}
                        </p>
                      </div>
                    ))}
                    <button
                      onClick={() => setPickerOpen(true)}
                      className="aspect-square rounded-2xl border-2 border-dashed border-sand-200 flex items-center justify-center text-ink-700/30 hover:border-clay-400 hover:text-clay-500 transition text-2xl"
                    >
                      +
                    </button>
                  </div>
                )}
              </section>

              {/* ── Extras ── */}
              {(watches.length > 0 || fragrances.length > 0 || accessories.length > 0) && (
                <section className="space-y-3">
                  <h3 className="text-sm font-semibold text-ink-900">Extras</h3>
                  <div className="space-y-2">

                    {/* Uhr */}
                    {watches.length > 0 && (
                      <div className="bg-white rounded-2xl border border-sand-100 p-3 flex items-center gap-3">
                        {currentWatch ? (
                          <>
                            <img
                              src={pickThumb(currentWatch, useAiImages)}
                              className="w-12 h-12 rounded-xl object-cover flex-shrink-0"
                              alt={currentWatch.name}
                            />
                            <div className="flex-1 min-w-0">
                              <p className="text-[10px] font-medium uppercase tracking-wide text-ink-700/40">⌚ Uhr</p>
                              <p className="text-sm font-medium text-ink-900 truncate">
                                {currentWatch.name || [currentWatch.brand, currentWatch.model].filter(Boolean).join(" ")}
                              </p>
                            </div>
                            <button onClick={() => setSelectedWatchId(null)} className="text-ink-700/30 hover:text-clay-500 text-lg leading-none">×</button>
                          </>
                        ) : (
                          <select
                            value=""
                            onChange={(e) => setSelectedWatchId(Number(e.target.value) || null)}
                            className="flex-1 text-sm text-ink-700/60 bg-transparent outline-none"
                          >
                            <option value="">⌚ Uhr hinzufügen…</option>
                            {watches.map((w) => (
                              <option key={w.id} value={w.id}>
                                {w.name || [w.brand, w.model].filter(Boolean).join(" ") || "Uhr"}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    )}

                    {/* Accessoire */}
                    {accessories.length > 0 && (
                      <div className="bg-white rounded-2xl border border-sand-100 p-3 flex items-center gap-3">
                        {currentAccessory ? (
                          <>
                            <img
                              src={pickThumb(currentAccessory, useAiImages)}
                              className="w-12 h-12 rounded-xl object-cover flex-shrink-0"
                              alt={currentAccessory.name}
                            />
                            <div className="flex-1 min-w-0">
                              <p className="text-[10px] font-medium uppercase tracking-wide text-ink-700/40">💎 Accessoire</p>
                              <p className="text-sm font-medium text-ink-900 truncate">
                                {currentAccessory.name || currentAccessory.type}
                              </p>
                            </div>
                            <button onClick={() => setSelectedAccessoryId(null)} className="text-ink-700/30 hover:text-clay-500 text-lg leading-none">×</button>
                          </>
                        ) : (
                          <select
                            value=""
                            onChange={(e) => setSelectedAccessoryId(Number(e.target.value) || null)}
                            className="flex-1 text-sm text-ink-700/60 bg-transparent outline-none"
                          >
                            <option value="">💎 Accessoire hinzufügen…</option>
                            {accessories.map((a) => (
                              <option key={a.id} value={a.id}>
                                {a.name || a.type || "Accessoire"}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    )}

                    {/* Duft */}
                    {fragrances.length > 0 && (
                      <div className="bg-white rounded-2xl border border-sand-100 p-3 flex items-center gap-3">
                        {currentFragrance ? (
                          <>
                            <img
                              src={pickThumb(currentFragrance, useAiImages)}
                              className="w-12 h-12 rounded-xl object-cover flex-shrink-0"
                              alt={currentFragrance.name}
                            />
                            <div className="flex-1 min-w-0">
                              <p className="text-[10px] font-medium uppercase tracking-wide text-ink-700/40">🧴 Duft</p>
                              <p className="text-sm font-medium text-ink-900 truncate">
                                {[currentFragrance.brand, currentFragrance.name].filter(Boolean).join(" ")}
                              </p>
                            </div>
                            <button onClick={() => setSelectedFragranceId(null)} className="text-ink-700/30 hover:text-clay-500 text-lg leading-none">×</button>
                          </>
                        ) : (
                          <select
                            value=""
                            onChange={(e) => setSelectedFragranceId(Number(e.target.value) || null)}
                            className="flex-1 text-sm text-ink-700/60 bg-transparent outline-none"
                          >
                            <option value="">🧴 Duft hinzufügen…</option>
                            {fragrances.map((f) => (
                              <option key={f.id} value={f.id}>
                                {[f.brand, f.name].filter(Boolean).join(" ") || "Duft"}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* ── Tags ── */}
              <section className="space-y-4">
                <h3 className="text-sm font-semibold text-ink-900">Tags</h3>

                {/* Anlass */}
                <div>
                  <label className="text-xs font-medium text-ink-700/60 uppercase tracking-wide block mb-1.5">Anlass</label>
                  <div className="flex flex-wrap gap-1.5">
                    {occasions.map((o) => (
                      <button
                        key={o}
                        onClick={() => setOccasion(occasion === o ? "" : o)}
                        className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                          occasion === o
                            ? "bg-clay-500 text-white"
                            : "bg-white border border-sand-200 text-ink-700/70 hover:border-clay-400"
                        }`}
                      >
                        {o}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Saison */}
                <div>
                  <label className="text-xs font-medium text-ink-700/60 uppercase tracking-wide block mb-1.5">Saison</label>
                  <div className="flex flex-wrap gap-1.5">
                    {(seasons.length ? seasons : ["Frühling", "Sommer", "Herbst", "Winter", "ganzjährig"]).map((s) => (
                      <button
                        key={s}
                        onClick={() => setSeason(season === s ? "" : s)}
                        className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                          season === s
                            ? "bg-clay-500 text-white"
                            : "bg-white border border-sand-200 text-ink-700/70 hover:border-clay-400"
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Wetter */}
                <div>
                  <label className="text-xs font-medium text-ink-700/60 uppercase tracking-wide block mb-1.5">Wetter <span className="normal-case text-ink-700/30">(optional)</span></label>
                  <div className="flex flex-wrap gap-1.5">
                    {WEATHER_OPTIONS.map((w) => (
                      <button
                        key={w.value}
                        onClick={() => setWeather(weather === w.value ? "" : w.value)}
                        className={`rounded-full px-3 py-1.5 text-xs font-medium transition flex items-center gap-1 ${
                          weather === w.value
                            ? "bg-clay-500 text-white"
                            : "bg-white border border-sand-200 text-ink-700/70 hover:border-clay-400"
                        }`}
                      >
                        <span>{w.icon}</span><span>{w.value}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </section>

              {/* ── Titel & Beschreibung ── */}
              <section className="space-y-3">
                <h3 className="text-sm font-semibold text-ink-900">Name & Beschreibung</h3>
                <p className="text-xs text-ink-700/50">Wird automatisch von der KI generiert – du kannst es anpassen.</p>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Outfit-Name, z.B. 'Casual Friday'"
                  className="w-full rounded-xl border border-sand-200 bg-white px-4 py-2.5 text-sm focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
                />
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  placeholder="Kurze Beschreibung (optional)…"
                  className="w-full rounded-xl border border-sand-200 bg-white px-4 py-2.5 text-sm focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition resize-none"
                />
              </section>

              {/* ── KI-Bewertung ── */}
              <section className="bg-white rounded-2xl border border-sand-100 p-4 flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-ink-900">✦ KI-Bewertung</p>
                  <p className="text-xs text-ink-700/50 mt-0.5">Stärken erkennen, offensichtliche Schwächen aufdecken</p>
                </div>
                <button
                  onClick={rateOutfit}
                  disabled={rating_loading || selectedItemIds.length === 0}
                  className="flex-shrink-0 rounded-xl bg-sand-100 text-ink-800 text-sm font-medium px-4 py-2 hover:bg-sand-200 transition disabled:opacity-40 flex items-center gap-1.5"
                >
                  {rating_loading ? <Spinner className="w-3.5 h-3.5 border-ink-700" /> : null}
                  {rating ? "Neu bewerten" : "Bewerten"}
                </button>
              </section>

              {/* Erneut bewerten – Ergebnis kurz anzeigen */}
              {rating && !ratingOpen && (
                <button
                  onClick={() => setRatingOpen(true)}
                  className="w-full text-left rounded-2xl bg-white border border-sand-100 px-4 py-3 flex items-center gap-3 hover:bg-sand-50 transition"
                >
                  <div className="w-10 h-10 rounded-full bg-clay-500/10 flex items-center justify-center flex-shrink-0">
                    <span className={`text-sm font-bold ${rating.score >= 75 ? "text-emerald-600" : rating.score >= 50 ? "text-amber-500" : "text-clay-500"}`}>
                      {rating.score}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-ink-700/50">Letzte Bewertung</p>
                    <p className="text-sm text-ink-900 truncate">{rating.verdict}</p>
                  </div>
                  <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 text-ink-700/30 flex-shrink-0">
                    <path fillRule="evenodd" d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06l-3.25 3.25a.75.75 0 0 1-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
                  </svg>
                </button>
              )}

              {/* Spacer für FAB */}
              <div className="h-4" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Item-Picker Sheet */}
      <ItemPickerSheet
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        items={items}
        selectedIds={selectedItemIds}
        onToggle={toggleItem}
        useAiImages={useAiImages}
      />

      {/* KI-Bewertungs-Popup */}
      <AnimatePresence>
        {ratingOpen && rating && (
          <RatingPopup rating={rating} onClose={() => setRatingOpen(false)} />
        )}
      </AnimatePresence>
    </>
  );
}
