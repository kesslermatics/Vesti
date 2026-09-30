/**
 * SavedOutfits – Tab-Inhalt der gespeicherten Outfits.
 * Zeigt alle Outfits mit Filter nach Anlass/Saison/Wetter.
 * Öffnet OutfitBuilder zum Bearbeiten.
 */

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";
import OutfitBuilder from "./OutfitBuilder";

function pickThumb(item, useAiImages) {
  if (!item) return "";
  if (useAiImages && item.has_ai_image) {
    return item.ai_thumbnail_url || item.ai_image_url || item.thumbnail_url;
  }
  return item.thumbnail_url || item.image_url || "";
}

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

function Tag({ label, color = "sand" }) {
  const cls =
    color === "clay"
      ? "bg-clay-500/10 text-clay-600"
      : color === "emerald"
      ? "bg-emerald-50 text-emerald-700"
      : "bg-sand-100 text-ink-700/60";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-[11px] font-medium ${cls}`}>
      {label}
    </span>
  );
}

function OutfitCard({ outfit, useAiImages, onEdit, onDelete }) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!confirm(`Outfit „${outfit.title}" wirklich löschen?`)) return;
    setDeleting(true);
    try {
      await api.deleteSavedOutfit(outfit.id);
      onDelete(outfit.id);
    } catch {
      setDeleting(false);
    }
  }

  const score = outfit.ai_rating?.score;
  const scoreColor =
    score == null ? "" : score >= 75 ? "text-emerald-600" : score >= 50 ? "text-amber-500" : "text-clay-500";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className="bg-white rounded-2xl shadow-soft overflow-hidden"
    >
      {/* Item-Thumbnails */}
      <div className="flex gap-1 p-3 pb-2">
        {outfit.items.slice(0, 5).map((item) => (
          <div key={item.id} className="flex-1 aspect-square rounded-xl overflow-hidden bg-sand-50 min-w-0">
            <img
              src={pickThumb(item, useAiImages)}
              alt={item.name}
              className="w-full h-full object-cover"
            />
          </div>
        ))}
        {outfit.items.length > 5 && (
          <div className="flex-1 aspect-square rounded-xl bg-sand-100 flex items-center justify-center text-xs font-medium text-ink-700/50 min-w-0">
            +{outfit.items.length - 5}
          </div>
        )}
        {outfit.items.length === 0 && (
          <div className="w-full h-20 rounded-xl bg-sand-50 flex items-center justify-center text-ink-700/30 text-sm">
            Keine Teile
          </div>
        )}
      </div>

      <div className="px-4 pb-4 space-y-2.5">
        {/* Titel + Score */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-ink-900 truncate">{outfit.title || "Outfit"}</h3>
            {outfit.description && (
              <p className="text-xs text-ink-700/60 mt-0.5 line-clamp-2">{outfit.description}</p>
            )}
          </div>
          {score != null && (
            <span className={`text-sm font-bold tabular-nums flex-shrink-0 ${scoreColor}`}>{score}</span>
          )}
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5">
          {outfit.occasion && <Tag label={outfit.occasion} color="clay" />}
          {outfit.season && <Tag label={outfit.season} />}
          {outfit.weather && <Tag label={outfit.weather} />}
          {(outfit.tags || [])
            .filter((t) => t !== outfit.occasion && t !== outfit.season && t !== outfit.weather)
            .map((t) => <Tag key={t} label={t} />)}
        </div>

        {/* Extras-Zeile */}
        {(outfit.watch || outfit.fragrance || outfit.accessory) && (
          <div className="flex gap-2 flex-wrap">
            {outfit.watch && (
              <div className="flex items-center gap-1 text-[11px] text-ink-700/50">
                <img src={pickThumb(outfit.watch, useAiImages)} className="w-5 h-5 rounded-md object-cover" alt="" />
                <span className="truncate max-w-[80px]">{outfit.watch.name || outfit.watch.brand}</span>
              </div>
            )}
            {outfit.accessory && (
              <div className="flex items-center gap-1 text-[11px] text-ink-700/50">
                <img src={pickThumb(outfit.accessory, useAiImages)} className="w-5 h-5 rounded-md object-cover" alt="" />
                <span className="truncate max-w-[80px]">{outfit.accessory.name || outfit.accessory.type}</span>
              </div>
            )}
            {outfit.fragrance && (
              <div className="flex items-center gap-1 text-[11px] text-ink-700/50">
                <img src={pickThumb(outfit.fragrance, useAiImages)} className="w-5 h-5 rounded-md object-cover" alt="" />
                <span className="truncate max-w-[80px]">{[outfit.fragrance.brand, outfit.fragrance.name].filter(Boolean).join(" ")}</span>
              </div>
            )}
          </div>
        )}

        {/* Aktionen */}
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => onEdit(outfit)}
            className="flex-1 rounded-xl border border-sand-200 text-sm text-ink-700/70 py-2 hover:bg-sand-50 transition font-medium"
          >
            Bearbeiten
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="rounded-xl border border-sand-200 text-sm text-clay-500 px-4 py-2 hover:bg-clay-500/5 transition"
          >
            {deleting ? "…" : "Löschen"}
          </button>
        </div>
      </div>
    </motion.div>
  );
}

