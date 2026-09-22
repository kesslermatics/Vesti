# Vesti MCP API

Read-only API für die Einbindung deiner Vesti-Garderobe in externe KI-Tools
(Claude, ChatGPT, Custom GPTs, etc.).

**Base URL:** `https://backend-production-66df.up.railway.app`

---

## Authentifizierung

Alle Endpoints erfordern einen API-Key im Request-Header:

```
X-API-Key: <dein-api-key>
```

Den Key generierst du in der Vesti-App unter **Profil → API-Key für MCP**.
Er ist unbegrenzt gültig und kann jederzeit widerrufen oder neu generiert werden.

---

## Endpoints

### 1. `GET /mcp/clothing` — Kleidungsstücke

Gibt alle Kleidungsstücke der Garderobe zurück.

**Response:** Array von Objekten

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | integer | Eindeutige ID |
| `name` | string | Bezeichnung (z.B. „Weißes Oxfordhemd") |
| `category` | string | Kategorie (z.B. „Hemd", „Jeans", „Chino") |
| `color` | string | Farbe |
| `material` | string | Material (z.B. „Baumwolle", „Wolle") |
| `pattern` | string | Muster (z.B. „Uni", „Kariert", „Gestreift") |
| `style` | string | Stil (z.B. „Casual", „Business", „Formal") |
| `occasion` | string | Anlass (z.B. „Büro", „Freizeit", „Festlich") |
| `season` | string | Saison (z.B. „Sommer", „Winter", „Ganzjährig") |
| `description` | string | KI-generierte Beschreibung |
| `details` | object | Kategoriespezifische Details (z.B. `{"schnitt": "slim"}`) |
| `quantity` | integer | Anzahl der Exemplare |
| `brand` | string | Marke |
| `favorite` | boolean | Als Favorit markiert |
| `has_ai_image` | boolean | KI-Produktfoto vorhanden |
| `created_at` | datetime | Hinzugefügt am (ISO 8601) |

**Beispiel:**
```json
[
  {
    "id": 42,
    "name": "Weißes Oxfordhemd",
    "category": "Hemd",
    "color": "Weiß",
    "material": "Baumwolle",
    "pattern": "Uni",
    "style": "Business",
    "occasion": "Büro",
    "season": "Ganzjährig",
    "description": "Klassisches weißes Hemd mit Button-Down-Kragen.",
    "details": { "schnitt": "Regular", "kragen": "Button-Down" },
    "quantity": 2,
    "brand": "Ralph Lauren",
    "favorite": true,
    "has_ai_image": false,
    "created_at": "2025-03-15T10:30:00Z"
  }
]
```

---

### 2. `GET /mcp/watches` — Uhrensammlung

Gibt alle Uhren der Sammlung zurück.

**Response:** Array von Objekten

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | integer | Eindeutige ID |
| `name` | string | Bezeichnung |
| `brand` | string | Marke |
| `model` | string | Modellname |
| `reference` | string | Referenznummer |
| `year` | integer\|null | Baujahr |
| `movement` | string | Werk (z.B. „Automatik", „Quarz", „Handaufzug") |
| `case_material` | string | Gehäusematerial (z.B. „Edelstahl", „Titan") |
| `case_diameter` | float\|null | Gehäusedurchmesser in mm |
| `case_thickness` | float\|null | Gehäusehöhe in mm |
| `lug_width` | float\|null | Bandanstoss in mm |
| `crystal` | string | Glas (z.B. „Saphirglas", „Mineralglas") |
| `water_resistance` | integer\|null | Wasserdichtigkeit in Metern |
| `complications` | array | Komplikationen (z.B. `["Datum", "Chronograph"]`) |
| `dial_color` | string | Zifferblattfarbe |
| `band_type` | string | Bandtyp (z.B. „Metallband", „Lederband") |
| `band_material` | string | Bandmaterial |
| `band_color` | string | Bandfarbe |
| `clasp` | string | Verschluss |
| `style` | string | Stil (z.B. „Dress / Elegant", „Sport", „Taucheruhr") |
| `occasions` | array | Anlässe |
| `condition` | string | Zustand |
| `box_papers` | string | Box & Papiere |
| `purchase_date` | datetime\|null | Kaufdatum |
| `purchase_price` | float\|null | Kaufpreis |
| `current_value` | float\|null | Aktueller Wert |
| `currency` | string | Währung (z.B. „EUR") |
| `serviced_at` | datetime\|null | Letzter Service |
| `service_interval_years` | integer\|null | Serviceintervall in Jahren |
| `warranty_until` | datetime\|null | Garantie bis |
| `favorite` | boolean | Favorit |
| `needs_review` | boolean | KI-Review ausstehend |
| `description` | string | Beschreibung |
| `notes` | string | Persönliche Notizen |
| `created_at` | datetime | Hinzugefügt am |

---

### 3. `GET /mcp/fragrances` — Duftsammlung

Gibt alle Düfte der Sammlung zurück.

**Response:** Array von Objekten

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | integer | Eindeutige ID |
| `name` | string | Name des Dufts |
| `brand` | string | Marke |
| `line` | string | Linie / Kollektion |
| `concentration` | string | Konzentration (z.B. „Eau de Parfum", „Eau de Toilette") |
| `year` | integer\|null | Erscheinungsjahr |
| `perfumer` | string | Parfümeur |
| `audience` | string | Zielgruppe (z.B. „Herren", „Unisex") |
| `family` | string | Primäre Duftfamilie (z.B. „Holzig", „Frisch / Zitrisch") |
| `secondary_family` | string | Sekundäre Duftfamilie |
| `top_notes` | array | Kopfnoten |
| `heart_notes` | array | Herznoten |
| `base_notes` | array | Basisnoten |
| `sillage` | string | Sillage / Projektion (z.B. „Mittel", „Stark") |
| `longevity` | string | Haltbarkeit (z.B. „6–8 Stunden") |
| `occasions` | array | Anlässe |
| `seasons` | array | Saisons |
| `time_of_day` | string | Tageszeit (z.B. „Abend", „Ganztags") |
| `bottle_size` | integer\|null | Flaschengröße in ml |
| `fill_level` | integer\|null | Füllstand in Prozent (0–100) |
| `quantity` | integer | Anzahl der Flakons |
| `purchase_price` | float\|null | Kaufpreis |
| `currency` | string | Währung |
| `opened_at` | datetime\|null | Geöffnet am |
| `favorite` | boolean | Favorit |
| `needs_review` | boolean | KI-Review ausstehend |
| `description` | string | Beschreibung |
| `notes` | string | Persönliche Notizen |
| `created_at` | datetime | Hinzugefügt am |

---

### 4. `GET /mcp/accessories` — Accessoires

Gibt alle Accessoires zurück (Schmuck, Taschen, Brillen, Gürtel, Schals u.a.).

**Response:** Array von Objekten

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | integer | Eindeutige ID |
| `name` | string | Bezeichnung |
| `brand` | string | Marke |
| `type` | string | Typ (z.B. „Ring", „Handtasche", „Sonnenbrille", „Gürtel") |
| `model` | string | Modell |
| `material` | string | Hauptmaterial |
| `secondary_material` | string | Zweitmaterial |
| `color` | string | Farbe |
| `stone` | string | Stein / Einlage |
| `style` | string | Stil |
| `occasions` | array | Anlässe |
| `condition` | string | Zustand |
| `details` | object | Typspezifische Details (z.B. Ringgröße, Kettenlänge) |
| `purchase_price` | float\|null | Kaufpreis |
| `current_value` | float\|null | Aktueller Wert |
| `currency` | string | Währung |
| `favorite` | boolean | Favorit |
| `needs_review` | boolean | KI-Review ausstehend |
| `description` | string | Beschreibung |
| `notes` | string | Persönliche Notizen |
| `created_at` | datetime | Hinzugefügt am |

---

### 5. `GET /mcp/analytics/watches` — Uhren-Statistiken

Aggregierte Kennzahlen der Uhrensammlung. Gut geeignet um Lücken zu erkennen,
Service-Fälligkeiten abzufragen oder den Sammlungswert zu ermitteln.

**Response:** Objekt

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `empty` | boolean | `true` wenn noch keine Uhren vorhanden |
| `total` | integer | Anzahl Uhren |
| `styles` | array | Verteilung nach Stil `[{label, count, share}]` |
| `brands` | array | Verteilung nach Marke |
| `movements` | array | Verteilung nach Werk |
| `case_materials` | array | Verteilung nach Gehäusematerial |
| `band_materials` | array | Verteilung nach Bandmaterial |
| `dial_colors` | array | Verteilung nach Zifferblattfarbe |
| `occasions` | array | Verteilung nach Anlass |
| `complications` | array | Top-10 Komplikationen |
| `diversity` | object | `{styles, brands, movements, case_materials}` — Anzahl einzigartiger Werte |
| `avg_diameter` | float\|null | Durchschnittlicher Gehäusedurchmesser in mm |
| `smallest_diameter` | float\|null | Kleinstes Gehäuse in mm |
| `largest_diameter` | float\|null | Größtes Gehäuse in mm |
| `wrist_advice` | string\|null | Empfehlung zur Größe basierend auf Handgelenkumfang |
| `total_purchase` | float\|null | Gesamte Kaufpreissumme |
| `total_value` | float\|null | Gesamter aktueller Wert |
| `value_change` | float\|null | Wertentwicklung (Wert minus Kaufpreis) |
| `service_soon` | array | Uhren mit Service fällig in 6 Monaten `[{id, name, due_date, overdue, days_left}]` |
| `warranty_active` | array | Uhren mit aktiver Garantie `[{id, name, until}]` |
| `needs_review` | integer | Anzahl Uhren mit ausstehendem KI-Review |
| `gaps` | array | Erkannte Lücken in der Sammlung als Strings |

---

### 6. `GET /mcp/analytics/fragrances` — Duft-Statistiken

Aggregierte Kennzahlen der Duftsammlung.

**Response:** Objekt

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `empty` | boolean | `true` wenn noch keine Düfte vorhanden |
| `total` | integer | Anzahl einzigartiger Düfte |
| `total_bottles` | integer | Gesamtanzahl Flakons (inkl. Mehrfachexemplare) |
| `families` | array | Verteilung nach Duftfamilie `[{label, count, share}]` |
| `notes` | array | Top-15 Noten über alle Pyramiden |
| `base_notes` | array | Top-10 Basisnoten |
| `concentrations` | array | Verteilung nach Konzentration |
| `brands` | array | Verteilung nach Marke |
| `occasions` | array | Verteilung nach Anlass |
| `times` | array | Verteilung nach Tageszeit |
| `audiences` | array | Verteilung nach Zielgruppe |
| `seasons` | array | Abdeckung pro Saison `[{label, count, share}]` für Frühling/Sommer/Herbst/Winter |
| `diversity` | object | `{families, notes, brands}` — Anzahl einzigartiger Werte |
| `total_ml` | integer\|null | Gesamtvolumen in ml |
| `total_spend` | float\|null | Gesamtausgaben |
| `low_stock` | array | Düfte mit niedrigem Füllstand `[{id, name, brand, fill_level}]` |
| `expiring` | array | Düfte die bald ablaufen `[{id, name, brand, expires_at, expired, days_left}]` |
| `duplicates` | array | Erkannte Dopplungen (gleiche Familie + ähnliche Basisnoten) |
| `needs_review` | integer | Anzahl Düfte mit ausstehendem KI-Review |
| `gaps` | array | Erkannte Lücken als Strings |

---

### 7. `GET /mcp/analytics/accessories` — Accessoire-Statistiken

Aggregierte Kennzahlen der Accessoire-Sammlung.

**Response:** Objekt

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `empty` | boolean | `true` wenn noch keine Accessoires vorhanden |
| `total` | integer | Anzahl Accessoires |
| `groups` | array | Verteilung nach Gruppe (z.B. Schmuck, Taschen, Brillen) `[{label, count, share}]` |
| `types` | array | Top-15 Typen |
| `brands` | array | Top-10 Marken |
| `materials` | array | Top-10 Materialien |
| `styles` | array | Verteilung nach Stil |
| `occasions` | array | Verteilung nach Anlass |
| `needs_review` | integer | Anzahl Accessoires mit ausstehendem KI-Review |

---

## Einbindung in Claude (Custom Instructions)

Um die Vesti-API in Claude zu nutzen, füge folgendes in die **Custom Instructions** ein:

```
Du hast Zugriff auf meine Vesti-Garderobe über diese API:
Base URL: https://backend-production-66df.up.railway.app
Auth-Header: X-API-Key: <dein-api-key>

Endpoints:
- GET /mcp/clothing          → Kleidungsstücke
- GET /mcp/watches           → Uhren
- GET /mcp/fragrances        → Düfte
- GET /mcp/accessories       → Accessoires
- GET /mcp/analytics/watches      → Uhren-Statistiken
- GET /mcp/analytics/fragrances   → Duft-Statistiken
- GET /mcp/analytics/accessories  → Accessoire-Statistiken

Wenn ich nach Outfit-Empfehlungen, meiner Garderobe oder meinen Sammlungen frage,
ruf die passenden Endpoints ab und antworte auf Basis meiner echten Daten.
```

## Einbindung als MCP Server (Claude Desktop / Cursor)

Füge in deine `mcp.json` / `claude_desktop_config.json` einen HTTP-MCP-Server ein:

```json
{
  "mcpServers": {
    "vesti": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://backend-production-66df.up.railway.app/mcp",
        "--header",
        "X-API-Key: <dein-api-key>"
      ]
    }
  }
}
```

> `mcp-remote` ist ein kleines Open-Source-Tool das einen lokalen stdio-MCP-Proxy
> für HTTP-Endpoints bereitstellt: [github.com/geelen/mcp-remote](https://github.com/geelen/mcp-remote)

---

## Fehler-Codes

| Status | Bedeutung |
|--------|-----------|
| `401 Unauthorized` | Key fehlt, ungültig oder widerrufen |
| `422 Unprocessable Entity` | Header `X-API-Key` nicht mitgeschickt |
| `500 Internal Server Error` | Serverfehler |
