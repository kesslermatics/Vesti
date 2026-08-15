import {
  ChipMultiSelect,
  DateField,
  NumberField,
  SelectField,
  TextField,
  TokenField,
} from "./Field";
import BrandField from "./BrandField";

// Kleine Abschnitts-Überschrift, damit die vielen Felder nicht als Block wirken
function Section({ title, children, columns = 2 }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <h4 className="text-xs font-semibold text-ink-900 uppercase tracking-wide">
          {title}
        </h4>
        <div className="flex-1 h-px bg-sand-100" />
      </div>
      <div className={columns === 2 ? "grid grid-cols-2 gap-3" : "space-y-3"}>
        {children}
      </div>
    </div>
  );
}

function Wide({ children }) {
  return <div className="col-span-2">{children}</div>;
}

// Alle Duftnoten aus den Gruppen zu einer flachen Vorschlagsliste
export function flatNotes(meta) {
  const groups = meta?.fragrances?.note_groups || [];
  return groups.flatMap((g) => g.items);
}

// ══════════════════════════════════════════════════════════════
//  Uhren-Formular
// ══════════════════════════════════════════════════════════════

export function WatchFields({ data, update, meta, brands }) {
  const w = meta?.watches || {};

  return (
    <div className="space-y-6">
      <Section title="Identifikation">
        <Wide>
          <TextField
            label="Name"
            value={data.name}
            onChange={(v) => update("name", v)}
            placeholder="z.B. Omega Speedmaster Professional"
          />
        </Wide>
        <BrandField
          value={data.brand}
          onChange={(v) => update("brand", v)}
          mine={brands?.mine || []}
          suggestions={brands?.suggestions || []}
        />
        <TextField
          label="Modell"
          value={data.model}
          onChange={(v) => update("model", v)}
          placeholder="z.B. Moonwatch"
        />
        <TextField
          label="Referenznummer"
          value={data.reference}
          onChange={(v) => update("reference", v)}
          placeholder="z.B. 310.30.42.50"
        />
        <NumberField
          label="Baujahr"
          value={data.year}
          onChange={(v) => update("year", v)}
          step="1"
          placeholder="z.B. 2021"
        />
      </Section>

      <Section title="Technik">
        <SelectField
          label="Werk"
          value={data.movement}
          onChange={(v) => update("movement", v)}
          options={w.movements || []}
        />
        <SelectField
          label="Gehäusematerial"
          value={data.case_material}
          onChange={(v) => update("case_material", v)}
          options={w.case_materials || []}
        />
        <NumberField
          label="Durchmesser"
          value={data.case_diameter}
          onChange={(v) => update("case_diameter", v)}
          unit="mm"
          step="0.1"
        />
        <NumberField
          label="Höhe"
          value={data.case_thickness}
          onChange={(v) => update("case_thickness", v)}
          unit="mm"
          step="0.1"
        />
        <NumberField
          label="Bandanstoß"
          value={data.lug_width}
          onChange={(v) => update("lug_width", v)}
          unit="mm"
          step="0.5"
        />
        <NumberField
          label="Wasserdichte"
          value={data.water_resistance}
          onChange={(v) => update("water_resistance", v)}
          unit="m"
          step="10"
        />
        <Wide>
          <SelectField
            label="Glas"
            value={data.crystal}
            onChange={(v) => update("crystal", v)}
            options={w.crystals || []}
          />
        </Wide>
        <Wide>
          <ChipMultiSelect
            label="Funktionen"
            value={data.complications}
            onChange={(v) => update("complications", v)}
            options={w.complications || []}
          />
        </Wide>
      </Section>

      <Section title="Optik">
        <TextField
          label="Zifferblatt-Farbe"
          value={data.dial_color}
          onChange={(v) => update("dial_color", v)}
        />
        <TextField
          label="Armband-Farbe"
          value={data.band_color}
          onChange={(v) => update("band_color", v)}
        />
        <SelectField
          label="Armband-Art"
          value={data.band_type}
          onChange={(v) => update("band_type", v)}
          options={w.band_types || []}
        />
        <SelectField
          label="Armband-Material"
          value={data.band_material}
          onChange={(v) => update("band_material", v)}
          options={w.band_materials || []}
        />
        <Wide>
          <SelectField
            label="Schließe"
            value={data.clasp}
            onChange={(v) => update("clasp", v)}
            options={w.clasps || []}
          />
        </Wide>
      </Section>

      <Section title="Einsatz">
        <Wide>
          <SelectField
            label="Uhrentyp"
            value={data.style}
            onChange={(v) => update("style", v)}
            options={w.styles || []}
          />
        </Wide>
        <Wide>
          <ChipMultiSelect
            label="Anlässe"
            value={data.occasions}
            onChange={(v) => update("occasions", v)}
            options={w.occasions || []}
          />
        </Wide>
      </Section>

      <Section title="Zustand & Kauf">
        <SelectField
          label="Zustand"
          value={data.condition}
          onChange={(v) => update("condition", v)}
          options={w.conditions || []}
        />
        <SelectField
          label="Lieferumfang"
          value={data.box_papers}
          onChange={(v) => update("box_papers", v)}
          options={w.sets || []}
        />
        <DateField
          label="Kaufdatum"
          value={data.purchase_date}
          onChange={(v) => update("purchase_date", v)}
        />
        <NumberField
          label="Kaufpreis"
          value={data.purchase_price}
          onChange={(v) => update("purchase_price", v)}
          unit={data.currency || "EUR"}
          step="1"
        />
        <NumberField
          label="Aktueller Wert"
          value={data.current_value}
          onChange={(v) => update("current_value", v)}
          unit={data.currency || "EUR"}
          step="1"
        />
        <DateField
          label="Garantie bis"
          value={data.warranty_until}
          onChange={(v) => update("warranty_until", v)}
        />
      </Section>

      <Section title="Service">
        <DateField
          label="Letzter Service"
          value={data.serviced_at}
          onChange={(v) => update("serviced_at", v)}
        />
        <NumberField
          label="Intervall"
          value={data.service_interval_years}
          onChange={(v) => update("service_interval_years", v)}
          unit="Jahre"
          step="1"
          min="1"
        />
        <Wide>
          <p className="text-[11px] text-ink-700/50">
            Nur für mechanische Werke relevant. Ohne Angabe wird mit fünf Jahren gerechnet,
            gemessen ab dem letzten Service oder dem Kaufdatum.
          </p>
        </Wide>
      </Section>

      <Section title="Notizen" columns={1}>
        <TextField
          label="Beschreibung"
          value={data.description}
          onChange={(v) => update("description", v)}
        />
        <TextField
          label="Eigene Notizen"
          value={data.notes}
          onChange={(v) => update("notes", v)}
          placeholder="z.B. Geschenk zum Abschluss"
        />
      </Section>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
//  Duft-Formular
// ══════════════════════════════════════════════════════════════

export function FragranceFields({ data, update, meta, brands }) {
  const f = meta?.fragrances || {};
  const notes = flatNotes(meta);

  return (
    <div className="space-y-6">
      <Section title="Identifikation">
        <Wide>
          <TextField
            label="Duftname"
            value={data.name}
            onChange={(v) => update("name", v)}
            placeholder="z.B. Sauvage Elixir"
          />
        </Wide>
        <BrandField
          label="Haus"
          value={data.brand}
          onChange={(v) => update("brand", v)}
          mine={brands?.mine || []}
          suggestions={brands?.suggestions || []}
        />
        <TextField
          label="Linie"
          value={data.line}
          onChange={(v) => update("line", v)}
          placeholder="z.B. Private Collection"
        />
        <SelectField
          label="Konzentration"
          value={data.concentration}
          onChange={(v) => update("concentration", v)}
          options={f.concentrations || []}
        />
        <SelectField
          label="Zielgruppe"
          value={data.audience}
          onChange={(v) => update("audience", v)}
          options={f.audiences || []}
        />
        <NumberField
          label="Erscheinungsjahr"
          value={data.year}
          onChange={(v) => update("year", v)}
          step="1"
        />
        <TextField
          label="Parfumeur"
          value={data.perfumer}
          onChange={(v) => update("perfumer", v)}
        />
      </Section>

      <Section title="Duftprofil">
        <SelectField
          label="Duftfamilie"
          value={data.family}
          onChange={(v) => update("family", v)}
          options={f.families || []}
        />
        <SelectField
          label="Zweite Familie"
          value={data.secondary_family}
          onChange={(v) => update("secondary_family", v)}
          options={f.families || []}
        />
        <Wide>
          <TokenField
            label="Kopfnoten"
            value={data.top_notes}
            onChange={(v) => update("top_notes", v)}
            suggestions={notes}
            placeholder="z.B. Bergamotte"
          />
        </Wide>
        <Wide>
          <TokenField
            label="Herznoten"
            value={data.heart_notes}
            onChange={(v) => update("heart_notes", v)}
            suggestions={notes}
            placeholder="z.B. Lavendel"
          />
        </Wide>
        <Wide>
          <TokenField
            label="Basisnoten"
            value={data.base_notes}
            onChange={(v) => update("base_notes", v)}
            suggestions={notes}
            placeholder="z.B. Vanille"
          />
        </Wide>
        <SelectField
          label="Sillage"
          value={data.sillage}
          onChange={(v) => update("sillage", v)}
          options={f.sillages || []}
        />
        <SelectField
          label="Haltbarkeit"
          value={data.longevity}
          onChange={(v) => update("longevity", v)}
          options={f.longevities || []}
        />
      </Section>

      <Section title="Einsatz">
        <Wide>
          <SelectField
            label="Tageszeit"
            value={data.time_of_day}
            onChange={(v) => update("time_of_day", v)}
            options={f.times || []}
          />
        </Wide>
        <Wide>
          <ChipMultiSelect
            label="Jahreszeiten"
            value={data.seasons}
            onChange={(v) => update("seasons", v)}
            options={f.seasons || []}
          />
        </Wide>
        <Wide>
          <ChipMultiSelect
            label="Anlässe"
            value={data.occasions}
            onChange={(v) => update("occasions", v)}
            options={f.occasions || []}
          />
        </Wide>
      </Section>

      <Section title="Flakon & Bestand">
        <NumberField
          label="Füllmenge"
          value={data.bottle_size}
          onChange={(v) => update("bottle_size", v)}
          unit="ml"
          step="5"
        />
        <NumberField
          label="Anzahl Flakons"
          value={data.quantity}
          onChange={(v) => update("quantity", v || 1)}
          step="1"
          min="1"
        />
        <Wide>
          <FillLevelSlider
            value={data.fill_level}
            onChange={(v) => update("fill_level", v)}
          />
        </Wide>
        <TextField
          label="Batch-Code"
          value={data.batch_code}
          onChange={(v) => update("batch_code", v)}
        />
        <DateField
          label="Geöffnet am"
          value={data.opened_at}
          onChange={(v) => update("opened_at", v)}
        />
        <DateField
          label="Kaufdatum"
          value={data.purchase_date}
          onChange={(v) => update("purchase_date", v)}
        />
        <NumberField
          label="Kaufpreis"
          value={data.purchase_price}
          onChange={(v) => update("purchase_price", v)}
          unit={data.currency || "EUR"}
          step="1"
        />
        <Wide>
          <p className="text-[11px] text-ink-700/50">
            Das Öffnungsdatum bestimmt, wann Vesti vor dem Kippen warnt. Zitrische und
            frische Düfte halten deutlich kürzer als schwere, harzige Basen.
          </p>
        </Wide>
      </Section>

      <Section title="Notizen" columns={1}>
        <TextField
          label="Beschreibung"
          value={data.description}
          onChange={(v) => update("description", v)}
        />
        <TextField
          label="Eigene Notizen"
          value={data.notes}
          onChange={(v) => update("notes", v)}
          placeholder="z.B. hält an mir nur 4 Stunden"
        />
      </Section>
    </div>
  );
}

// Füllstand als Schieberegler – schneller zu bedienen als ein Zahlenfeld
export function FillLevelSlider({ value, onChange }) {
  const level = value ?? 100;
  return (
    <div className="block">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium text-ink-700/70 uppercase tracking-wide">
          Füllstand
        </span>
        <span
          className={`text-sm font-semibold ${
            level <= 15 ? "text-clay-600" : "text-ink-900"
          }`}
        >
          {level} %
        </span>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        step="5"
        value={level}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-clay-500"
      />
      {level <= 15 && (
        <p className="text-[11px] text-clay-600 mt-1">
          Wird als knapp gewertet und in der Analyse als Nachkauf-Hinweis angezeigt.
        </p>
      )}
    </div>
  );
}
