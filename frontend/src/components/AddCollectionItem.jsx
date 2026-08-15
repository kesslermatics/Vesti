import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, fileToBase64 } from "../api";
import { FragranceFields, WatchFields } from "./CollectionForm";

const STEP = {
  CAPTURE: "capture",
  ANALYZING: "analyzing",
  CONFIRM: "confirm",
  DONE: "done",
};

const MAX_IMAGES = 6;

// Alles, was pro Sammlung unterschiedlich ist, liegt hier gebündelt.
// Der Wizard selbst ist für Uhren und Düfte identisch.
const KINDS = {
  watch: {
    title: "Neue Uhr",
    icon: "⌚",
    emptyHint:
      "Fotografiere das Zifferblatt und wenn möglich den Gehäuseboden. Dort steht meist die Referenznummer – damit erkennt die KI das exakte Modell und kennt dann auch Werk, Durchmesser und Wasserdichte.",
    hintPlaceholder: "z.B. Omega, 42 mm, von 2021",
    analysisRows: [
      "Zifferblatt und Gravuren lesen",
      "Technische Daten zum Modell ergänzen",
      "Uhr in Szene setzen",
    ],
    fields: WatchFields,
    loadBrands: () => api.getWatchBrands(),
    analyze: (payload) => api.analyzeWatch(payload),
    shot: (data) =>
      api.analyzeWatchShot({
        images: data.images,
        brand: data.brand,
        model: data.model,
        dial_color: data.dial_color,
        case_material: data.case_material,
        band_material: data.band_material,
      }),
    create: (payload) => api.createWatch(payload),
    label: (data) =>
      [data.brand, data.model].filter(Boolean).join(" ") || data.name || "Uhr",
    identifiedHint: "Modell erkannt – die technischen Daten stammen aus dem Modellwissen.",
    unidentifiedHint:
      "Das genaue Modell war nicht lesbar. Die Angaben sind optisch geschätzt, prüfe sie bitte.",
  },
  fragrance: {
    title: "Neuer Duft",
    icon: "🧴",
    emptyHint:
      "Ein Duft ist auf einem Foto nicht riechbar – die KI liest das Etikett. Fotografiere den Flakon so, dass Name und Konzentration klar zu lesen sind, dann kennt sie auch die Duftpyramide.",
    hintPlaceholder: "z.B. Dior Sauvage Elixir, 60 ml",
    analysisRows: [
      "Etikett und Verpackung lesen",
      "Duftpyramide und Charakter ergänzen",
      "Flakon in Szene setzen",
    ],
    fields: FragranceFields,
    loadBrands: () => api.getFragranceBrands(),
    analyze: (payload) => api.analyzeFragrance(payload),
    shot: (data) =>
      api.analyzeFragranceShot({
        images: data.images,
        brand: data.brand,
        name: data.name,
        family: data.family,
      }),
    create: (payload) => api.createFragrance(payload),
    label: (data) => [data.brand, data.name].filter(Boolean).join(" ") || "Duft",
    identifiedHint: "Duft erkannt – Duftpyramide und Charakter stammen aus dem Modellwissen.",
    unidentifiedHint:
      "Der Duft war nicht eindeutig lesbar. Die Noten wurden bewusst leer gelassen, statt sie zu erfinden – trage sie gerne selbst ein.",
  },
};

function AnalysisRow({ active, done, label }) {
  return (
    <div className="flex items-center gap-3">
      <span
        className={`w-5 h-5 flex-shrink-0 rounded-full flex items-center justify-center text-[10px] ${
          done
            ? "bg-clay-500 text-white"
            : active
            ? "bg-clay-500/15 text-clay-600"
            : "bg-sand-100 text-ink-700/30"
        }`}
      >
        {done ? "✓" : active ? "•" : ""}
      </span>
      <span
        className={`text-sm ${
          done ? "text-ink-900" : active ? "text-ink-900 font-medium" : "text-ink-700/40"
        }`}
      >
        {label}
      </span>
      {active && (
        <motion.span
          className="inline-block w-3.5 h-3.5 border-2 border-clay-500 border-t-transparent rounded-full ml-auto"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
        />
      )}
    </div>
  );
}

