import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";

const MODE = { SUGGEST: "suggest", FITCHECK: "fitcheck" };

function Spinner({ className = "w-4 h-4 border-clay-500" }) {
  return (
    <motion.span
      className={`inline-block border-2 border-t-transparent rounded-full ${className}`}
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
    />
  );
}

/* ─────────────── Vorschläge ─────────────── */
function Suggest() {
  const [direction, setDirection] = useState("");
  const [history, setHistory] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run(text) {
    setLoading(true);
    setError("");
    try {
      const res = await api.shoppingSuggest({ direction: text, history });
      setResult(res);
      setHistory((h) => [
        ...h,
        { role: "user", content: text || "Was fehlt meiner Garderobe?" },
        {
          role: "assistant",
          content:
            (res.intro ? res.intro + " " : "") +
            res.suggestions.map((s) => s.title).join(", "),
        },
      ]);
      setDirection("");
    } catch (err) {
      setError(err.message || "Vorschläge fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* Chat-Verlauf */}
      {history.length > 0 && (
        <div className="space-y-2">
          {history.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={`text-sm rounded-2xl px-4 py-2.5 max-w-[85%] ${
                m.role === "user"
                  ? "bg-clay-500 text-white ml-auto"
                  : "bg-white text-ink-800 shadow-soft"
              }`}
            >
              {m.content}
            </motion.div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3">{error}</div>
      )}

      {/* Vorschläge */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-3"
        >
          {result.intro && (
            <div className="rounded-2xl bg-sand-100 p-4 text-sm text-ink-800 leading-relaxed">
              {result.intro}
            </div>
          )}
          {result.suggestions.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="bg-white rounded-2xl shadow-soft p-4"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <h4 className="font-medium text-ink-900 leading-snug">{s.title}</h4>
                <span className="shrink-0 text-xs bg-sand-100 text-ink-700 rounded-full px-2.5 py-1">
                  {s.category}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {[s.color, s.material].filter(Boolean).map((t, j) => (
                  <span key={j} className="text-xs text-ink-700/60">
                    {t}
                  </span>
                ))}
              </div>
              <p className="text-sm text-ink-700/80 leading-relaxed">{s.reason}</p>
              {s.combines_with?.length > 0 && (
                <p className="mt-2 text-xs text-clay-600">
                  Passt zu: {s.combines_with.join(", ")}
                </p>
              )}
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Eingabe */}
      <div className="space-y-2">
        <input
          type="text"
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !loading) run(direction.trim());
          }}
          placeholder={
            result
              ? "Nachfragen, z.B. 'eher fürs Büro' oder 'nur Schuhe'"
              : "Richtung (optional), z.B. 'Sommer, casual'"
          }
          className="w-full rounded-xl border border-sand-200 bg-white px-4 py-3 text-sm focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
        />
        <button
          onClick={() => run(direction.trim())}
          disabled={loading}
          className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Spinner className="w-4 h-4 border-white" />
              Analysiere deine Garderobe …
            </>
          ) : result ? (
            "Neue Vorschläge"
          ) : (
            "✦ Vorschläge holen"
          )}
        </button>
      </div>
    </div>
  );
}