export default function SavedOutfits({
  items,
  watches,
  fragrances,
  accessories,
  meta,
  useAiImages,
}) {
  const [outfits, setOutfits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState(""); // Anlass-Filter
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editPrefill, setEditPrefill] = useState(null);

  useEffect(() => {
    api.listSavedOutfits()
      .then(setOutfits)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function handleSaved(outfit) {
    setOutfits((prev) => {
      const exists = prev.some((o) => o.id === outfit.id);
      return exists
        ? prev.map((o) => (o.id === outfit.id ? outfit : o))
        : [outfit, ...prev];
    });
  }

  function handleDelete(id) {
    setOutfits((prev) => prev.filter((o) => o.id !== id));
  }

  function openNew() {
    setEditPrefill(null);
    setBuilderOpen(true);
  }

  function openEdit(outfit) {
    setEditPrefill({
      _editId: outfit.id,
      item_ids: (outfit.items || []).map((i) => i.id),
      watch_id: outfit.watch?.id || null,
      fragrance_id: outfit.fragrance?.id || null,
      accessory_id: outfit.accessory?.id || null,
      occasion: outfit.occasion,
      season: outfit.season,
      weather: outfit.weather,
      title: outfit.title,
      why: outfit.description,
    });
    setBuilderOpen(true);
  }

  // Alle verfügbaren Anlass-Tags aus gespeicherten Outfits sammeln
  const allOccasions = [...new Set(outfits.map((o) => o.occasion).filter(Boolean))];

  const filtered = filter
    ? outfits.filter(
        (o) =>
          o.occasion === filter ||
          o.season === filter ||
          o.weather === filter ||
          (o.tags || []).includes(filter)
      )
    : outfits;

  return (
    <>
      <div className="space-y-5">
        {error && (
          <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3">{error}</div>
        )}

        {/* Filter-Chips */}
        {allOccasions.length > 1 && (
          <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
            <button
              onClick={() => setFilter("")}
              className={`flex-shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition ${
                !filter ? "bg-clay-500 text-white" : "bg-sand-100 text-ink-700/70 hover:bg-sand-200"
              }`}
            >
              Alle
            </button>
            {allOccasions.map((o) => (
              <button
                key={o}
                onClick={() => setFilter(filter === o ? "" : o)}
                className={`flex-shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition ${
                  filter === o ? "bg-clay-500 text-white" : "bg-sand-100 text-ink-700/70 hover:bg-sand-200"
                }`}
              >
                {o}
              </button>
            ))}
          </div>
        )}

        {loading && <Spinner />}

        {!loading && outfits.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <div className="text-5xl mb-4">👔</div>
            <h2 className="text-lg font-semibold text-ink-900">Noch keine Outfits</h2>
            <p className="text-sm text-ink-700/60 mt-1 max-w-xs mx-auto">
              Stelle dein erstes Outfit zusammen oder exportiere einen Vorschlag vom Generator.
            </p>
            <button
              onClick={openNew}
              className="mt-5 rounded-xl bg-clay-500 text-white font-medium px-5 py-2.5 hover:bg-clay-600 transition"
            >
              + Outfit erstellen
            </button>
          </motion.div>
        )}

        {!loading && outfits.length > 0 && filtered.length === 0 && (
          <div className="text-center py-10 text-sm text-ink-700/50">
            Kein Outfit passt zu diesem Filter.
          </div>
        )}

        <AnimatePresence>
          {filtered.map((outfit) => (
            <OutfitCard
              key={outfit.id}
              outfit={outfit}
              useAiImages={useAiImages}
              onEdit={openEdit}
              onDelete={handleDelete}
            />
          ))}
        </AnimatePresence>

        {/* Spacer für FAB */}
        <div className="h-20" />
      </div>

      {/* OutfitBuilder */}
      <OutfitBuilder
        open={builderOpen}
        onClose={() => setBuilderOpen(false)}
        onSaved={handleSaved}
        items={items}
        watches={watches}
        fragrances={fragrances}
        accessories={accessories}
        meta={meta}
        useAiImages={useAiImages}
        prefill={editPrefill}
      />
    </>
  );
}
