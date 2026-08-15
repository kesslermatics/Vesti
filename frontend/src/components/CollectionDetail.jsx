import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";
import { FillLevelSlider, FragranceFields, WatchFields } from "./CollectionForm";

// ── Bild-Galerie: KI-Foto zuerst, dann die eigenen Aufnahmen ──
function Gallery({ entry, label }) {
  const baseUrls = entry.image_urls?.length ? entry.image_urls : [entry.image_url];
  const baseThumbs = entry.thumbnail_urls?.length
    ? entry.thumbnail_urls
    : [entry.thumbnail_url || entry.image_url];

  const urls = entry.has_ai_image ? [entry.ai_image_url, ...baseUrls] : baseUrls;
  const thumbs = entry.has_ai_image
    ? [entry.ai_thumbnail_url || entry.ai_image_url, ...baseThumbs]
    : baseThumbs;

  const [active, setActive] = useState(0);
  useEffect(() => setActive(0), [entry.id, urls.length]);

  const idx = Math.min(active, urls.length - 1);
  const isAi = entry.has_ai_image && idx === 0;

  return (
    <div>
      <div className="relative rounded-3xl overflow-hidden bg-ink-900/5 aspect-square">
        <img
          src={urls[idx]}
          alt={label}
          className="absolute inset-0 w-full h-full object-cover"
        />
        {isAi && (
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
          {thumbs.map((t, i) => (
            <button
              key={t}
              onClick={() => setActive(i)}
              className={`relative h-16 w-16 flex-shrink-0 rounded-2xl overflow-hidden transition ${
                i === idx ? "ring-2 ring-clay-500" : "opacity-60 hover:opacity-100"
              }`}
            >
              <img src={t} alt={`Ansicht ${i + 1}`} className="w-full h-full object-cover" />
              {entry.has_ai_image && i === 0 && (
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

function GlassCard({ children, className = "" }) {
  return (
    <div
      className={`rounded-3xl border border-white/40 bg-white/60 backdrop-blur-xl shadow-[0_4px_30px_rgba(0,0,0,0.05)] ${className}`}
    >
      {children}
    </div>
  );
}

// Zeile in der Datentabelle. Leere Werte werden ausgelassen.
function Row({ label, value }) {
  if (value === null || value === undefined || value === "" ) return null;
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="text-xs text-ink-700/50 flex-shrink-0">{label}</span>
      <span className="text-sm text-ink-900 text-right">{value}</span>
    </div>
  );
}

function Chips({ items }) {
  if (!items?.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((i) => (
        <span
          key={i}
          className="rounded-full bg-sand-100 text-ink-700/80 text-xs px-2.5 py-1"
        >
          {i}
        </span>
      ))}
    </div>
  );
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

function money(value, currency = "EUR") {
  if (value === null || value === undefined || value === "") return "";
  try {
    return new Intl.NumberFormat("de-DE", {
      style: "currency",
      currency: currency || "EUR",
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${value} ${currency}`;
  }
}

// ══════════════════════════════════════════════════════════════
//  Gemeinsames Detail-Gerüst
// ══════════════════════════════════════════════════════════════

function DetailShell({
  entry,
  title,
  subtitle,
  onClose,
  onDeleted,
  onUpdated,
  children,
  editFields: EditFields,
  meta,
  loadBrands,
  onSave,
  onReanalyze,
  onGenerateImage,
  onToggleFavorite,
  onDeleteEntry,
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(null);
  const [brands, setBrands] = useState({ mine: [], suggestions: [] });
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Nur von `editing` abhängig: `loadBrands` kommt als Inline-Arrow herein und
  // wäre bei jedem Render neu, was den Effekt in eine Endlosschleife treiben würde.
  useEffect(() => {
    if (!editing) return;
    loadBrands().then(setBrands).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editing]);

  function startEdit() {
    setDraft({ ...entry });
    setEditing(true);
  }

  function update(key, value) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function run(action, label) {
    setBusy(label);
    setError("");
    try {
      const updated = await action();
      if (updated) onUpdated(updated);
      return updated;
    } catch (err) {
      setError(err.message || "Aktion fehlgeschlagen.");
      return null;
    } finally {
      setBusy("");
    }
  }

  async function save() {
    const updated = await run(() => onSave(draft), "save");
    if (updated) setEditing(false);
  }

  return (
    <motion.div
      className="fixed inset-0 z-50 flex flex-col bg-sand-50"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 24 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
    >
      {/* Kopf */}
      <div
        className="flex-shrink-0 px-5 pb-3 border-b border-sand-100 bg-sand-50/90 backdrop-blur-md"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-xl font-bold text-ink-900 tracking-tight truncate">
              {title}
            </h2>
            {subtitle && (
              <p className="text-xs text-ink-700/60 truncate">{subtitle}</p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => run(() => onToggleFavorite(!entry.favorite), "fav")}
              className={`w-9 h-9 rounded-full flex items-center justify-center transition ${
                entry.favorite
                  ? "bg-amber-400 text-white"
                  : "bg-sand-100 text-ink-700/40 hover:text-ink-700"
              }`}
              aria-label="Favorit"
            >
              ⭐
            </button>
            <button
              onClick={onClose}
              className="w-9 h-9 rounded-full bg-sand-100 text-ink-700 flex items-center justify-center text-xl leading-none hover:bg-sand-200 transition"
              aria-label="Schließen"
            >
              ×
            </button>
          </div>
        </div>
      </div>

      {/* Inhalt */}
      <div className="flex-1 overflow-y-auto px-5 py-5">
        <div className="max-w-lg mx-auto space-y-5">
          {error && (
            <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2">
              {error}
            </div>
          )}

          {entry.needs_review && !editing && (
            <div className="rounded-2xl bg-amber-400/10 px-4 py-3 space-y-2">
              <p className="text-sm text-ink-800">
                Dieser Eintrag wurde aus der Kleidungs-Garderobe übernommen. Die
                technischen Daten fehlen noch, weil sie dort nie erfasst wurden.
              </p>
              <button
                onClick={() => run(() => onReanalyze(true), "reanalyze")}
                disabled={busy === "reanalyze"}
                className="w-full rounded-xl bg-clay-500 text-white text-sm font-medium py-2.5 hover:bg-clay-600 transition disabled:opacity-60"
              >
                {busy === "reanalyze" ? "KI analysiert …" : "Jetzt per KI erfassen"}
              </button>
            </div>
          )}

          <Gallery entry={entry} label={title} />

          {editing ? (
            <>
              <EditFields data={draft} update={update} meta={meta} brands={brands} />
              <div className="flex gap-2">
                <button
                  onClick={() => setEditing(false)}
                  className="flex-1 rounded-xl border border-sand-200 bg-white py-3 text-sm font-medium text-ink-700 hover:bg-sand-50 transition"
                >
                  Abbrechen
                </button>
                <button
                  onClick={save}
                  disabled={busy === "save"}
                  className="flex-1 rounded-xl bg-clay-500 text-white py-3 text-sm font-medium hover:bg-clay-600 transition disabled:opacity-60"
                >
                  {busy === "save" ? "Speichern …" : "Speichern"}
                </button>
              </div>
            </>
          ) : (
            <>
              {children}

              <div className="space-y-2 pt-2">
                <button
                  onClick={startEdit}
                  className="w-full rounded-xl border border-sand-200 bg-white py-3 text-sm font-medium text-ink-700 hover:bg-sand-50 transition"
                >
                  ✏️ Angaben bearbeiten
                </button>
                <button
                  onClick={() => run(() => onGenerateImage(), "shot")}
                  disabled={busy === "shot"}
                  className="w-full rounded-xl border border-clay-400 bg-clay-500/5 py-3 text-sm font-medium text-clay-600 hover:bg-clay-500/10 transition disabled:opacity-60"
                >
                  {busy === "shot"
                    ? "Wird in Szene gesetzt …"
                    : entry.has_ai_image
                    ? "🔄 Neu in Szene setzen"
                    : "✨ In Szene setzen"}
                </button>
                <button
                  onClick={() => run(() => onReanalyze(false), "reanalyze")}
                  disabled={busy === "reanalyze"}
                  className="w-full rounded-xl border border-sand-200 bg-white py-3 text-sm font-medium text-ink-700 hover:bg-sand-50 transition disabled:opacity-60"
                >
                  {busy === "reanalyze" ? "KI analysiert …" : "🔍 Per KI neu erfassen"}
                </button>

                {confirmDelete ? (
                  <div className="rounded-xl bg-clay-500/10 p-3 space-y-2">
                    <p className="text-sm text-ink-800">
                      Wirklich löschen? Das lässt sich nicht rückgängig machen.
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setConfirmDelete(false)}
                        className="flex-1 rounded-lg border border-sand-200 bg-white py-2 text-sm font-medium text-ink-700"
                      >
                        Behalten
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            await onDeleteEntry();
                            onDeleted(entry.id);
                          } catch (err) {
                            setError(err.message || "Löschen fehlgeschlagen.");
                          }
                        }}
                        className="flex-1 rounded-lg bg-clay-500 py-2 text-sm font-medium text-white"
                      >
                        Löschen
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmDelete(true)}
                    className="w-full rounded-xl py-3 text-sm font-medium text-clay-600 hover:bg-clay-500/5 transition"
                  >
                    Aus der Sammlung entfernen
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ══════════════════════════════════════════════════════════════
//  Uhr
// ══════════════════════════════════════════════════════════════

export function WatchDetail({ watch, meta, onClose, onDeleted, onUpdated }) {
  return (
    <AnimatePresence>
      {watch && (
        <DetailShell
          key={watch.id}
          entry={watch}
          title={watch.name || [watch.brand, watch.model].filter(Boolean).join(" ") || "Uhr"}
          subtitle={[watch.brand, watch.reference].filter(Boolean).join(" · ")}
          meta={meta}
          onClose={onClose}
          onDeleted={onDeleted}
          onUpdated={onUpdated}
          editFields={WatchFields}
          loadBrands={() => api.getWatchBrands()}
          onSave={(draft) => api.updateWatch(watch.id, draft)}
          onReanalyze={(regen) => api.reanalyzeWatch(watch.id, regen)}
          onGenerateImage={() => api.generateWatchImage(watch.id)}
          onToggleFavorite={(fav) => api.toggleWatchFavorite(watch.id, fav)}
          onDeleteEntry={() => api.deleteWatch(watch.id)}
        >
          {watch.description && (
            <p className="text-sm text-ink-800 leading-relaxed">{watch.description}</p>
          )}

          {watch.service_due && (
            <div className="rounded-2xl bg-clay-500/10 px-4 py-3">
              <p className="text-sm text-clay-600 font-medium">
                Service ist fällig
              </p>
              <p className="text-xs text-ink-700/60 mt-0.5">
                Berechnet für {formatDate(watch.service_due_date)}. Bei mechanischen
                Werken schützt eine Revision vor Folgeschäden.
              </p>
            </div>
          )}

          {watch.wrist_advice && (
            <div className="rounded-2xl bg-sand-100 px-4 py-3">
              <p className="text-xs font-medium text-ink-700/60 uppercase tracking-wide mb-1">
                An deinem Handgelenk
              </p>
              <p className="text-sm text-ink-800">{watch.wrist_advice}</p>
            </div>
          )}

          <GlassCard className="p-4 divide-y divide-sand-100">
            <div>
              <Row label="Uhrentyp" value={watch.style} />
              <Row label="Werk" value={watch.movement} />
              <Row label="Baujahr" value={watch.year} />
              <Row label="Referenz" value={watch.reference} />
            </div>
            <div className="pt-2">
              <Row label="Gehäuse" value={watch.case_material} />
              <Row
                label="Durchmesser"
                value={watch.case_diameter ? `${watch.case_diameter} mm` : ""}
              />
              <Row
                label="Höhe"
                value={watch.case_thickness ? `${watch.case_thickness} mm` : ""}
              />
              <Row label="Glas" value={watch.crystal} />
              <Row
                label="Wasserdicht"
                value={watch.water_resistance ? `${watch.water_resistance} m` : ""}
              />
            </div>
            <div className="pt-2">
              <Row label="Zifferblatt" value={watch.dial_color} />
              <Row label="Armband" value={watch.band_type} />
              <Row label="Band-Material" value={watch.band_material} />
              <Row label="Band-Farbe" value={watch.band_color} />
              <Row label="Schließe" value={watch.clasp} />
              <Row
                label="Bandanstoß"
                value={watch.lug_width ? `${watch.lug_width} mm` : ""}
              />
            </div>
            <div className="pt-2">
              <Row label="Zustand" value={watch.condition} />
              <Row label="Lieferumfang" value={watch.box_papers} />
              <Row label="Gekauft" value={formatDate(watch.purchase_date)} />
              <Row
                label="Kaufpreis"
                value={money(watch.purchase_price, watch.currency)}
              />
              <Row
                label="Aktueller Wert"
                value={money(watch.current_value, watch.currency)}
              />
              <Row label="Garantie bis" value={formatDate(watch.warranty_until)} />
              <Row label="Letzter Service" value={formatDate(watch.serviced_at)} />
            </div>
          </GlassCard>

          {watch.complications?.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-ink-700/60 uppercase tracking-wide">
                Funktionen
              </p>
              <Chips items={watch.complications} />
            </div>
          )}

          {watch.occasions?.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-ink-700/60 uppercase tracking-wide">
                Passt zu
              </p>
              <Chips items={watch.occasions} />
            </div>
          )}

          {watch.notes && (
            <div className="rounded-2xl bg-sand-100 px-4 py-3">
              <p className="text-xs font-medium text-ink-700/60 uppercase tracking-wide mb-1">
                Deine Notiz
              </p>
              <p className="text-sm text-ink-800">{watch.notes}</p>
            </div>
          )}
        </DetailShell>
      )}
    </AnimatePresence>
  );
}

// ══════════════════════════════════════════════════════════════
//  Duft
// ══════════════════════════════════════════════════════════════

// Duftpyramide: Kopf oben, Basis unten – die übliche Leserichtung
function Pyramid({ fragrance }) {
  const levels = [
    { label: "Kopfnoten", notes: fragrance.top_notes, hint: "die ersten Minuten" },
    { label: "Herznoten", notes: fragrance.heart_notes, hint: "der Kern des Dufts" },
    { label: "Basisnoten", notes: fragrance.base_notes, hint: "was am Ende bleibt" },
  ].filter((l) => l.notes?.length);

  if (!levels.length) {
    return (
      <div className="rounded-2xl bg-sand-100 px-4 py-3">
        <p className="text-sm text-ink-700/60">
          Noch keine Duftnoten hinterlegt. Über „Per KI neu erfassen" versucht Vesti,
          den Duft anhand des Etiketts zu identifizieren.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-ink-700/60 uppercase tracking-wide">
        Duftpyramide
      </p>
      {levels.map((level, i) => (
        <div key={level.label} className="relative pl-4">
          <span
            className="absolute left-0 top-1.5 bottom-0 w-0.5 rounded-full"
            style={{ backgroundColor: `rgba(185, 115, 79, ${0.9 - i * 0.25})` }}
          />
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-medium text-ink-900">{level.label}</span>
            <span className="text-[11px] text-ink-700/40">{level.hint}</span>
          </div>
          <div className="mt-1.5">
            <Chips items={level.notes} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function FragranceDetail({ fragrance, meta, onClose, onDeleted, onUpdated }) {
  const [fill, setFill] = useState(fragrance?.fill_level ?? 100);
  const [fillBusy, setFillBusy] = useState(false);

  useEffect(() => {
    setFill(fragrance?.fill_level ?? 100);
  }, [fragrance?.id, fragrance?.fill_level]);

  async function commitFill(value) {
    setFill(value);
    setFillBusy(true);
    try {
      const updated = await api.updateFillLevel(fragrance.id, value);
      onUpdated(updated);
    } catch {
      // Fehler hier stillschweigend ignorieren, der Regler ist unkritisch
    } finally {
      setFillBusy(false);
    }
  }

  return (
    <AnimatePresence>
      {fragrance && (
        <DetailShell
          key={fragrance.id}
          entry={fragrance}
          title={fragrance.name || "Duft"}
          subtitle={[fragrance.brand, fragrance.concentration].filter(Boolean).join(" · ")}
          meta={meta}
          onClose={onClose}
          onDeleted={onDeleted}
          onUpdated={onUpdated}
          editFields={FragranceFields}
          loadBrands={() => api.getFragranceBrands()}
          onSave={(draft) => api.updateFragrance(fragrance.id, draft)}
          onReanalyze={(regen) => api.reanalyzeFragrance(fragrance.id, regen)}
          onGenerateImage={() => api.generateFragranceImage(fragrance.id)}
          onToggleFavorite={(fav) => api.toggleFragranceFavorite(fragrance.id, fav)}
          onDeleteEntry={() => api.deleteFragrance(fragrance.id)}
        >
          {fragrance.description && (
            <p className="text-sm text-ink-800 leading-relaxed">
              {fragrance.description}
            </p>
          )}

          {fragrance.expired && (
            <div className="rounded-2xl bg-clay-500/10 px-4 py-3">
              <p className="text-sm text-clay-600 font-medium">
                Haltbarkeit überschritten
              </p>
              <p className="text-xs text-ink-700/60 mt-0.5">
                Geöffnet am {formatDate(fragrance.opened_at)}, erwartet gekippt seit{" "}
                {formatDate(fragrance.expires_at)}. Riech vor dem Tragen kurz nach –
                Zitrusnoten kippen zuerst.
              </p>
            </div>
          )}

          {/* Füllstand direkt bedienbar, ohne in den Bearbeiten-Modus zu wechseln */}
          <GlassCard className="p-4">
            <FillLevelSlider value={fill} onChange={commitFill} />
            {fillBusy && (
              <p className="text-[11px] text-ink-700/40 mt-1">Wird gespeichert …</p>
            )}
          </GlassCard>

          <Pyramid fragrance={fragrance} />

          <GlassCard className="p-4 divide-y divide-sand-100">
            <div>
              <Row label="Duftfamilie" value={fragrance.family} />
              <Row label="Zweite Familie" value={fragrance.secondary_family} />
              <Row label="Konzentration" value={fragrance.concentration} />
              <Row label="Linie" value={fragrance.line} />
              <Row label="Zielgruppe" value={fragrance.audience} />
              <Row label="Erschienen" value={fragrance.year} />
              <Row label="Parfumeur" value={fragrance.perfumer} />
            </div>
            <div className="pt-2">
              <Row label="Sillage" value={fragrance.sillage} />
              <Row label="Haltbarkeit" value={fragrance.longevity} />
              <Row label="Tageszeit" value={fragrance.time_of_day} />
            </div>
            <div className="pt-2">
              <Row
                label="Flakon"
                value={fragrance.bottle_size ? `${fragrance.bottle_size} ml` : ""}
              />
              <Row
                label="Anzahl"
                value={fragrance.quantity > 1 ? `${fragrance.quantity} Flakons` : ""}
              />
              <Row label="Batch-Code" value={fragrance.batch_code} />
              <Row label="Geöffnet" value={formatDate(fragrance.opened_at)} />
              <Row label="Gekauft" value={formatDate(fragrance.purchase_date)} />
              <Row
                label="Kaufpreis"
                value={money(fragrance.purchase_price, fragrance.currency)}
              />
              {fragrance.expires_at && !fragrance.expired && (
                <Row label="Haltbar bis" value={formatDate(fragrance.expires_at)} />
              )}
            </div>
          </GlassCard>

          {fragrance.seasons?.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-ink-700/60 uppercase tracking-wide">
                Jahreszeiten
              </p>
              <Chips items={fragrance.seasons} />
            </div>
          )}

          {fragrance.occasions?.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-ink-700/60 uppercase tracking-wide">
                Passt zu
              </p>
              <Chips items={fragrance.occasions} />
            </div>
          )}

          {fragrance.notes && (
            <div className="rounded-2xl bg-sand-100 px-4 py-3">
              <p className="text-xs font-medium text-ink-700/60 uppercase tracking-wide mb-1">
                Deine Notiz
              </p>
              <p className="text-sm text-ink-800">{fragrance.notes}</p>
            </div>
          )}
        </DetailShell>
      )}
    </AnimatePresence>
  );
}
