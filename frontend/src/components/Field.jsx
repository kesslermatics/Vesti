// Wiederverwendbares Formularfeld: entweder Select (mit Optionen) oder Text-Input.
export function SelectField({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
        {label}
      </span>
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 text-ink-900 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
      >
        <option value="">–</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export function TextField({ label, value, onChange, placeholder }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
        {label}
      </span>
      <input
        type="text"
        value={value || ""}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 text-ink-900 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
      />
    </label>
  );
}
