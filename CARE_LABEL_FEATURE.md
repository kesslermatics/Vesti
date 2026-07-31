# Pflege-Etikett Erkennung

## Feature
Die KI liest jetzt automatisch **alle Informationen vom Pflege-Etikett** und speichert sie strukturiert beim Kleidungsstück.

## Was wird erkannt?

### 1. Pflegehinweise (`care_instructions`)
- **🌡️ Waschtemperatur**: z.B. "30°C", "40°C", "Handwäsche", "nicht waschen"
- **💨 Trockner**: z.B. "Trockner niedrig", "nicht Trockner", "lufttrocknen"
- **🔥 Bügeln**: z.B. "niedrige Temperatur", "mittlere Temperatur", "nicht bügeln"
- **⚗️ Bleichen**: z.B. "nicht bleichen"
- **✨ Chemische Reinigung**: z.B. "chemische Reinigung", "professionelle Reinigung"
- **⚠️ Besondere Hinweise**: z.B. "separat waschen", "auf links waschen"

### 2. Material-Details (`material_details`)
- **📋 Zusammensetzung**: Exakte Material-Angaben vom Etikett, z.B. "80% Wolle, 20% Polyamid"
- **🪵 Ledertyp** (bei Leder): z.B. "Glattleder", "Wildleder", "Nubukleder"
- **🧵 Futter**: Futtermaterial, z.B. "100% Polyester", "Lederfutter"
- **👟 Sohle** (bei Schuhen): z.B. "Gummisohle", "Ledersohle"
- **🌍 Herkunft**: z.B. "Made in Italy", "Made in China"

## Wie funktioniert es?

### 1. Mehrere Bilder hochladen
- **Hauptbild**: Vorderansicht des Kleidungsstücks
- **Rückseite**: Für Schnitt und Details
- **Futter**: Innenseite
- **Etikett**: 🏷️ **Hier steht die wichtige Info!**

Die KI analysiert ALLE Bilder gemeinsam und bevorzugt Etikett-Informationen gegenüber optischen Schätzungen.

### 2. Automatische Extraktion
Wenn ein Pflege-Etikett sichtbar ist, liest die KI:
- Alle Pflegesymbole und deren Bedeutung
- Die exakte Material-Zusammensetzung (Prozentangaben)
- Waschtemperatur
- Spezielle Pflegehinweise
- Bei Schuhen: Ledertyp, Sohlen- und Futtermaterial

### 3. Anzeige

#### In AddItem (Bestätigen-Phase)
Zwei farblich getrennte Boxen zeigen:
- **📋 Material & Herkunft** (beige Hintergrund)
- **🧺 Pflegehinweise** (rosa Hintergrund mit Icons)

Der Nutzer sieht sofort, welche Infos vom Etikett erkannt wurden.

#### In ItemDetail
Beim Öffnen eines gespeicherten Items:
- Normale Details bleiben wie gehabt
- Material-Details in eigener beiger Box
- Pflegehinweise in eigener rosa Box mit Icons
- Übersichtliche Darstellung mit Emojis

## Beispiele

### Hemd mit Pflege-Etikett
```json
{
  "material": "100% Baumwolle",
  "details": {
    "kragenform": "Button-Down",
    "care_instructions": {
      "wash_temp": "40°C",
      "dry": "Trockner niedrig",
      "iron": "mittlere Temperatur",
      "bleach": "nicht bleichen",
      "special": "auf links waschen"
    },
    "material_details": {
      "composition": "100% Baumwolle",
      "origin": "Made in Bangladesh"
    }
  }
}
```

### Lederschuh mit Details
```json
{
  "material": "Leder",
  "details": {
    "verschluss": "Schnürung",
    "care_instructions": {
      "special": "mit Lederpflege behandeln"
    },
    "material_details": {
      "leather_type": "Glattleder",
      "lining": "Lederfutter",
      "sole": "Gummisohle",
      "composition": "Obermaterial: 100% Rindsleder",
      "origin": "Made in Italy"
    }
  }
}
```

