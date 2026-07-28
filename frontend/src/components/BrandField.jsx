import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

/** Vergleichsschlüssel – muss zur Backend-Logik passen. */
function normalizeKey(s) {
  return (s || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

/**
 * Marken-Combobox: freie Eingabe mit Vorschlägen.
 * `mine` sind bereits verwendete Marken (werden zuerst gezeigt),
 * `suggestions` sind bekannte Marken.
 */
export default function BrandField({ label = "Marke", value, onChange, mine = [], suggestions = [] }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value || "");
  const wrapRef = useRef(null);

  // Externe Änderungen übernehmen
  useEffect(() => {
    setQuery(value || "");
  }, [value]);

  // Klick außerhalb schließt die Liste
  useEffect(() => {
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const { mineFiltered, suggFiltered, exactExists } = useMemo(() => {
    const q = normalizeKey(query);
    const match = (list) =>
      q ? list.filter((b) => normalizeKey(b).includes(q)) : list;

    const m = match(mine).slice(0, 8);
    const s = match(suggestions).slice(0, 8);
    const all = [...mine, ...suggestions];
    const exact = q ? all.some((b) => normalizeKey(b) === q) : true;

    return { mineFiltered: m, suggFiltered: s, exactExists: exact };
  }, [query, mine, suggestions]);

  function pick(brand) {
    setQuery(brand);
    onChange(brand);
    setOpen(false);
  }

  const hasOptions = mineFiltered.length > 0 || suggFiltered.length > 0;

  return (
    <div className="relative" ref={wrapRef}>
      <label className="block">
        <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
          {label}
          <span className="ml-1 font-normal normal-case text-ink-700/40">(optional)</span>
        </span>
        <div className="relative mt-1">
          <input
            type="text"
            value={query}
            onFocus={() => setOpen(true)}
            onChange={(e) => {
              setQuery(e.target.value);
              onChange(e.target.value);
              setOpen(true);
            }}
            onKeyDown={(e) => {
              if (e.key === "Escape") setOpen(false);
              if (e.key === "Enter") {
                e.preventDefault();
                // Erste Übereinstimmung übernehmen, sonst Freitext behalten
                const first = mineFiltered[0] || suggFiltered[0];
                if (first && !exactExists) pick(first);
                else setOpen(false);
              }
            }}
            placeholder="z.B. YoungLA, Marc O'Polo"
            autoComplete="off"
            className="w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 pr-8 text-ink-900 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
          />
          {query ? (
            <button
              type="button"
              onClick={() => pick("")}
              aria-label="Marke entfernen"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-700/40 hover:text-ink-900 text-lg leading-none"
            >
              ×
            </button>
          ) : (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-700/30 text-xs pointer-events-none">
              ▾
            </span>
          )}
        </div>
      </label>

      <AnimatePresence>
        {open && (hasOptions || (query.trim() && !exactExists)) && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute z-20 mt-1 w-full max-h-56 overflow-y-auto rounded-xl border border-sand-200 bg-white shadow-soft"
          >
            {/* Neue Marke anlegen */}
            {query.trim() && !exactExists && (
              <button
                type="button"
                onClick={() => pick(query.trim())}
                className="w-full text-left px-3 py-2.5 text-sm text-clay-600 hover:bg-sand-50 transition border-b border-sand-100"
              >
                <span className="font-medium">„{query.trim()}"</span> neu anlegen
              </button>
            )}

            {mineFiltered.length > 0 && (
              <div>
                <div className="px-3 pt-2 pb-1 text-[11px] font-semibold text-ink-700/40 uppercase tracking-wide">
                  Deine Marken
                </div>
                {mineFiltered.map((b) => (
                  <button
                    key={b}
                    type="button"
                    onClick={() => pick(b)}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-sand-50 transition ${
                      normalizeKey(b) === normalizeKey(query)
                        ? "text-clay-600 font-medium"
                        : "text-ink-800"
                    }`}
                  >
                    {b}
                  </button>
                ))}
              </div>
            )}

            {suggFiltered.length > 0 && (
              <div>
                <div className="px-3 pt-2 pb-1 text-[11px] font-semibold text-ink-700/40 uppercase tracking-wide">
                  Vorschläge
                </div>
                {suggFiltered.map((b) => (
                  <button
                    key={b}
                    type="button"
                    onClick={() => pick(b)}
                    className="w-full text-left px-3 py-2 text-sm text-ink-800 hover:bg-sand-50 transition"
                  >
                    {b}
                  </button>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
