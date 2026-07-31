import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";
import { SelectField, TextField, GroupedSelectField } from "./Field";
import BrandField from "./BrandField";

const STEP = {
  CAPTURE: "capture",     // Bilder sammeln + Hinweis
  ANALYZING: "analyzing", // KI arbeitet (2 Phasen)
  CONFIRM: "confirm",     // Ergebnis prüfen & speichern
  DONE: "done",           // Erfolgs-Moment
};

// Vorschläge, welche Aufnahmen sich lohnen
const SHOT_HINTS = [
  { icon: "👕", label: "Vorderseite", hint: "Das Hauptbild" },
  { icon: "🔄", label: "Rückseite", hint: "Schnitt & Details" },
  { icon: "🧵", label: "Futter", hint: "Innenseite" },
  { icon: "🏷️", label: "Etikett", hint: "Material & Pflege" },
];

const MAX_IMAGES = 6;

export default function AddItem({ open, onClose, meta, onCreated }) {
  const [step, setStep] = useState(STEP.CAPTURE);
  const [images, setImages] = useState([]); // [{ file, url, id }]
  const [hint, setHint] = useState("");
  const [phase, setPhase] = useState(0); // 0 = Kategorie, 1 = Details
  const [quickResult, setQuickResult] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [encoded, setEncoded] = useState([]); // vom Backend zurückgegebene base64-Bilder
  const [error, setError] = useState("");
  const [brands, setBrands] = useState({ mine: [], suggestions: [] });
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    api.getBrands().then(setBrands).catch(() => {});
  }, [open]);

  // Object-URLs aufräumen
  useEffect(() => {
    return () => images.forEach((img) => URL.revokeObjectURL(img.url));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function reset() {
    images.forEach((img) => URL.revokeObjectURL(img.url));
    setStep(STEP.CAPTURE);
    setImages([]);
    setHint("");
    setPhase(0);
    setQuickResult(null);
    setMetadata(null);
    setEncoded([]);
    setError("");
    setSaving(false);
  }

  function close() {
    reset();
    onClose();
  }

  function addFiles(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setError("");
    setImages((prev) => {
      const room = MAX_IMAGES - prev.length;
      const next = files.slice(0, room).map((file) => ({
        file,
        url: URL.createObjectURL(file),
        id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`,
      }));
      return [...prev, ...next];
    });
    e.target.value = "";
  }

  function removeImage(id) {
    setImages((prev) => {
      const target = prev.find((i) => i.id === id);
      if (target) URL.revokeObjectURL(target.url);
      return prev.filter((i) => i.id !== id);
    });
  }

  function makePrimary(id) {
    setImages((prev) => {
      const idx = prev.findIndex((i) => i.id === id);
      if (idx <= 0) return prev;
      const copy = [...prev];
      const [picked] = copy.splice(idx, 1);
      return [picked, ...copy];
    });
  }

  async function analyze() {
    if (!images.length) return;
    setError("");
    setPhase(0);
    setStep(STEP.ANALYZING);

    try {
      const quick = await api.analyzeQuick(
        images.map((i) => i.file),
        hint.trim()
      );
      setQuickResult(quick);
      const imgs = quick.images || [
        { image_base64: quick.image_base64, image_mime: quick.image_mime },
      ];
      setEncoded(imgs);

      setPhase(1);
      const detail = await api.analyzeDetail({
        images: imgs,
        category: quick.category,
        hint: hint.trim(),
      });

      setMetadata({
        name: detail.name,
        category: quick.category,
        color: quick.color,
        material: detail.material,
        pattern: detail.pattern,
        style: detail.style,
        occasion: detail.occasion,
        season: detail.season,
        description: detail.description,
        details: detail.details || {},
        brand: "",
        quantity: 1,
      });
      setStep(STEP.CONFIRM);
    } catch (err) {
      const msg = err.message || "";
      setError(
        msg.toLowerCase().includes("demand") || msg.includes("503") || msg.includes("502")
          ? "Die KI ist gerade überlastet — bitte in ein paar Sekunden nochmal versuchen."
          : msg || "Analyse fehlgeschlagen."
      );
      setStep(STEP.CAPTURE);
    }
  }

  function update(key, val) {
    setMetadata((m) => ({ ...m, [key]: val }));
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      const [primary, ...rest] = encoded;
      const created = await api.createItem({
        ...metadata,
        image_base64: primary.image_base64,
        image_mime: primary.image_mime,
        extra_images: rest,
      });
      setStep(STEP.DONE);
      // Kurzer Erfolgs-Moment, dann schließen
      setTimeout(() => {
        onCreated(created);
        close();
      }, 900);
    } catch (err) {
      setError(err.message || "Speichern fehlgeschlagen.");
      setSaving(false);
    }
  }

  const progress =
    step === STEP.CAPTURE ? 0.15 : step === STEP.ANALYZING ? (phase === 0 ? 0.45 : 0.75) : 1;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex flex-col bg-sand-50"
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 24, scale: 0.98 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
          {/* ── Kopf mit Fortschritt ── */}
          <div
            className="flex-shrink-0 px-5 pb-3 border-b border-sand-100 bg-sand-50/90 backdrop-blur-md"
            style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-widest text-clay-600">
                  {step === STEP.CAPTURE && "Schritt 1 · Aufnahmen"}
                  {step === STEP.ANALYZING && "Schritt 2 · KI-Analyse"}
                  {step === STEP.CONFIRM && "Schritt 3 · Prüfen"}
                  {step === STEP.DONE && "Fertig"}
                </p>
                <h2 className="text-xl font-bold text-ink-900 tracking-tight">
                  Neues Teil
                </h2>
              </div>
              <button
                onClick={close}
                className="w-9 h-9 rounded-full bg-sand-100 text-ink-700 flex items-center justify-center text-xl leading-none hover:bg-sand-200 transition"
                aria-label="Schließen"
              >
                ×
              </button>
            </div>

            <div className="mt-3 h-1 rounded-full bg-sand-200 overflow-hidden">
              <motion.div
                className="h-full bg-clay-500 rounded-full"
                animate={{ width: `${progress * 100}%` }}
                transition={{ type: "spring", stiffness: 120, damping: 20 }}
              />
            </div>
          </div>

          {/* ── Inhalt ── */}
          <div className="flex-1 overflow-y-auto px-5 py-5">
            <div className="max-w-lg mx-auto">
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mb-4 rounded-xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2"
                  >
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              <AnimatePresence mode="wait">
                {/* ══ Aufnahmen ══ */}
                {step === STEP.CAPTURE && (
                  <motion.div
                    key="capture"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-5"
                  >
                    <p className="text-sm text-ink-700/70 leading-relaxed">
                      Mehrere Aufnahmen machen die Analyse deutlich genauer. Ein Foto vom
                      Pflege-Etikett verrät der KI zum Beispiel das exakte Material.
                    </p>

                    {/* Shot-Vorschläge */}
                    <div className="grid grid-cols-4 gap-2">
                      {SHOT_HINTS.map((s, i) => (
                        <motion.div
                          key={s.label}
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className={`rounded-xl px-2 py-2.5 text-center transition ${
                            images.length > i
                              ? "bg-clay-500/10 ring-1 ring-clay-500/30"
                              : "bg-sand-100"
                          }`}
                        >
                          <div className="text-lg leading-none">{s.icon}</div>
                          <div className="mt-1 text-[10px] font-medium text-ink-900 leading-tight">
                            {s.label}
                          </div>
                        </motion.div>
                      ))}
                    </div>

                    {/* Bild-Grid */}
                    <div className="grid grid-cols-3 gap-3">
                      <AnimatePresence>
                        {images.map((img, idx) => (
                          <motion.div
                            key={img.id}
                            layout
                            initial={{ opacity: 0, scale: 0.85 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.85 }}
                            transition={{ type: "spring", stiffness: 320, damping: 26 }}
                            className="relative aspect-square rounded-2xl overflow-hidden bg-white shadow-soft group"
                          >
                            <img
                              src={img.url}
                              alt={`Aufnahme ${idx + 1}`}
                              className="w-full h-full object-cover"
                            />
                            {idx === 0 ? (
                              <span className="absolute bottom-1.5 left-1.5 bg-clay-500 text-white text-[10px] font-semibold rounded-full px-2 py-0.5">
                                Hauptbild
                              </span>
                            ) : (
                              <button
                                onClick={() => makePrimary(img.id)}
                                className="absolute bottom-1.5 left-1.5 bg-ink-900/70 text-white text-[10px] font-medium rounded-full px-2 py-0.5 backdrop-blur-sm hover:bg-ink-900/90 transition"
                              >
                                Als Hauptbild
                              </button>
                            )}
                            <button
                              onClick={() => removeImage(img.id)}
                              className="absolute top-1.5 right-1.5 w-6 h-6 rounded-full bg-ink-900/70 text-white text-sm leading-none backdrop-blur-sm hover:bg-clay-500 transition"
                              aria-label="Entfernen"
                            >
                              ×
                            </button>
                          </motion.div>
                        ))}
                      </AnimatePresence>

                      {images.length < MAX_IMAGES && (
                        <motion.button
                          layout
                          whileTap={{ scale: 0.95 }}
                          onClick={() => fileRef.current?.click()}
                          className="aspect-square rounded-2xl border-2 border-dashed border-sand-200 bg-white flex flex-col items-center justify-center gap-1 text-ink-700/50 hover:border-clay-400 hover:text-clay-500 transition"
                        >
                          <span className="text-2xl leading-none">＋</span>
                          <span className="text-[11px] font-medium">
                            {images.length === 0 ? "Foto" : "Weiteres"}
                          </span>
                        </motion.button>
                      )}
                    </div>

                    <input
                      ref={fileRef}
                      type="file"
                      accept="image/*"
                      multiple
                      className="hidden"
                      onChange={addFiles}
                    />

                    {/* Hinweis-Feld */}
                    <AnimatePresence>
                      {images.length > 0 && (
                        <motion.div
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 8 }}
                          className="space-y-1"
                        >
                          <label className="block text-xs font-medium text-ink-700/70 uppercase tracking-wide">
                            Hinweise für die KI
                            <span className="ml-1 font-normal normal-case text-ink-700/40">
                              (optional)
                            </span>
                          </label>
                          <input
                            type="text"
                            value={hint}
                            onChange={(e) => setHint(e.target.value)}
                            placeholder="z.B. Nike, Größe M, 100% Baumwolle"
                            className="w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 text-ink-900 text-sm placeholder:text-ink-700/30 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
                          />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                )}

                {/* ══ Analyse ══ */}
                {step === STEP.ANALYZING && (
                  <motion.div
                    key="analyzing"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-5"
                  >
                    {/* Bilder-Stapel mit Puls */}
                    <div className="relative mx-auto w-48 h-48">
                      {images.slice(0, 3).map((img, i) => (
                        <motion.img
                          key={img.id}
                          src={img.url}
                          alt=""
                          className="absolute inset-0 w-full h-full object-cover rounded-3xl shadow-soft"
                          style={{ zIndex: 3 - i }}
                          initial={{ rotate: 0, scale: 1 }}
                          animate={{
                            rotate: i === 0 ? 0 : i === 1 ? -6 : 6,
                            scale: 1 - i * 0.04,
                            y: i * 6,
                          }}
                          transition={{ type: "spring", stiffness: 200, damping: 20 }}
                        />
                      ))}
                      <motion.div
                        className="absolute -inset-2 rounded-[2rem] border-2 border-clay-500/40"
                        animate={{ opacity: [0.2, 0.7, 0.2], scale: [1, 1.04, 1] }}
                        transition={{ repeat: Infinity, duration: 2 }}
                      />
                    </div>

                    <div className="space-y-3">
                      <AnalysisRow
                        active={phase === 0}
                        done={phase > 0}
                        label="Kategorie & Farbe erkennen"
                        result={
                          quickResult
                            ? `${quickResult.category} · ${quickResult.color}`
                            : null
                        }
                      />
                      <AnalysisRow
                        active={phase === 1}
                        done={false}
                        label="Material, Schnitt & Details lesen"
                        result={null}
                      />
                    </div>

                    <p className="text-center text-xs text-ink-700/50">
                      {images.length > 1
                        ? `${images.length} Aufnahmen werden gemeinsam ausgewertet`
                        : "Einen Moment noch"}
                    </p>
                  </motion.div>
                )}

                {/* ══ Bestätigen ══ */}
                {step === STEP.CONFIRM && metadata && (
                  <motion.div
                    key="confirm"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-5"
                  >
                    {/* Bild-Streifen */}
                    <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
                      {images.map((img, idx) => (
                        <img
                          key={img.id}
                          src={img.url}
                          alt={`Aufnahme ${idx + 1}`}
                          className={`h-24 w-24 flex-shrink-0 object-cover rounded-2xl ${
                            idx === 0 ? "ring-2 ring-clay-500" : ""
                          }`}
                        />
                      ))}
                    </div>

                    <div className="rounded-2xl bg-clay-500/8 px-4 py-3">
                      <p className="text-sm text-ink-800">
                        Das hat die KI erkannt. Passe alles an, was nicht stimmt.
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="col-span-2">
                        <TextField
                          label="Name"
                          value={metadata.name}
                          onChange={(v) => update("name", v)}
                          placeholder="z.B. Blaues Leinenhemd"
                        />
                      </div>
                      <GroupedSelectField
                        label="Kategorie"
                        value={metadata.category}
                        onChange={(v) => update("category", v)}
                        groups={meta.category_groups}
                      />
                      <TextField
                        label="Farbe"
                        value={metadata.color}
                        onChange={(v) => update("color", v)}
                      />
                      <SelectField
                        label="Material"
                        value={metadata.material}
                        onChange={(v) => update("material", v)}
                        options={meta.materials}
                      />
                      <TextField
                        label="Muster / Textur"
                        value={metadata.pattern}
                        onChange={(v) => update("pattern", v)}
                      />
                      <SelectField
                        label="Stil"
                        value={metadata.style}
                        onChange={(v) => update("style", v)}
                        options={meta.styles}
                      />
                      <SelectField
                        label="Anlass"
                        value={metadata.occasion}
                        onChange={(v) => update("occasion", v)}
                        options={meta.occasions}
                      />
                      <div className="col-span-2">
                        <SelectField
                          label="Jahreszeit"
                          value={metadata.season}
                          onChange={(v) => update("season", v)}
                          options={meta.seasons}
                        />
                      </div>
                      <BrandField
                        value={metadata.brand}
                        onChange={(v) => update("brand", v)}
                        mine={brands.mine}
                        suggestions={brands.suggestions}
                      />
                      <label className="block">
                        <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
                          Stückzahl
                        </span>
                        <input
                          type="number"
                          min="1"
                          value={metadata.quantity ?? 1}
                          onChange={(e) =>
                            update("quantity", Math.max(1, Number(e.target.value) || 1))
                          }
                          className="mt-1 w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 text-ink-900 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
                        />
                      </label>
                      <div className="col-span-2">
                        <TextField
                          label="Beschreibung"
                          value={metadata.description}
                          onChange={(v) => update("description", v)}
                        />
                      </div>

                      {metadata.details && Object.keys(metadata.details).length > 0 && (
                        <div className="col-span-2 pt-3 border-t border-sand-200">
                          <p className="text-xs font-medium text-ink-700/70 uppercase tracking-wide mb-3">
                            Spezifische Details
                          </p>
                          <div className="grid grid-cols-2 gap-3">
                            {Object.entries(metadata.details).map(([key, value]) => (
                              <TextField
                                key={key}
                                label={key.replace(/_/g, " ")}
                                value={value || ""}
                                onChange={(v) =>
                                  setMetadata((m) => ({
                                    ...m,
                                    details: { ...m.details, [key]: v },
                                  }))
                                }
                              />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}

                {/* ══ Fertig ══ */}
                {step === STEP.DONE && (
                  <motion.div
                    key="done"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center justify-center py-20 gap-4"
                  >
                    <motion.div
                      initial={{ scale: 0, rotate: -90 }}
                      animate={{ scale: 1, rotate: 0 }}
                      transition={{ type: "spring", stiffness: 240, damping: 14 }}
                      className="w-20 h-20 rounded-full bg-clay-500 text-white flex items-center justify-center text-4xl"
                    >
                      ✓
                    </motion.div>
                    <p className="text-lg font-semibold text-ink-900">
                      In der Garderobe
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* ── Aktionsleiste ── */}
          {step !== STEP.DONE && (
            <div
              className="flex-shrink-0 px-5 pt-3 border-t border-sand-100 bg-sand-50/90 backdrop-blur-md"
              style={{ paddingBottom: "max(env(safe-area-inset-bottom), 0.75rem)" }}
            >
              <div className="max-w-lg mx-auto flex items-center gap-3">
                {step === STEP.CAPTURE && (
                  <>
                    <span className="text-xs text-ink-700/50 flex-1">
                      {images.length === 0
                        ? "Mindestens ein Foto"
                        : `${images.length} von ${MAX_IMAGES} Aufnahmen`}
                    </span>
                    <motion.button
                      whileTap={{ scale: 0.97 }}
                      onClick={analyze}
                      disabled={images.length === 0}
                      className="rounded-xl bg-clay-500 text-white font-medium px-6 py-3 hover:bg-clay-600 transition disabled:opacity-40"
                    >
                      ✦ Analysieren
                    </motion.button>
                  </>
                )}

                {step === STEP.ANALYZING && (
                  <button
                    onClick={() => setStep(STEP.CAPTURE)}
                    className="w-full rounded-xl border border-sand-200 text-ink-700 font-medium py-3 hover:bg-sand-100 transition"
                  >
                    Abbrechen
                  </button>
                )}

                {step === STEP.CONFIRM && (
                  <>
                    <button
                      onClick={() => setStep(STEP.CAPTURE)}
                      className="rounded-xl border border-sand-200 text-ink-700 font-medium px-4 py-3 hover:bg-sand-100 transition"
                    >
                      Zurück
                    </button>
                    <motion.button
                      whileTap={{ scale: 0.97 }}
                      onClick={save}
                      disabled={saving}
                      className="flex-1 rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 transition disabled:opacity-60 flex items-center justify-center gap-2"
                    >
                      {saving ? (
                        <>
                          <motion.span
                            className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                            animate={{ rotate: 360 }}
                            transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                          />
                          Speichern …
                        </>
                      ) : (
                        "In Garderobe speichern"
                      )}
                    </motion.button>
                  </>
                )}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function AnalysisRow({ active, done, label, result }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-2xl px-4 py-3 transition ${
        active ? "bg-white shadow-soft" : done ? "bg-clay-500/8" : "bg-sand-100"
      }`}
    >
      <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
        {done ? (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="text-clay-600 text-sm font-bold"
          >
            ✓
          </motion.span>
        ) : active ? (
          <motion.span
            className="block w-4 h-4 border-2 border-clay-500 border-t-transparent rounded-full"
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
          />
        ) : (
          <span className="block w-1.5 h-1.5 rounded-full bg-ink-700/25" />
        )}
      </div>
      <div className="min-w-0">
        <p
          className={`text-sm font-medium ${
            active || done ? "text-ink-900" : "text-ink-700/50"
          }`}
        >
          {label}
        </p>
        {result && <p className="text-xs text-clay-600 mt-0.5 truncate">{result}</p>}
      </div>
    </div>
  );
}