### Woll-Pullover
```json
{
  "material": "Wolle",
  "details": {
    "care_instructions": {
      "wash_temp": "Handwäsche",
      "dry": "liegend trocknen",
      "iron": "nicht bügeln",
      "bleach": "nicht bleichen",
      "special": "separat waschen, nicht wringen"
    },
    "material_details": {
      "composition": "80% Merinowolle, 20% Polyamid",
      "origin": "Made in Scotland"
    }
  }
}
```

## UI/UX Highlights

### Icons für Pflegesymbole
- 🌡️ Waschen
- 💨 Trocknen
- 🔥 Bügeln
- ⚗️ Bleichen
- ✨ Chemische Reinigung
- ⚠️ Besondere Hinweise

### Farb-Coding
- **Material-Details**: Beige Hintergrund (`bg-sand-100`)
- **Pflegehinweise**: Rosa Hintergrund (`bg-clay-500/5`)
- Klare visuelle Trennung für bessere Lesbarkeit

### Responsive Layout
- AddItem: Kompakte Boxen mit Icons
- ItemDetail: Übersichtliche Liste mit align-right Werten
- Mobile-optimiert

## Technische Details

### Backend (`gemini_service.py`)
Die `detail_analyze_image()` Funktion wurde erweitert mit:
- Erweiterte Prompt-Anweisungen für Etikett-Lesen
- Strukturierte Extraktion von `care_instructions` und `material_details`
- Nested JSON-Struktur im `details` Feld

### Frontend

**AddItem.jsx**:
- Zeigt erkannte Pflege/Material-Infos in der Confirm-Phase
- Zwei separate Boxen mit Icons und Farb-Coding
- Sonstige Details bleiben editierbar

**ItemDetail.jsx**:
- Separate Anzeige-Bereiche für care/material
- Icons für bessere Verständlichkeit
- Flex-Layout mit rechts ausgerichteten Werten

### Datenstruktur
```typescript
interface ClothingItem {
  // ... normale Felder
  details: {
    // Kategorie-spezifisch (z.B. schnitt, kragenform)
    [key: string]: string;
    
    // Pflegehinweise
    care_instructions?: {
      wash_temp?: string;
      dry?: string;
      iron?: string;
      bleach?: string;
      dry_clean?: string;
      special?: string;
    };
    
    // Material-Details
    material_details?: {
      composition?: string;
      leather_type?: string;
      lining?: string;
      sole?: string;
      origin?: string;
    };
  };
}
```

## Vorteile

1. **Genauigkeit**: Etikett-Infos sind präziser als visuelle Schätzungen
2. **Praktischer Nutzen**: User weiß immer, wie er seine Kleidung pflegen muss
3. **Werterhaltung**: Richtige Pflege erhält Kleidung länger
4. **Kaufentscheidungen**: Bei Schuhen z.B. sieht man Lederqualität
5. **Nachhaltigkeit**: Länger tragbare Kleidung durch richtige Pflege

## Beispiel-Workflow

1. User macht Foto vom Hemd (Vorderseite)
2. User macht Foto vom Pflege-Etikett am Hals
3. KI-Analyse läuft
4. In Confirm-Phase sieht User:
   - "40°C Waschtemperatur erkannt"
   - "100% Baumwolle vom Etikett"
   - "Made in Bangladesh"
5. User bestätigt → Infos werden gespeichert
6. Später in ItemDetail: Alle Pflege-Infos auf einen Blick

## Testing

### Testfälle
- [ ] Hemd mit klarem Pflege-Etikett
- [ ] Lederschuh mit Material-Angaben
- [ ] Woll-Pullover mit Handwäsche-Hinweis
- [ ] Jeans ohne Etikett (sollte graceful degradieren)
- [ ] Mehrsprachiges Etikett (Englisch/Deutsch/Französisch)
- [ ] Verwaschenes/unleserliches Etikett

### Edge Cases
- Kein Etikett vorhanden → Felder bleiben leer
- Unleserliches Etikett → KI macht optische Schätzung
- Mehrere Etiketten → KI kombiniert Infos
- Etikett in Fremdsprache → KI übersetzt automatisch

## Deployment

Keine Breaking Changes:
- Neue Felder sind optional
- Alte Items ohne care/material-Infos funktionieren weiter
- Graceful degradation wenn Felder leer sind
- Rückwärtskompatibel
