import { useState } from "react";
import { motion } from "framer-motion";
import { api } from "../api";
import Modal from "./Modal";
import { SelectField, TextField } from "./Field";

export default function ItemDetail({ item, meta, onClose, onDeleted, onUpdated }) {
  const [occasion, setOccasion] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [qtyBusy, setQtyBusy] = useState(false);

  const open = Boolean(item);

  async function changeQty(delta) {
    const next = Math.max(1, (item.quantity || 1) + delta);
    if (next === (item.quantity || 1)) return;
    setQtyBusy(true);
    try {
      const updated = await api.updateQuantity(item.id, next);
      onUpdated?.(updated);
    } catch (err) {
      setError(err.message || "Stückzahl konnte nicht geändert werden.");
    } finally {
      setQtyBusy(false);
    }
  }

  async function getRecommendation() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.recommend({ item_id: item.id, occasion, note });
      setResult(res);
    } catch (err) {
      setError(err.message || "Empfehlung fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  async function remove() {
    if (!confirm("Dieses Teil wirklich löschen?")) return;
    try {
      await api.deleteItem(item.id);
      onDeleted(item.id);
    } catch (err) {
      setError(err.message || "Löschen fehlgeschlagen.");
    }
  }

  function handleClose() {
    setOccasion("");
    setNote("");
    setResult(null);
    setError("");
    onClose();
  }

  return (
    <Modal open={open} onClose={handleClose}>
      {item && (
        <div className="p-5 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-ink-900">
              {item.name || item.category}
            </h2>
            <button onClick={handleClose} className="text-ink-700/50 hover:text-ink-900 text-2xl leading-none">
              ×
            </button>
          </div>

          <img
            src={item.image_url}
            alt={item.name}
            className="w-full aspect-[4/3] object-cover rounded-2xl mb-4"
          />

          <div className="flex flex-wrap gap-2 mb-4">
            {[item.category, item.color, item.style, item.material, item.season, item.brand]
              .filter(Boolean)
              .map((tag, i) => (
                <span key={i} className="text-xs bg-sand-100 text-ink-700 rounded-full px-3 py-1">
                  {tag}
                </span>
              ))}
          </div>

          {/* Stückzahl */}
          <div className="flex items-center justify-between bg-sand-100 rounded-2xl px-4 py-3 mb-4">
            <div>
              <span className="text-sm font-medium text-ink-900">Stückzahl</span>
              <p className="text-xs text-ink-700/50">
                Wie viele davon besitzt du?
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => changeQty(-1)}
                disabled={qtyBusy || (item.quantity || 1) <= 1}
                aria-label="Weniger"
                className="w-8 h-8 rounded-full bg-white text-ink-800 shadow-sm text-lg leading-none disabled:opacity-40 hover:bg-sand-50 transition"
              >
                −
              </button>
              <span className="w-8 text-center font-semibold text-ink-900">
                {item.quantity || 1}
              </span>
              <button
                onClick={() => changeQty(1)}
                disabled={qtyBusy}
                aria-label="Mehr"
                className="w-8 h-8 rounded-full bg-white text-ink-800 shadow-sm text-lg leading-none disabled:opacity-40 hover:bg-sand-50 transition"
              >
                +
              </button>
            </div>
          </div>

          {/* Spezifische Details */}
          {item.details && Object.keys(item.details).length > 0 && (
            <div className="mb-5">
              <h3 className="text-xs font-semibold text-ink-700/70 uppercase tracking-wide mb-2">
                Details
              </h3>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                {Object.entries(item.details)
                  .filter(([, v]) => v)
                  .map(([k, v]) => (
                    <div key={k} className="text-sm">
                      <span className="text-ink-700/50 capitalize">
                        {k.replace(/_/g, " ")}:{" "}
                      </span>
                      <span className="text-ink-900">{v}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {!result && (
            <div className="space-y-3">
              <p className="text-sm text-ink-700/70">
                Wofür möchtest du dieses Teil kombinieren? Vesti stellt ein Outfit aus deiner Garderobe zusammen.
              </p>
              <SelectField label="Anlass" value={occasion} onChange={setOccasion} options={meta.occasions} />
              <TextField
                label="Zusatzwunsch (optional)"
                value={note}
                onChange={setNote}
                placeholder="z.B. wird kühl abends, eher dezent …"
              />
              <button
                onClick={getRecommendation}
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
                    Vesti stylt …
                  </>
                ) : (
                  "✨ Outfit vorschlagen"
                )}
              </button>
            </div>
          )}

          {error && (
            <div className="mt-3 rounded-xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2">
              {error}
            </div>
          )}

          {result && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              {/* Tauglichkeits-Urteil */}
              {(() => {
                const cfg = {
                  perfekt:    { bg: "bg-emerald-50",  text: "text-emerald-700", border: "border-emerald-200", icon: "✓" },
                  geht:       { bg: "bg-sand-100",    text: "text-ink-700",     border: "border-sand-200",    icon: "~" },
                  notlösung:  { bg: "bg-amber-50",    text: "text-amber-700",   border: "border-amber-200",   icon: "⚠" },
                  ungeeignet: { bg: "bg-clay-500/10", text: "text-clay-700",    border: "border-clay-200",    icon: "✕" },
                }[result.suitability] || cfg.geht;
                return (
                  <div className={`rounded-2xl border ${cfg.bg} ${cfg.border} px-4 py-3 flex gap-3 items-start`}>
                    <span className={`text-lg font-bold ${cfg.text} shrink-0`}>{cfg.icon}</span>
                    <div>
                      <p className={`text-sm font-semibold capitalize ${cfg.text}`}>
                        {result.suitability}
                      </p>
                      {result.suitability_reason && (
                        <p className={`text-sm mt-0.5 ${cfg.text} opacity-80`}>
                          {result.suitability_reason}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })()}

              <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide">
                Dein Outfit
              </h3>
              <div className="grid grid-cols-3 gap-3">
                {result.pieces.map((p) => (
                  <div key={p.item_id} className="text-center">
                    <img
                      src={p.image_url}
                      alt={p.name}
                      className="w-full aspect-square object-cover rounded-xl shadow-soft"
                    />
                    <span className="mt-1 block text-xs text-ink-700/70 truncate">{p.name}</span>
                  </div>
                ))}
              </div>
              <div className="rounded-2xl bg-sand-100 p-4 text-sm text-ink-800 leading-relaxed">
                {result.explanation}
              </div>
              <button
                onClick={() => setResult(null)}
                className="w-full rounded-xl border border-sand-200 text-ink-700 font-medium py-2.5 hover:bg-sand-100 transition"
              >
                Neuer Vorschlag
              </button>
            </motion.div>
          )}

          <button
            onClick={remove}
            className="mt-5 w-full text-center text-sm text-ink-700/50 hover:text-clay-600 transition"
          >
            Teil löschen
          </button>
        </div>
      )}
    </Modal>
  );
}
