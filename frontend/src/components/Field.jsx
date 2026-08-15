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

export function GroupedSelectField({ label, value, onChange, groups }) {
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
        {groups.map((grp) => (
          <optgroup key={grp.group} label={grp.group}>
            {grp.items.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </optgroup>
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

// Zahlenfeld mit optionaler Einheit (z.B. Gehäusedurchmesser in mm)
export function NumberField({ label, value, onChange, unit, placeholder, step = "any", min, max }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
        {label}
      </span>
      <div className="relative mt-1">
        <input
          type="number"
          inputMode="decimal"
          step={step}
          min={min}
          max={max}
          value={value ?? ""}
          placeholder={placeholder}
          onChange={(e) => {
            const raw = e.target.value;
            onChange(raw === "" ? null : Number(raw));
          }}
          className={`w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 text-ink-900 placeholder:text-ink-700/30 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition ${
            unit ? "pr-12" : ""
          }`}
        />
        {unit && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-ink-700/40 pointer-events-none">
            {unit}
          </span>
        )}
      </div>
    </label>
  );
}

// Datumsfeld. Speichert als ISO-Datum, zeigt den nativen Date-Picker.
export function DateField({ label, value, onChange }) {
  // Backend liefert ISO mit Uhrzeit, das Input braucht YYYY-MM-DD
  const asDate = value ? String(value).slice(0, 10) : "";
  return (
    <label className="block">
      <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
        {label}
      </span>
      <input
        type="date"
        value={asDate}
        onChange={(e) => onChange(e.target.value || null)}
        className="mt-1 w-full rounded-xl border border-sand-200 bg-white px-3 py-2.5 text-ink-900 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
      />
    </label>
  );
}

// Mehrfachauswahl als antippbare Chips – für kurze Optionslisten
// (Anlässe, Jahreszeiten, Komplikationen).
export function ChipMultiSelect({ label, value = [], onChange, options, hint }) {
  const selected = Array.isArray(value) ? value : [];

  function toggle(option) {
    onChange(
      selected.includes(option)
        ? selected.filter((v) => v !== option)
        : [...selected, option]
    );
  }

  return (
    <div className="block">
      <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
        {label}
      </span>
      {hint && <p className="text-[11px] text-ink-700/40 mt-0.5">{hint}</p>}
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {options.map((option) => {
          const active = selected.includes(option);
          return (
            <button
              key={option}
              type="button"
              onClick={() => toggle(option)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                active
                  ? "bg-clay-500 text-white"
                  : "bg-sand-100 text-ink-700/70 hover:bg-sand-200"
              }`}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Freie Mehrfacheingabe mit Vorschlägen – für Duftnoten.
// Die Notenliste ist bewusst unvollständig, deshalb sind eigene Einträge erlaubt:
// eine korrekt gelesene, seltene Note ist wertvoller als eine verworfene.
export function TokenField({ label, value = [], onChange, suggestions = [], placeholder }) {
  const selected = Array.isArray(value) ? value : [];
  const listId = `tokens-${label.replace(/\s+/g, "-").toLowerCase()}`;

  function add(raw) {
    const entry = (raw || "").trim();
    if (!entry) return;
    if (selected.some((v) => v.toLowerCase() === entry.toLowerCase())) return;
    onChange([...selected, entry]);
  }

  function remove(entry) {
    onChange(selected.filter((v) => v !== entry));
  }

  function onKeyDown(e) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(e.target.value);
      e.target.value = "";
    } else if (e.key === "Backspace" && !e.target.value && selected.length) {
      remove(selected[selected.length - 1]);
    }
  }

  return (
    <div className="block">
      <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
        {label}
      </span>
      <div className="mt-1 rounded-xl border border-sand-200 bg-white px-2 py-2 focus-within:border-clay-500 focus-within:ring-2 focus-within:ring-clay-500/20 transition">
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {selected.map((entry) => (
              <span
                key={entry}
                className="inline-flex items-center gap-1 rounded-full bg-clay-500/10 text-clay-600 text-xs font-medium pl-2.5 pr-1 py-1"
              >
                {entry}
                <button
                  type="button"
                  onClick={() => remove(entry)}
                  className="w-4 h-4 rounded-full hover:bg-clay-500/20 flex items-center justify-center leading-none"
                  aria-label={`${entry} entfernen`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        <input
          type="text"
          list={listId}
          placeholder={placeholder || "Eintragen und Enter drücken"}
          onKeyDown={onKeyDown}
          onBlur={(e) => {
            add(e.target.value);
            e.target.value = "";
          }}
          className="w-full bg-transparent px-1 text-sm text-ink-900 placeholder:text-ink-700/30 outline-none"
        />
        <datalist id={listId}>
          {suggestions.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      </div>
    </div>
  );
}
