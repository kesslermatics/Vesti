import { motion } from "framer-motion";

/** Kleine Kennzahl-Karte */
export function StatCard({ label, value, sub, accent = false }) {
  return (
    <div
      className={`rounded-2xl p-4 ${
        accent ? "bg-clay-500 text-white" : "bg-white shadow-soft"
      }`}
    >
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className={`text-2xl font-bold ${accent ? "text-white" : "text-ink-900"}`}
      >
        {value}
      </motion.div>
      <div className={`text-xs mt-0.5 ${accent ? "text-white/80" : "text-ink-700/60"}`}>
        {label}
      </div>
      {sub && (
        <div className={`text-[11px] mt-1 ${accent ? "text-white/60" : "text-ink-700/40"}`}>
          {sub}
        </div>
      )}
    </div>
  );
}

/** Horizontales Balkendiagramm */
export function BarList({ data, max, colorKey, emptyText = "Keine Daten" }) {
  if (!data?.length) {
    return <p className="text-sm text-ink-700/40">{emptyText}</p>;
  }
  const peak = max ?? Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="space-y-2.5">
      {data.map((d, i) => (
        <div key={d.label}>
          <div className="flex items-baseline justify-between mb-1">
            <span className="text-sm text-ink-800 capitalize">{d.label}</span>
            <span className="text-xs text-ink-700/50 tabular-nums">
              {d.count}
              {d.share != null && <span className="ml-1.5 text-ink-700/30">{d.share}%</span>}
            </span>
          </div>
          <div className="h-2 bg-sand-100 rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ background: colorKey ? d[colorKey] : undefined }}
              initial={{ width: 0 }}
              animate={{ width: `${(d.count / peak) * 100}%` }}
              transition={{ duration: 0.6, delay: i * 0.05, ease: "easeOut" }}
            >
              {!colorKey && <div className="h-full w-full bg-clay-500 rounded-full" />}
            </motion.div>
          </div>
        </div>
      ))}
    </div>
  );
}

/** Farbpalette als Streifen mit Anteilen */
export function ColorBar({ colors }) {
  if (!colors?.length) return null;

  return (
    <div className="space-y-3">
      <div className="flex h-3 rounded-full overflow-hidden">
        {colors.map((c, i) => (
          <motion.div
            key={c.label}
            className="h-full first:rounded-l-full last:rounded-r-full"
            style={{ background: c.hex }}
            initial={{ width: 0 }}
            animate={{ width: `${c.share}%` }}
            transition={{ duration: 0.6, delay: i * 0.04 }}
            title={`${c.label} ${c.share}%`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1.5">
        {colors.map((c) => (
          <div key={c.label} className="flex items-center gap-1.5">
            <span
              className="w-3 h-3 rounded-full border border-ink-900/10 shrink-0"
              style={{ background: c.hex }}
            />
            <span className="text-xs text-ink-800">{c.label}</span>
            <span className="text-xs text-ink-700/40 tabular-nums">{c.share}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Saison-Abdeckung als Ring-Segmente */
export function SeasonRings({ seasons, totalPieces }) {
  const icons = { Frühling: "🌱", Sommer: "☀️", Herbst: "🍂", Winter: "❄️" };

  return (
    <div className="grid grid-cols-4 gap-3">
      {seasons.map((s, i) => {
        const pct = totalPieces ? Math.min(100, (s.count / totalPieces) * 100) : 0;
        const r = 26;
        const circ = 2 * Math.PI * r;
        return (
          <div key={s.label} className="flex flex-col items-center">
            <div className="relative w-16 h-16">
              <svg viewBox="0 0 64 64" className="w-full h-full -rotate-90">
                <circle cx="32" cy="32" r={r} fill="none" stroke="#f3ede4" strokeWidth="6" />
                <motion.circle
                  cx="32"
                  cy="32"
                  r={r}
                  fill="none"
                  stroke="#b9734f"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={circ}
                  initial={{ strokeDashoffset: circ }}
                  animate={{ strokeDashoffset: circ - (pct / 100) * circ }}
                  transition={{ duration: 0.8, delay: i * 0.08, ease: "easeOut" }}
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-lg">
                {icons[s.label]}
              </span>
            </div>
            <span className="mt-1 text-xs font-medium text-ink-900">{s.count}</span>
            <span className="text-[11px] text-ink-700/50">{s.label}</span>
          </div>
        );
      })}
    </div>
  );
}

/** Score-Ring für die KI-Bewertung */
export function ScoreRing({ score, label }) {
  const r = 46;
  const circ = 2 * Math.PI * r;
  const color = score >= 70 ? "#5f8f57" : score >= 45 ? "#c79445" : "#b9734f";

  return (
    <div className="relative w-32 h-32 mx-auto">
      <svg viewBox="0 0 112 112" className="w-full h-full -rotate-90">
        <circle cx="56" cy="56" r={r} fill="none" stroke="#f3ede4" strokeWidth="8" />
        <motion.circle
          cx="56"
          cy="56"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - (score / 100) * circ }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-3xl font-bold"
          style={{ color }}
        >
          {score}
        </motion.span>
        {label && <span className="text-[11px] text-ink-700/50 mt-0.5">{label}</span>}
      </div>
    </div>
  );
}
