import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../api";
import Modal from "./Modal";
import { SelectField, TextField, GroupedSelectField } from "./Field";

const STEP = {
  UPLOAD: "upload",
  READY: "ready",
  QUICK: "quick",         // Schritt 1: Kategorie & Farbe
  DETAIL: "detail",       // Schritt 2: Details
  CONFIRM: "confirm",
  SAVING: "saving",
};

export default function AddItem({ open, onClose, meta, onCreated }) {
  const [step, setStep] = useState(STEP.UPLOAD);
  const [preview, setPreview] = useState(null);
  const [file, setFile] = useState(null);
  const [hint, setHint] = useState("");
  const [quickResult, setQuickResult] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [image, setImage] = useState({ base64: "", mime: "" });
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  function reset() {
    setStep(STEP.UPLOAD);
    setPreview(null);
    setFile(null);
    setHint("");
    setQuickResult(null);
    setMetadata(null);
    setImage({ base64: "", mime: "" });
    setError("");
  }

  function close() {
    reset();
    onClose();
  }

  function handleFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setError("");
    setPreview(URL.createObjectURL(f));
    setFile(f);
    setStep(STEP.READY);
    e.target.value = "";
  }

  async function analyze() {
    if (!file) return;
    setError("");
    
    // Schritt 1: Quick
    setStep(STEP.QUICK);
    try {
      const quick = await api.analyzeQuick(file, hint.trim());
      setQuickResult(quick);
      setImage({ base64: quick.image_base64, mime: quick.image_mime });

      // Schritt 2: Detail
      setStep(STEP.DETAIL);
      const detail = await api.analyzeDetail({
        image_base64: quick.image_base64,
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
      setStep(STEP.READY);
    }
  }

  function update(key, val) {
    setMetadata((m) => ({ ...m, [key]: val }));
  }

  async function save() {
    setStep(STEP.SAVING);
    setError("");
    try {
      const created = await api.createItem({
        ...metadata,
        image_base64: image.base64,
        image_mime: image.mime,
      });
      onCreated(created);
      close();
    } catch (err) {
      setError(err.message || "Speichern fehlgeschlagen.");
      setStep(STEP.CONFIRM);
    }
  }

  return (
    <Modal open={open} onClose={close}>
      <div className="p-5 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-ink-900">Neues Teil hinzufügen</h2>
          <button onClick={close} className="text-ink-700/50 hover:text-ink-900 text-2xl leading-none">
            ×
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2">
            {error}
          </div>
        )}

        {/* ── Upload & Hinweis ── */}
        {(step === STEP.UPLOAD || step === STEP.READY) && (
          <div className="space-y-4">
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full aspect-[4/3] rounded-2xl border-2 border-dashed border-sand-200 bg-white flex flex-col items-center justify-center gap-2 text-ink-700/60 hover:border-clay-400 hover:text-clay-500 transition overflow-hidden"
            >
              {preview ? (
                <img src={preview} alt="Vorschau" className="w-full h-full object-cover" />
              ) : (
                <>
                  <span className="text-4xl">📷</span>
                  <span className="text-sm font-medium">Foto aufnehmen oder auswählen</span>
                </>
              )}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={handleFile}
            />

            {step === STEP.READY && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-1"
              >
                <label className="block text-xs font-medium text-ink-700/70 uppercase tracking-wide">
                  Hinweise für die KI
                  <span className="ml-1 font-normal normal-case text-ink-700/40">(optional)</span>
                </label>
                <input
                  type="text"
                  value={hint}
                  onChange={(e) => setHint(e.target.value)}
                  placeholder="z.B. Nike, Größe M, 100% Baumwolle, hellblau"
                  className="w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 text-ink-900 text-sm placeholder:text-ink-700/30 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
                />
                <p className="text-xs text-ink-700/40">
                  Marke, Größe, Material — hilft der KI bei genaueren Ergebnissen.
                </p>
              </motion.div>
            )}

            {step === STEP.READY && (
              <>
                <motion.button
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={analyze}
                  className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition"
                >
                  ✦ KI-Analyse starten
                </motion.button>
                <button
                  onClick={() => fileRef.current?.click()}
                  className="w-full text-center text-sm text-ink-700/50 hover:text-ink-900 transition"
                >
                  Anderes Foto wählen
                </button>
              </>
            )}
          </div>
        )}

        {/* ── Progress: Schritt 1 (Kategorie & Farbe) ── */}
        {step === STEP.QUICK && (
          <div className="space-y-4">
            {preview && (
              <img src={preview} alt="Vorschau" className="w-full aspect-[4/3] object-cover rounded-2xl" />
            )}
            <div className="bg-sand-100 rounded-2xl p-4">
              <div className="flex items-center gap-3 mb-3">
                <motion.div
                  className="w-5 h-5 border-2 border-clay-500 border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                />
                <span className="text-sm font-medium text-ink-900">Schritt 1/2: Kategorie wird erkannt …</span>
              </div>
              <div className="h-1.5 bg-sand-200 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-clay-500"
                  initial={{ width: "0%" }}
                  animate={{ width: "50%" }}
                  transition={{ duration: 0.6 }}
                />
              </div>
            </div>
          </div>
        )}

        {/* ── Progress: Schritt 2 (Details) ── */}
        {step === STEP.DETAIL && quickResult && (
          <div className="space-y-4">
            {preview && (
              <img src={preview} alt="Vorschau" className="w-full aspect-[4/3] object-cover rounded-2xl" />
            )}
            <div className="bg-sand-100 rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-ink-700/60 uppercase tracking-wide">Erkannt:</span>
                <span className="text-sm font-medium text-ink-900">
                  {quickResult.category} · {quickResult.color}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <motion.div
                  className="w-5 h-5 border-2 border-clay-500 border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                />
                <span className="text-sm font-medium text-ink-900">Schritt 2/2: Details werden analysiert …</span>
              </div>
              <div className="h-1.5 bg-sand-200 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-clay-500"
                  initial={{ width: "50%" }}
                  animate={{ width: "100%" }}
                  transition={{ duration: 1.2 }}
                />
              </div>
            </div>
          </div>
        )}

        {/* ── Bestätigen ── */}
        {(step === STEP.CONFIRM || step === STEP.SAVING) && metadata && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {preview && (
              <img src={preview} alt="Vorschau" className="w-full aspect-[4/3] object-cover rounded-2xl" />
            )}
            <p className="text-sm text-ink-700/70">
              Passt das? Du kannst alles anpassen, bevor du speicherst.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <TextField label="Name" value={metadata.name} onChange={(v) => update("name", v)} placeholder="z.B. Blaues Leinenhemd" />
              </div>
              <GroupedSelectField label="Kategorie" value={metadata.category} onChange={(v) => update("category", v)} groups={meta.category_groups} />
              <TextField label="Farbe" value={metadata.color} onChange={(v) => update("color", v)} />
              <SelectField label="Material" value={metadata.material} onChange={(v) => update("material", v)} options={meta.materials} />
              <TextField label="Muster / Textur" value={metadata.pattern} onChange={(v) => update("pattern", v)} />
              <SelectField label="Stil" value={metadata.style} onChange={(v) => update("style", v)} options={meta.styles} />
              <SelectField label="Anlass" value={metadata.occasion} onChange={(v) => update("occasion", v)} options={meta.occasions} />
              <div className="col-span-2">
                <SelectField label="Jahreszeit" value={metadata.season} onChange={(v) => update("season", v)} options={meta.seasons} />
              </div>
              <TextField label="Marke" value={metadata.brand} onChange={(v) => update("brand", v)} placeholder="z.B. Uniqlo" />
              <label className="block">
                <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
                  Stückzahl
                </span>
                <input
                  type="number"
                  min="1"
                  value={metadata.quantity ?? 1}
                  onChange={(e) => update("quantity", Math.max(1, Number(e.target.value) || 1))}
                  className="mt-1 w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 text-ink-900 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
                />
              </label>
              <div className="col-span-2">
                <TextField label="Beschreibung" value={metadata.description} onChange={(v) => update("description", v)} />
              </div>

              {/* Kategorienspezifische Detail-Felder */}
              {metadata.details && Object.keys(metadata.details).length > 0 && (
                <div className="col-span-2 pt-3 border-t border-sand-200">
                  <p className="text-xs font-medium text-ink-700/70 uppercase tracking-wide mb-3">
                    Spezifische Details
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(metadata.details).map(([key, value]) => (
                      <TextField
                        key={key}
                        label={key.replace(/_/g, ' ')}
                        value={value || ""}
                        onChange={(v) => {
                          setMetadata((m) => ({
                            ...m,
                            details: { ...m.details, [key]: v },
                          }));
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
            <button
              onClick={save}
              disabled={step === STEP.SAVING}
              className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60"
            >
              {step === STEP.SAVING ? "Speichern …" : "In Garderobe speichern"}
            </button>
          </motion.div>
        )}
      </div>
    </Modal>
  );
}
