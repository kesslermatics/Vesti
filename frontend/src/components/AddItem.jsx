import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../api";
import Modal from "./Modal";
import { SelectField, TextField } from "./Field";

const STEP = {
  UPLOAD: "upload",       // Foto auswählen
  READY: "ready",         // Foto gewählt, Hinweis eingeben, Analyse-Button
  ANALYZING: "analyzing", // KI läuft
  CONFIRM: "confirm",     // Metadaten bestätigen
  SAVING: "saving",
};

export default function AddItem({ open, onClose, meta, onCreated }) {
  const [step, setStep] = useState(STEP.UPLOAD);
  const [preview, setPreview] = useState(null);
  const [file, setFile] = useState(null);
  const [hint, setHint] = useState("");
  const [metadata, setMetadata] = useState(null);
  const [image, setImage] = useState({ base64: "", mime: "" });
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  function reset() {
    setStep(STEP.UPLOAD);
    setPreview(null);
    setFile(null);
    setHint("");
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
    // Input zurücksetzen, damit dieselbe Datei nochmal wählbar ist
    e.target.value = "";
  }

  async function analyze() {
    if (!file) return;
    setError("");
    setStep(STEP.ANALYZING);
    try {
      const res = await api.analyze(file, hint.trim());
      setMetadata(res.metadata);
      setImage({ base64: res.image_base64, mime: res.image_mime });
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
        {/* Header */}
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

        {/* ── Schritt 1 & 2: Foto + Hinweis ── */}
        {(step === STEP.UPLOAD || step === STEP.READY || step === STEP.ANALYZING) && (
          <div className="space-y-4">
            {/* Foto-Fläche */}
            <button
              onClick={() => fileRef.current?.click()}
              disabled={step === STEP.ANALYZING}
              className="w-full aspect-[4/3] rounded-2xl border-2 border-dashed border-sand-200 bg-white flex flex-col items-center justify-center gap-2 text-ink-700/60 hover:border-clay-400 hover:text-clay-500 transition overflow-hidden"
            >
              {preview ? (
                <>
                  <img src={preview} alt="Vorschau" className="w-full h-full object-cover" />
                </>
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

            {/* Hinweis-Feld — erscheint sobald ein Foto gewählt ist */}
            {(step === STEP.READY || step === STEP.ANALYZING) && (
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
                  disabled={step === STEP.ANALYZING}
                  placeholder="z.B. Nike, Größe M, 100% Baumwolle, hellblau"
                  className="w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 text-ink-900 text-sm placeholder:text-ink-700/30 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition disabled:opacity-50"
                />
                <p className="text-xs text-ink-700/40">
                  Marke, Größe, Material — hilft der KI bei genaueren Ergebnissen.
                </p>
              </motion.div>
            )}

            {/* Analyse-Button */}
            {step === STEP.READY && (
              <motion.button
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={analyze}
                className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition"
              >
                ✦ KI-Analyse starten
              </motion.button>
            )}

            {/* Foto wechseln (nur im READY-Zustand) */}
            {step === STEP.READY && (
              <button
                onClick={() => fileRef.current?.click()}
                className="w-full text-center text-sm text-ink-700/50 hover:text-ink-900 transition"
              >
                Anderes Foto wählen
              </button>
            )}

            {/* Spinner */}
            {step === STEP.ANALYZING && (
              <div className="flex items-center justify-center gap-2 text-clay-500 text-sm">
                <motion.span
                  className="inline-block w-4 h-4 border-2 border-clay-500 border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                />
                KI analysiert dein Kleidungsstück …
              </div>
            )}
          </div>
        )}

        {/* ── Schritt 3: Metadaten bestätigen ── */}
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
              <SelectField label="Kategorie" value={metadata.category} onChange={(v) => update("category", v)} options={meta.categories} />
              <TextField label="Farbe" value={metadata.color} onChange={(v) => update("color", v)} />
              <SelectField label="Material" value={metadata.material} onChange={(v) => update("material", v)} options={meta.materials} />
              <TextField label="Muster / Textur" value={metadata.pattern} onChange={(v) => update("pattern", v)} />
              <SelectField label="Stil" value={metadata.style} onChange={(v) => update("style", v)} options={meta.styles} />
              <SelectField label="Anlass" value={metadata.occasion} onChange={(v) => update("occasion", v)} options={meta.occasions} />
              <div className="col-span-2">
                <SelectField label="Jahreszeit" value={metadata.season} onChange={(v) => update("season", v)} options={meta.seasons} />
              </div>
              <div className="col-span-2">
                <TextField label="Beschreibung" value={metadata.description} onChange={(v) => update("description", v)} />
              </div>
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