export default function AddCollectionItem({ open, kind, onClose, meta, onCreated }) {
  const config = KINDS[kind] || KINDS.watch;

  const [step, setStep] = useState(STEP.CAPTURE);
  const [images, setImages] = useState([]); // [{ file, url, id }]
  const [hint, setHint] = useState("");
  const [phase, setPhase] = useState(0);
  const [data, setData] = useState(null);
  const [encoded, setEncoded] = useState([]);
  const [identified, setIdentified] = useState(false);
  const [confidence, setConfidence] = useState("");
  const [aiImage, setAiImage] = useState(null);
  const [regenerating, setRegenerating] = useState(false);
  const [showOriginal, setShowOriginal] = useState(false);
  const [brands, setBrands] = useState({ mine: [], suggestions: [] });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);
  const cameraRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    config.loadBrands().then(setBrands).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, kind]);

  function reset() {
    images.forEach((img) => URL.revokeObjectURL(img.url));
    setStep(STEP.CAPTURE);
    setImages([]);
    setHint("");
    setPhase(0);
    setData(null);
    setEncoded([]);
    setIdentified(false);
    setConfidence("");
    setAiImage(null);
    setRegenerating(false);
    setShowOriginal(false);
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
      // Bilder als base64 hochschicken – Uhren und Düfte brauchen nur einen
      // Analyse-Durchgang, weil die Identifikation über die Schrift läuft.
      const payloadImages = await Promise.all(
        images.map(async (img) => ({
          image_base64: await fileToBase64(img.file),
          image_mime: img.file.type || "image/jpeg",
        }))
      );
      setEncoded(payloadImages);

      setPhase(1);
      const result = await config.analyze({
        images: payloadImages,
        hint: hint.trim(),
      });

      setData(result.metadata);
      setIdentified(result.identified);
      setConfidence(result.confidence || "");

      setPhase(2);
      try {
        const shot = await config.shot({ ...result.metadata, images: payloadImages });
        if (shot?.ai_image_base64) {
          setAiImage({ base64: shot.ai_image_base64, mime: shot.ai_image_mime });
        }
      } catch {
        // Inszenierung ist optional
      }

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

  function update(key, value) {
    setData((d) => ({ ...d, [key]: value }));
  }

  async function regenerateShot() {
    if (!encoded.length || !data) return;
    setRegenerating(true);
    setError("");
    try {
      const shot = await config.shot({ ...data, images: encoded });
      if (shot?.ai_image_base64) {
        setAiImage({ base64: shot.ai_image_base64, mime: shot.ai_image_mime });
        setShowOriginal(false);
      }
    } catch (err) {
      setError(err.message || "Bildgenerierung fehlgeschlagen.");
    } finally {
      setRegenerating(false);
    }
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      const [primary, ...rest] = encoded;
      const created = await config.create({
        ...data,
        image_base64: primary.image_base64,
        image_mime: primary.image_mime,
        extra_images: rest,
        ai_image_base64: aiImage?.base64 || "",
        ai_image_mime: aiImage?.mime || "image/png",
      });
      setStep(STEP.DONE);
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
    step === STEP.CAPTURE
      ? 0.12
      : step === STEP.ANALYZING
      ? phase === 0
        ? 0.3
        : phase === 1
        ? 0.6
        : 0.85
      : 1;

  const shotHints =
    (kind === "watch" ? meta?.watches?.shot_hints : meta?.fragrances?.shot_hints) || [];
  const Fields = config.fields;

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
                  {config.icon} {config.title}
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
                      {config.emptyHint}
                    </p>

                    {shotHints.length > 0 && (
                      <div className="grid grid-cols-4 gap-2">
                        {shotHints.map((s, i) => (
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
                    )}

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
                            className="relative aspect-square rounded-2xl overflow-hidden bg-white shadow-soft"
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
                        <motion.div
                          layout
                          className="aspect-square rounded-2xl border-2 border-dashed border-sand-200 bg-white flex flex-col items-center justify-center gap-1.5 text-ink-700/50"
                        >
                          <motion.button
                            whileTap={{ scale: 0.92 }}
                            onClick={() => cameraRef.current?.click()}
                            className="flex flex-col items-center gap-0.5 hover:text-clay-500 transition"
                          >
                            <span className="text-2xl leading-none">📷</span>
                            <span className="text-[10px] font-medium">Kamera</span>
                          </motion.button>
                          <div className="w-px h-3 bg-sand-200" />
                          <motion.button
                            whileTap={{ scale: 0.92 }}
                            onClick={() => fileRef.current?.click()}
                            className="flex flex-col items-center gap-0.5 hover:text-clay-500 transition"
                          >
                            <span className="text-2xl leading-none">🖼️</span>
                            <span className="text-[10px] font-medium">Galerie</span>
                          </motion.button>
                        </motion.div>
                      )}
                    </div>

                    <input
                      ref={cameraRef}
                      type="file"
                      accept="image/*"
                      capture="environment"
                      className="hidden"
                      onChange={addFiles}
                    />
                    <input
                      ref={fileRef}
                      type="file"
                      accept="image/*"
                      multiple
                      className="hidden"
                      onChange={addFiles}
                    />

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
                            placeholder={config.hintPlaceholder}
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
                    <div className="relative mx-auto w-48 h-48">
                      {images.slice(0, 3).map((img, i) => (
                        <motion.img
                          key={img.id}
                          src={img.url}
                          alt=""
                          className="absolute inset-0 w-full h-full object-cover rounded-3xl shadow-soft"
                          style={{ zIndex: 3 - i }}
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
                      {config.analysisRows.map((label, i) => (
                        <AnalysisRow
                          key={label}
                          active={phase === i + 1 || (phase === 0 && i === 0)}
                          done={phase > i + 1}
                          label={label}
                        />
                      ))}
                    </div>

                    <p className="text-center text-xs text-ink-700/50">
                      {images.length > 1
                        ? `${images.length} Aufnahmen werden gemeinsam ausgewertet`
                        : "Einen Moment noch"}
                    </p>
                  </motion.div>
                )}

                {/* ══ Bestätigen ══ */}
                {step === STEP.CONFIRM && data && (
                  <motion.div
                    key="confirm"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-5"
                  >
                    {aiImage && (
                      <div className="space-y-2">
                        <div className="relative rounded-2xl overflow-hidden bg-white shadow-soft">
                          <AnimatePresence mode="wait">
                            <motion.img
                              key={showOriginal ? "orig" : "ai"}
                              src={
                                showOriginal
                                  ? images[0]?.url
                                  : `data:${aiImage.mime};base64,${aiImage.base64}`
                              }
                              alt={showOriginal ? "Original" : "KI-Produktfoto"}
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              exit={{ opacity: 0 }}
                              transition={{ duration: 0.18 }}
                              className="w-full aspect-square object-cover"
                            />
                          </AnimatePresence>
                          {regenerating && (
                            <div className="absolute inset-0 bg-white/70 backdrop-blur-sm flex flex-col items-center justify-center gap-2">
                              <motion.span
                                className="inline-block w-6 h-6 border-2 border-clay-500 border-t-transparent rounded-full"
                                animate={{ rotate: 360 }}
                                transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                              />
                              <span className="text-xs text-ink-700">Neu generieren …</span>
                            </div>
                          )}
                          <span className="absolute top-2 left-2 bg-ink-900/70 text-white text-[10px] font-medium rounded-full px-2 py-0.5 backdrop-blur-sm">
                            {showOriginal ? "📷 Dein Foto" : "✨ In Szene gesetzt"}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <div className="flex-1 flex rounded-xl bg-sand-100 p-0.5 text-xs font-medium">
                            <button
                              onClick={() => setShowOriginal(false)}
                              className={`flex-1 rounded-lg py-1.5 transition ${
                                !showOriginal
                                  ? "bg-white shadow-sm text-ink-900"
                                  : "text-ink-700/60"
                              }`}
                            >
                              ✨ Inszeniert
                            </button>
                            <button
                              onClick={() => setShowOriginal(true)}
                              className={`flex-1 rounded-lg py-1.5 transition ${
                                showOriginal
                                  ? "bg-white shadow-sm text-ink-900"
                                  : "text-ink-700/60"
                              }`}
                            >
                              📷 Original
                            </button>
                          </div>
                          <button
                            onClick={regenerateShot}
                            disabled={regenerating}
                            className="rounded-xl border border-sand-200 bg-white px-3 py-2 text-xs font-medium text-ink-700 hover:bg-sand-50 transition disabled:opacity-50 flex items-center gap-1.5"
                          >
                            <span className={regenerating ? "animate-spin" : ""}>🔄</span>
                            Neu
                          </button>
                        </div>
                      </div>
                    )}

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

                    {!aiImage && (
                      <button
                        onClick={regenerateShot}
                        disabled={regenerating}
                        className="w-full rounded-xl border border-dashed border-clay-400 bg-clay-500/5 px-4 py-3 text-sm font-medium text-clay-600 hover:bg-clay-500/10 transition disabled:opacity-50 flex items-center justify-center gap-2"
                      >
                        {regenerating ? (
                          <>
                            <motion.span
                              className="inline-block w-4 h-4 border-2 border-clay-500 border-t-transparent rounded-full"
                              animate={{ rotate: 360 }}
                              transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                            />
                            Wird in Szene gesetzt …
                          </>
                        ) : (
                          <>✨ In Szene setzen</>
                        )}
                      </button>
                    )}

                    {/* Ehrlichkeit über die Erkennungsqualität */}
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        identified ? "bg-clay-500/8" : "bg-amber-400/10"
                      }`}
                    >
                      <p className="text-sm text-ink-800">
                        {identified ? config.identifiedHint : config.unidentifiedHint}
                      </p>
                      {confidence && (
                        <p className="text-xs text-ink-700/50 mt-1">
                          Sicherheit der Erkennung: {confidence}
                        </p>
                      )}
                    </div>

                    <Fields data={data} update={update} meta={meta} brands={brands} />
                  </motion.div>
                )}

                {/* ══ Fertig ══ */}
                {step === STEP.DONE && (
                  <motion.div
                    key="done"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="py-20 text-center"
                  >
                    <div className="text-5xl mb-3">{config.icon}</div>
                    <h3 className="text-lg font-semibold text-ink-900">
                      {config.label(data || {})} gespeichert
                    </h3>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* ── Fuß mit Aktion ── */}
          {step !== STEP.DONE && (
            <div
              className="flex-shrink-0 px-5 pt-3 border-t border-sand-100 bg-sand-50/90 backdrop-blur-md"
              style={{ paddingBottom: "max(env(safe-area-inset-bottom), 1rem)" }}
            >
              <div className="max-w-lg mx-auto">
                {step === STEP.CAPTURE && (
                  <button
                    onClick={analyze}
                    disabled={!images.length}
                    className="w-full rounded-xl bg-clay-500 text-white font-medium py-3.5 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-40"
                  >
                    {images.length
                      ? `${images.length} ${
                          images.length === 1 ? "Aufnahme" : "Aufnahmen"
                        } analysieren`
                      : "Mindestens eine Aufnahme nötig"}
                  </button>
                )}
                {step === STEP.CONFIRM && (
                  <button
                    onClick={save}
                    disabled={saving}
                    className="w-full rounded-xl bg-clay-500 text-white font-medium py-3.5 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60 flex items-center justify-center gap-2"
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
                      "Zur Sammlung hinzufügen"
                    )}
                  </button>
                )}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