/* ─────────────── Fit Check ─────────────── */
function FitCheck() {
  const [text, setText] = useState("");
  const [image, setImage] = useState(null); // {base64, mime, preview}
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  function handleFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = String(reader.result).split(",")[1] || "";
      setImage({ base64, mime: f.type || "image/jpeg", preview: URL.createObjectURL(f) });
    };
    reader.readAsDataURL(f);
    e.target.value = "";
  }

  async function run() {
    if (!text.trim()) {
      setError("Bitte die Produktbeschreibung einfügen.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.fitCheck({
        product_text: text,
        image_base64: image?.base64 || "",
        image_mime: image?.mime || "",
      });
      setResult(res);
    } catch (err) {
      setError(err.message || "Fit-Check fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  const scoreColor =
    result == null
      ? ""
      : result.score >= 70
      ? "text-emerald-600"
      : result.score >= 40
      ? "text-amber-600"
      : "text-clay-600";

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-700/70">
        Kopiere die komplette Produktbeschreibung aus dem Shop (Uniqlo, YoungLA, Zalando …) hier
        rein – gerne inklusive Material, Maßtabelle und Größenangaben.
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={7}
        placeholder="Produktname, Material, Maße, Größenangaben, Beschreibung …"
        className="w-full rounded-xl border border-sand-200 bg-white px-4 py-3 text-sm focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition resize-none"
      />

      {/* Optionales Bild */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => fileRef.current?.click()}
          className="flex-1 rounded-xl border border-dashed border-sand-200 bg-white py-3 text-sm text-ink-700/60 hover:border-clay-400 hover:text-clay-500 transition"
        >
          {image ? "Bild ersetzen" : "📷 Produktbild hinzufügen (optional)"}
        </button>
        {image && (
          <div className="relative shrink-0">
            <img
              src={image.preview}
              alt="Produkt"
              className="w-14 h-14 object-cover rounded-xl shadow-soft"
            />
            <button
              onClick={() => setImage(null)}
              aria-label="Bild entfernen"
              className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-ink-900 text-white text-xs leading-none"
            >
              ×
            </button>
          </div>
        )}
      </div>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />

      {error && (
        <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3">{error}</div>
      )}

      <button
        onClick={run}
        disabled={loading}
        className="w-full rounded-xl bg-clay-500 text-white font-medium py-3 hover:bg-clay-600 active:scale-[0.99] transition disabled:opacity-60 flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Spinner className="w-4 h-4 border-white" />
            Prüfe gegen deine Garderobe …
          </>
        ) : (
          "✦ Fit Check starten"
        )}
      </button>

      {/* Ergebnis */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            {/* Score */}
            <div className="bg-white rounded-2xl shadow-soft p-5 text-center">
              <div className={`text-5xl font-bold ${scoreColor}`}>
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.15 }}
                >
                  {result.score}%
                </motion.span>
              </div>
              <p className="mt-1 text-sm font-medium text-ink-900">{result.verdict}</p>
              <div className="mt-4 h-2 bg-sand-100 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full ${
                    result.score >= 70
                      ? "bg-emerald-500"
                      : result.score >= 40
                      ? "bg-amber-500"
                      : "bg-clay-500"
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${result.score}%` }}
                  transition={{ duration: 0.7, ease: "easeOut" }}
                />
              </div>
            </div>

            {/* Begründung */}
            <div className="bg-sand-100 rounded-2xl p-4 text-sm text-ink-800 leading-relaxed">
              {result.explanation}
            </div>

            {/* Pro / Contra */}
            {(result.pros?.length > 0 || result.cons?.length > 0) && (
              <div className="grid sm:grid-cols-2 gap-3">
                {result.pros?.length > 0 && (
                  <div className="bg-white rounded-2xl shadow-soft p-4">
                    <h4 className="text-xs font-semibold text-emerald-600 uppercase tracking-wide mb-2">
                      Spricht dafür
                    </h4>
                    <ul className="space-y-1.5">
                      {result.pros.map((p, i) => (
                        <li key={i} className="text-sm text-ink-800 flex gap-2">
                          <span className="text-emerald-600">+</span>
                          {p}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.cons?.length > 0 && (
                  <div className="bg-white rounded-2xl shadow-soft p-4">
                    <h4 className="text-xs font-semibold text-clay-600 uppercase tracking-wide mb-2">
                      Spricht dagegen
                    </h4>
                    <ul className="space-y-1.5">
                      {result.cons.map((c, i) => (
                        <li key={i} className="text-sm text-ink-800 flex gap-2">
                          <span className="text-clay-600">−</span>
                          {c}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Größe */}
            {result.size_advice && (
              <div className="bg-white rounded-2xl shadow-soft p-4">
                <h4 className="text-xs font-semibold text-ink-900 uppercase tracking-wide mb-1.5">
                  Größenempfehlung
                </h4>
                <p className="text-sm text-ink-800 leading-relaxed">{result.size_advice}</p>
              </div>
            )}

            {/* Kombiniert mit */}
            {result.combines_with?.length > 0 && (
              <div className="bg-white rounded-2xl shadow-soft p-4">
                <h4 className="text-xs font-semibold text-ink-900 uppercase tracking-wide mb-2">
                  Kombinierbar mit
                </h4>
                <div className="flex flex-wrap gap-2">
                  {result.combines_with.map((c, i) => (
                    <span
                      key={i}
                      className="text-xs bg-sand-100 text-ink-700 rounded-full px-3 py-1"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─────────────── Wrapper ─────────────── */
export default function Shopping() {
  const [mode, setMode] = useState(MODE.SUGGEST);

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      {/* Umschalter */}
      <div className="flex bg-sand-100 rounded-xl p-1 mb-5">
        {[
          [MODE.SUGGEST, "Vorschläge"],
          [MODE.FITCHECK, "Fit Check"],
        ].map(([m, label]) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
              mode === m ? "bg-white text-ink-900 shadow-sm" : "text-ink-700/60"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {mode === MODE.SUGGEST ? <Suggest /> : <FitCheck />}
    </motion.div>
  );
}
