import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, fileToBase64 } from "../api";
import { GroupedSelectField, SelectField, TextField } from "./Field";
import BrandField from "./BrandField";

// ---- Bild-Galerie (KI-Foto zuerst, dann eigene Aufnahmen) ----
function ImageGallery({ item }) {
  const baseUrls = item.image_urls?.length ? item.image_urls : [item.image_url];
  const baseThumbs = item.thumbnail_urls?.length
    ? item.thumbnail_urls
    : [item.thumbnail_url || item.image_url];

  const urls = item.has_ai_image ? [item.ai_image_url, ...baseUrls] : baseUrls;
  const thumbUrls = item.has_ai_image
    ? [item.ai_thumbnail_url || item.ai_image_url, ...baseThumbs]
    : baseThumbs;

  const [active, setActive] = useState(0);
  const [fullLoaded, setFullLoaded] = useState(false);
  useEffect(() => { setActive(0); setFullLoaded(false); }, [item.id, urls.length]);

  const idx = Math.min(active, urls.length - 1);
  const fullUrl = urls[idx];
  const thumbUrl = thumbUrls[idx] || fullUrl;
  const isAiActive = item.has_ai_image && idx === 0;

  // Wenn aktives Bild wechselt: Vollbild neu laden
  useEffect(() => { setFullLoaded(false); }, [fullUrl]);

  return (
    <div>
      <div className="relative rounded-3xl overflow-hidden bg-ink-900/5 aspect-square">
        {/* Thumbnail sofort sichtbar als Platzhalter */}
        <img
          src={thumbUrl}
          alt={item.name}
          className="absolute inset-0 w-full h-full object-cover"
          style={{ filter: fullLoaded ? "none" : "blur(2px)", transition: "filter 0.15s" }}
        />
        {/* Vollbild lädt still im Hintergrund */}
        <img
          key={fullUrl}
          src={fullUrl}
          alt={item.name}
          onLoad={() => setFullLoaded(true)}
          className="absolute inset-0 w-full h-full object-cover"
          style={{ opacity: fullLoaded ? 1 : 0, transition: "opacity 0.2s" }}
        />
        {isAiActive && (
          <span className="absolute top-3 left-3 bg-clay-500/90 text-white text-[11px] font-medium rounded-full px-2.5 py-1 backdrop-blur-md shadow-sm">
            ✨ In Szene gesetzt
          </span>
        )}
        {urls.length > 1 && (
          <span className="absolute bottom-3 right-3 bg-ink-900/50 text-white text-xs rounded-full px-2.5 py-1 backdrop-blur-md">
            {idx + 1}/{urls.length}
          </span>
        )}
      </div>

      {urls.length > 1 && (
        <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
          {thumbUrls.map((t, i) => (
            <button
              key={t}
              onClick={() => setActive(i)}
              className={`relative h-16 w-16 flex-shrink-0 rounded-2xl overflow-hidden transition ${
                i === idx ? "ring-2 ring-clay-500" : "opacity-60 hover:opacity-100"
              }`}
            >
              <img src={t} alt={`Ansicht ${i + 1}`} className="w-full h-full object-cover" />
              {item.has_ai_image && i === 0 && (
                <span className="absolute inset-x-0 bottom-0 bg-clay-500/80 text-white text-[8px] text-center leading-tight py-0.5">
                  KI
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---- kleine Glass-Karte ----
function GlassCard({ children, className = "" }) {
  return (
    <div
      className={`rounded-3xl border border-white/40 bg-white/60 backdrop-blur-xl shadow-[0_4px_30px_rgba(0,0,0,0.05)] ${className}`}
    >
      {children}
    </div>
  );
}

export default function ItemDetail({ item, meta, onClose, onDeleted, onUpdated }) {
  const [occasion, setOccasion] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [qtyBusy, setQtyBusy] = useState(false);
  const [favBusy, setFavBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [reanalyzeBusy, setReanalyzeBusy] = useState(false);
  const [addBusy, setAddBusy] = useState(false);
  const [tryonBusy, setTryonBusy] = useState(false);
  const [tryonImage, setTryonImage] = useState(null); // { base64, mime }
  // Edit-Mode
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState(null);
  const [saveBusy, setSaveBusy] = useState(false);
  const [brands, setBrands] = useState({ mine: [], suggestions: [] });
  const fileRef = useRef(null);

  const open = Boolean(item);

  function startEdit() {
    setEditData({
      name: item.name || "",
      category: item.category || "",
      color: item.color || "",
      material: item.material || "",
      pattern: item.pattern || "",
      style: item.style || "",
      occasion: item.occasion || "",
      season: item.season || "",
      description: item.description || "",
      brand: item.brand || "",
    });
    api.getBrands().then(setBrands).catch(() => {});
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setEditData(null);
  }

  async function saveEdit() {
    setSaveBusy(true);
    setError("");
    try {
      const updated = await api.updateItem(item.id, editData);
      onUpdated?.(updated);
      setEditing(false);
      setEditData(null);
    } catch (err) {
      setError(err.message || "Speichern fehlgeschlagen.");
    } finally {
      setSaveBusy(false);
    }
  }

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

  async function toggleFav() {
    setFavBusy(true);
    try {
      const updated = await api.toggleFavorite(item.id, !item.favorite);
      onUpdated?.(updated);
    } catch (err) {
      setError(err.message || "Favorit konnte nicht geändert werden.");
    } finally {
      setFavBusy(false);
    }
  }

  async function generateAiImage() {
    setAiBusy(true);
    setError("");
    try {
      const updated = await api.generateItemImage(item.id);
      onUpdated?.(updated);
    } catch (err) {
      const msg = err.message || "";
      if (msg.includes("Wirtschaftsraum") || msg.includes("us-west1") || msg.includes("regulatorischen")) {
        setError("🌍 Die Inszenierung ist in der EU von Google gesperrt. Das Backend müsste in einer US-Region (us-west1) laufen.");
      } else {
        setError(msg || "Bild konnte nicht in Szene gesetzt werden.");
      }
    } finally {
    }
  }

  async function removeAiImage() {
    setAiBusy(true);
    setError("");
    try {
      const updated = await api.deleteAiImage(item.id);
      onUpdated?.(updated);
    } catch (err) {
      setError(err.message || "Bild konnte nicht entfernt werden.");
    } finally {
      setAiBusy(false);
    }
  }

  async function reanalyze() {
    setReanalyzeBusy(true);
    setError("");
    try {
      const updated = await api.reanalyzeItem(item.id, true);
      onUpdated?.(updated);
    } catch (err) {
      setError(err.message || "Neue Analyse fehlgeschlagen.");
    } finally {
      setReanalyzeBusy(false);
    }
  }

  async function addImages(e) {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (!files.length) return;
    setAddBusy(true);
    setError("");
    try {
      const images = await Promise.all(
        files.map(async (f) => ({
          image_base64: await fileToBase64(f),
          image_mime: f.type || "image/jpeg",
        }))
      );
      const updated = await api.addItemImages(item.id, images);
      onUpdated?.(updated);
    } catch (err) {
      setError(err.message || "Bilder konnten nicht hinzugefügt werden.");
    } finally {
      setAddBusy(false);
    }
  }

  async function getRecommendation() {
    setLoading(true);
    setError("");
    setResult(null);
    setTryonImage(null);
    try {
      const res = await api.recommend({ item_id: item.id, occasion, note });
      setResult(res);
    } catch (err) {
      setError(err.message || "Empfehlung fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  async function showTryon() {
    if (!result) return;
    setTryonBusy(true);
    setError("");
    try {
      const ids = result.pieces.map((p) => p.item_id);
      const res = await api.outfitTryon(ids, occasion);
      setTryonImage({ base64: res.image_base64, mime: res.image_mime });
    } catch (err) {
      setError(err.message || "Anprobe fehlgeschlagen.");
    } finally {
      setTryonBusy(false);
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
    setTryonImage(null);
    setEditing(false);
    setEditData(null);
    onClose();
  }

  const busy = aiBusy || reanalyzeBusy || addBusy;

  return (
    <AnimatePresence>
      {open && item && (
        <motion.div
          className="fixed inset-0 z-50 flex flex-col"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Deckender Hintergrund: erst Vollton, darüber das unscharfe Item-Bild */}
          <div className="absolute inset-0 bg-sand-50" />
          <div className="absolute inset-0 overflow-hidden">
            <img
              src={item.thumbnail_url || item.image_url}
              alt=""
              className="w-full h-full object-cover scale-125 blur-3xl opacity-30"
            />
            {/* sanfter Verlauf sorgt für Lesbarkeit und Tiefe */}
            <div className="absolute inset-0 bg-gradient-to-b from-sand-50/70 via-sand-50/85 to-sand-50" />
          </div>

          {/* Ganzflächiges Sheet */}
          <motion.div
            className="relative flex-1 overflow-y-auto"
            initial={{ y: 40, opacity: 0.5 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
          >
            {/* Kopfleiste (sticky, glass) */}
            <div
              className="sticky top-0 z-10 flex items-center justify-between px-5 py-3 bg-white/50 backdrop-blur-xl border-b border-white/40"
              style={{ paddingTop: "max(env(safe-area-inset-top), 0.75rem)" }}
            >
              <div className="min-w-0">
                <h2 className="text-lg font-semibold text-ink-900 truncate">
                  {editing ? "Bearbeiten" : (item.name || item.category)}
                </h2>
                <p className="text-xs text-ink-700/50 truncate">{item.category}</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {!editing && (
                  <button
                    onClick={startEdit}
                    className="w-9 h-9 rounded-full bg-white/70 text-ink-800 flex items-center justify-center text-base leading-none hover:bg-white transition"
                    aria-label="Bearbeiten"
                  >
                    ✏️
                  </button>
                )}
                <button
                  onClick={editing ? cancelEdit : handleClose}
                  className="w-9 h-9 rounded-full bg-white/70 text-ink-800 flex items-center justify-center text-xl leading-none hover:bg-white transition"
                  aria-label={editing ? "Abbrechen" : "Schließen"}
                >
                  ×
                </button>
              </div>
            </div>

            <div className="max-w-lg mx-auto px-5 py-5 space-y-4">

              {/* ── Edit-Mode ── */}
              {editing && editData && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-4"
                >
                  <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2">
                      <TextField label="Name" value={editData.name}
                        onChange={(v) => setEditData((d) => ({ ...d, name: v }))} />
                    </div>
                    <GroupedSelectField label="Kategorie" value={editData.category}
                      onChange={(v) => setEditData((d) => ({ ...d, category: v }))}
                      groups={meta.category_groups} />
                    <TextField label="Farbe" value={editData.color}
                      onChange={(v) => setEditData((d) => ({ ...d, color: v }))} />
                    <SelectField label="Material" value={editData.material}
                      onChange={(v) => setEditData((d) => ({ ...d, material: v }))}
                      options={meta.materials} />
                    <TextField label="Muster / Textur" value={editData.pattern}
                      onChange={(v) => setEditData((d) => ({ ...d, pattern: v }))} />
                    <SelectField label="Stil" value={editData.style}
                      onChange={(v) => setEditData((d) => ({ ...d, style: v }))}
                      options={meta.styles} />
                    <SelectField label="Anlass" value={editData.occasion}
                      onChange={(v) => setEditData((d) => ({ ...d, occasion: v }))}
                      options={meta.occasions} />
                    <div className="col-span-2">
                      <SelectField label="Jahreszeit" value={editData.season}
                        onChange={(v) => setEditData((d) => ({ ...d, season: v }))}
                        options={meta.seasons} />
                    </div>
                    <div className="col-span-2">
                      <BrandField value={editData.brand}
                        onChange={(v) => setEditData((d) => ({ ...d, brand: v }))}
                        mine={brands.mine} suggestions={brands.suggestions} />
                    </div>
                    <div className="col-span-2">
                      <TextField label="Beschreibung" value={editData.description}
                        onChange={(v) => setEditData((d) => ({ ...d, description: v }))} />
                    </div>
                  </div>

                  {error && (
                    <div className="rounded-2xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2">
                      {error}
                    </div>
                  )}

                  <button
                    onClick={saveEdit}
                    disabled={saveBusy}
                    className="w-full rounded-2xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 transition disabled:opacity-60 flex items-center justify-center gap-2"
                  >
                    {saveBusy ? <><Spinner tone="white" /> Speichern …</> : "✓ Speichern"}
                  </button>

                  <div style={{ height: "env(safe-area-inset-bottom)" }} />
                </motion.div>
              )}

              {/* ── Normal-Mode ── */}
              {!editing && (<>
              <ImageGallery item={item} />

              {/* Aktions-Reihe: Bilder hinzufügen + neue Analyse */}
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => fileRef.current?.click()}
                  disabled={busy}
                  className="flex items-center justify-center gap-2 rounded-2xl border border-white/50 bg-white/60 backdrop-blur-xl px-4 py-3 text-sm font-medium text-ink-800 hover:bg-white/80 transition disabled:opacity-50"
                >
                  {addBusy ? (
                    <Spinner tone="ink" />
                  ) : (
                    <span className="text-lg">📸</span>
                  )}
                  Bilder hinzufügen
                </button>
                <button
                  onClick={reanalyze}
                  disabled={busy}
                  className="flex items-center justify-center gap-2 rounded-2xl bg-clay-500 text-white px-4 py-3 text-sm font-medium hover:bg-clay-600 transition disabled:opacity-50"
                >
                  {reanalyzeBusy ? (
                    <Spinner tone="white" />
                  ) : (
                    <span className="text-lg">🔁</span>
                  )}
                  Neu analysieren
                </button>
              </div>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={addImages}
              />
              {reanalyzeBusy && (
                <p className="text-center text-xs text-ink-700/50">
                  Vesti liest die Bilder neu aus, aktualisiert alle Details und setzt das Teil neu in Szene …
                </p>
              )}

              {/* Tags + Beschreibung */}
              <div className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  {[item.category, item.color, item.style, item.material, item.pattern, item.season, item.occasion, item.brand]
                    .filter(Boolean)
                    .map((tag, i) => (
                      <span
                        key={i}
                        className="text-xs bg-white/60 backdrop-blur-md border border-white/40 text-ink-700 rounded-full px-3 py-1"
                      >
                        {tag}
                      </span>
                    ))}
                </div>
                {item.description && (
                  <p className="text-sm text-ink-700/70 leading-relaxed px-0.5">
                    {item.description}
                  </p>
                )}
              </div>

              {/* KI-Produktfoto Steuerung */}
              <GlassCard className="p-4">
                <div className="flex items-center gap-2">
                  <button
                    onClick={generateAiImage}
                    disabled={busy}
                    className="flex-1 flex items-center justify-center gap-2 rounded-2xl bg-clay-500/10 hover:bg-clay-500/20 text-clay-600 px-4 py-3 transition disabled:opacity-60"
                  >
                    {aiBusy ? (
                      <Spinner tone="clay" />
                    ) : (
                      <span className="text-lg">✨</span>
                    )}
                    <span className="text-sm font-medium">
                      {item.has_ai_image ? "Neu in Szene setzen" : "In Szene setzen"}
                    </span>
                  </button>
                  {item.has_ai_image && !aiBusy && (
                    <button
                      onClick={removeAiImage}
                      className="rounded-2xl bg-white/60 hover:bg-white/80 text-ink-700 px-4 py-3 text-sm font-medium transition"
                      aria-label="Inszeniertes Bild entfernen"
                    >
                      🗑️
                    </button>
                  )}
                </div>
              </GlassCard>

              {/* Favorit + Stückzahl */}
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={toggleFav}
                  disabled={favBusy}
                  className="flex items-center justify-center gap-2 rounded-2xl border border-white/50 bg-white/60 backdrop-blur-xl px-4 py-3 transition hover:bg-white/80 disabled:opacity-60"
                >
                  <span className="text-lg">{item.favorite ? "⭐" : "☆"}</span>
                  <span className="text-sm font-medium text-ink-900">
                    {item.favorite ? "Favorit" : "Merken"}
                  </span>
                </button>
                <div className="flex items-center justify-between rounded-2xl border border-white/50 bg-white/60 backdrop-blur-xl px-3 py-2">
                  <button
                    onClick={() => changeQty(-1)}
                    disabled={qtyBusy || (item.quantity || 1) <= 1}
                    className="w-8 h-8 rounded-full bg-white text-ink-800 shadow-sm text-lg leading-none disabled:opacity-40 hover:bg-sand-50 transition"
                    aria-label="Weniger"
                  >
                    −
                  </button>
                  <span className="font-semibold text-ink-900">{item.quantity || 1}×</span>
                  <button
                    onClick={() => changeQty(1)}
                    disabled={qtyBusy}
                    className="w-8 h-8 rounded-full bg-white text-ink-800 shadow-sm text-lg leading-none disabled:opacity-40 hover:bg-sand-50 transition"
                    aria-label="Mehr"
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Details */}
              {item.details && Object.keys(item.details).length > 0 && (
                <GlassCard className="p-4 space-y-3">
                  <h3 className="text-xs font-semibold text-ink-700/70 uppercase tracking-wide">
                    Details
                  </h3>

                  {Object.entries(item.details)
                    .filter(([k, v]) => v && k !== "care_instructions" && k !== "material_details")
                    .map(([k, v]) => (
                      <div key={k} className="text-sm flex justify-between gap-3">
                        <span className="text-ink-700/50 capitalize">{k.replace(/_/g, " ")}</span>
                        <span className="text-ink-900 text-right">{v}</span>
                      </div>
                    ))}

                  {item.details.material_details &&
                    Object.values(item.details.material_details).some((v) => v) && (
                      <div className="rounded-2xl bg-white/50 p-3 space-y-1.5">
                        <div className="text-xs font-semibold text-ink-700/70 uppercase tracking-wide mb-1">
                          📋 Material & Herkunft
                        </div>
                        {Object.entries(item.details.material_details)
                          .filter(([, v]) => v)
                          .map(([k, v]) => (
                            <div key={k} className="text-sm flex justify-between gap-3">
                              <span className="text-ink-700/60">
                                {k === "composition" && "Zusammensetzung"}
                                {k === "leather_type" && "Ledertyp"}
                                {k === "lining" && "Futter"}
                                {k === "sole" && "Sohle"}
                                {k === "origin" && "Herkunft"}
                              </span>
                              <span className="text-ink-900 font-medium text-right">{v}</span>
                            </div>
                          ))}
                      </div>
                    )}

                  {item.details.care_instructions &&
                    Object.values(item.details.care_instructions).some((v) => v) && (
                      <div className="rounded-2xl bg-clay-500/5 p-3 space-y-1.5">
                        <div className="text-xs font-semibold text-clay-600 uppercase tracking-wide mb-1">
                          🧺 Pflegehinweise
                        </div>
                        {Object.entries(item.details.care_instructions)
                          .filter(([, v]) => v)
                          .map(([k, v]) => (
                            <div key={k} className="text-sm flex justify-between gap-3">
                              <span className="text-ink-700/60">
                                {k === "wash_temp" && "🌡️ Waschen"}
                                {k === "dry" && "💨 Trocknen"}
                                {k === "iron" && "🔥 Bügeln"}
                                {k === "bleach" && "⚗️ Bleichen"}
                                {k === "dry_clean" && "✨ Reinigung"}
                                {k === "special" && "⚠️ Besonderes"}
                              </span>
                              <span className="text-ink-900 font-medium text-right">{v}</span>
                            </div>
                          ))}
                      </div>
                    )}
                </GlassCard>
              )}

              {error && (
                <div className="rounded-2xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2">
                  {error}
                </div>
              )}

              {/* Outfit-Empfehlung */}
              {!result && (
                <GlassCard className="p-4 space-y-3">
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
                    className="w-full rounded-2xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Spinner tone="white" />
                        Vesti stylt …
                      </>
                    ) : (
                      "✨ Outfit vorschlagen"
                    )}
                  </button>
                </GlassCard>
              )}

              {result && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-4"
                >
                  {(() => {
                    const cfgMap = {
                      perfekt: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", icon: "✓" },
                      geht: { bg: "bg-sand-100", text: "text-ink-700", border: "border-sand-200", icon: "~" },
                      notlösung: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", icon: "⚠" },
                      ungeeignet: { bg: "bg-clay-500/10", text: "text-clay-700", border: "border-clay-200", icon: "✕" },
                    };
                    const cfg = cfgMap[result.suitability] || cfgMap.geht;
                    return (
                      <div className={`rounded-2xl border ${cfg.bg} ${cfg.border} px-4 py-3 flex gap-3 items-start`}>
                        <span className={`text-lg font-bold ${cfg.text} shrink-0`}>{cfg.icon}</span>
                        <div>
                          <p className={`text-sm font-semibold capitalize ${cfg.text}`}>{result.suitability}</p>
                          {result.suitability_reason && (
                            <p className={`text-sm mt-0.5 ${cfg.text} opacity-80`}>{result.suitability_reason}</p>
                          )}
                        </div>
                      </div>
                    );
                  })()}

                  <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide">Dein Outfit</h3>
                  <div className="grid grid-cols-3 gap-3">
                    {result.pieces.map((p) => (
                      <div key={p.item_id} className="text-center">
                        <img
                          src={p.image_url}
                          alt={p.name}
                          className="w-full aspect-square object-cover rounded-2xl shadow-soft"
                        />
                        <span className="mt-1 block text-xs text-ink-700/70 truncate">{p.name}</span>
                      </div>
                    ))}
                  </div>
                  <GlassCard className="p-4 text-sm text-ink-800 leading-relaxed">
                    {result.explanation}
                  </GlassCard>

                  {/* KI-Anprobe */}
                  <AnimatePresence>
                    {tryonImage && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="rounded-3xl overflow-hidden relative"
                      >
                        <img
                          src={`data:${tryonImage.mime};base64,${tryonImage.base64}`}
                          alt="KI-Anprobe"
                          className="w-full object-cover"
                        />
                        <span className="absolute top-3 left-3 bg-clay-500/90 text-white text-[11px] font-medium rounded-full px-2.5 py-1 backdrop-blur-md">
                          ✨ KI-Anprobe
                        </span>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Anprobe-Button */}
                  <button
                    onClick={showTryon}
                    disabled={tryonBusy}
                    className="w-full flex items-center justify-center gap-2 rounded-2xl border border-clay-400/50 bg-clay-500/5 text-clay-600 font-medium py-3 hover:bg-clay-500/10 transition disabled:opacity-60"
                  >
                    {tryonBusy ? (
                      <>
                        <Spinner tone="clay" />
                        Anprobe wird erstellt …
                      </>
                    ) : tryonImage ? (
                      "🔄 Neue Anprobe"
                    ) : (
                      "✨ Anprobe zeigen"
                    )}
                  </button>

                  <button
                    onClick={() => { setResult(null); setTryonImage(null); }}
                    className="w-full rounded-2xl border border-white/50 bg-white/60 backdrop-blur-xl text-ink-700 font-medium py-2.5 hover:bg-white/80 transition"
                  >
                    Neuer Vorschlag
                  </button>
                </motion.div>
              )}

              <button
                onClick={remove}
                className="w-full text-center text-sm text-ink-700/50 hover:text-clay-600 transition py-2"
              >
                Teil löschen
              </button>

              <div style={{ height: "env(safe-area-inset-bottom)" }} />
            </>) /* end !editing */}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Spinner({ tone = "white" }) {
  const color =
    tone === "white" ? "border-white" : tone === "clay" ? "border-clay-500" : "border-ink-700";
  return (
    <motion.span
      className={`inline-block w-4 h-4 border-2 ${color} border-t-transparent rounded-full`}
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
    />
  );
}
