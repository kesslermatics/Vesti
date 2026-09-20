# Vesti 👔

Vesti ist eine smarte App zur digitalen Garderobenverwaltung. Mithilfe der Gemini-KI hilft dir die App nicht nur dabei, deinen Kleiderschrank zu organisieren, sondern generiert auch maßgeschneiderte Outfit-Vorschläge für jeden Anlass – basierend auf den Kleidungsstücken, die du bereits besitzt.

Neben der Kleidung verwaltet Vesti zwei weitere Sammlungen: **Uhren** und **Düfte**. Beide liegen in eigenen Tabellen statt als Kleidungskategorie, weil sie völlig andere Attribute haben – eine Uhr hat einen Gehäusedurchmesser und ein Serviceintervall, ein Duft eine Duftpyramide und ein Haltbarkeitsdatum. Der Outfit-Generator, der Chat und die Kaufberatung kennen alle drei Sammlungen und empfehlen zum Look auch die passende Uhr und den passenden Duft.

## Wie es funktioniert

1. **Registrieren / Anmelden** – Jeder Nutzer hat sein eigenes Konto und seine eigene, private Garderobe.
2. **Foto machen** – Du fotografierst ein Kleidungsstück.
3. **KI extrahiert Metadaten** – Gemini erkennt Kategorie, Farbe, Material, Muster, Stil, Anlass und Jahreszeit.
4. **Bestätigen** – Du prüfst und korrigierst die Vorschläge, dann wird das Teil samt Bild gespeichert.
5. **Garderobe durchstöbern** – Alle Teile werden nach Kategorie sortiert angezeigt.
6. **Outfit vorschlagen lassen** – Du wählst ein Teil, gibst einen Anlass an, und Gemini stellt aus deiner Garderobe ein passendes Outfit zusammen – mit Bildern und einer deutschen Begründung.

## Datenhaltung

Alle Daten liegen in der Postgres-Datenbank – auch die **Bilder** selbst (als Binärdaten in der Tabelle `clothing_items`). Es gibt keinen Dateisystem-Speicher, dadurch ist das Backend auf Railway zustandslos und Bilder gehen bei einem Redeploy nicht verloren. Jedes Kleidungsstück gehört genau einem Nutzer (`user_id`), die Garderoben sind vollständig voneinander getrennt.

## Nutzer-Management

- Registrierung & Login über E-Mail und Passwort.
- Passwörter werden mit PBKDF2-SHA256 (240k Runden, zufälliger Salt) gehasht – nie im Klartext gespeichert.
- Authentifizierung per JWT (Bearer-Token), im Browser in `localStorage`.
- Alle Garderoben-Endpunkte sind geschützt und liefern ausschließlich die Teile des angemeldeten Nutzers.

## Projektstruktur

```
Vesti/
├── backend/          FastAPI + SQLAlchemy + Gemini
│   └── app/
│       ├── main.py                    REST-Endpunkte (Kleidung, Outfits, Chat, Shopping)
│       ├── collections_api.py         REST-Endpunkte für Uhren & Düfte
│       ├── shared.py                  gemeinsame Helfer beider Router
│       ├── auth.py                    Passwort-Hashing & JWT
│       ├── gemini_service.py          KI: Bildanalyse, Inszenierung, Empfehlungen
│       ├── models.py                  DB-Modelle (User, ClothingItem, Watch, Fragrance)
│       ├── schemas.py                 Pydantic-Schemas
│       ├── categories.py              Kleidungs-Kategorien & Metadaten
│       ├── watches.py                 Uhren-Vokabulare + Handgelenk-Heuristik
│       ├── fragrances.py              Duft-Vokabulare + Haltbarkeit
│       ├── analytics.py               Statistik der Garderobe
│       ├── analytics_collections.py   Statistik der Uhren- & Duftsammlung
│       ├── migrations.py              Auto-Migration + Umzug alter Uhren
│       ├── database.py                DB-Verbindung (SQLite / Postgres)
│       └── config.py                  Einstellungen (Env)
└── frontend/         Vite + React + Tailwind + Framer Motion
    └── src/
        ├── App.jsx                    Navigation, Sammlungs-Umschalter, Auth-Gating
        ├── api.js                     API-Client + Token-Handling
        └── components/
            ├── AddItem.jsx            Erfassungs-Wizard Kleidung
            ├── AddCollectionItem.jsx  Erfassungs-Wizard Uhren & Düfte
            ├── CollectionView.jsx     Sammlungs-Ansicht + Duftberatung
            ├── CollectionForm.jsx     Formularfelder Uhren & Düfte
            ├── CollectionDetail.jsx   Detail-Ansichten Uhren & Düfte
            ├── Analytics.jsx          Auswertung aller drei Sammlungen
            └── ItemDetail, Chat, Shopping, OutfitGenerator, Profile, Field …
```

## Navigation

Die Bottom-Bar hat vier Einträge: **Sammlung**, **Analyse**, **Shopping**, **Chat**. Die drei Sammlungen sind bewusst keine eigenen Tabs, sondern ein Segmented Control innerhalb von „Sammlung" – sieben Tabs wären auf einem Handy nicht mehr bedienbar. Profil und Abmelden liegen hinter dem Avatar-Button oben rechts.

## Uhren & Düfte

**Erfassung:** Anders als bei Kleidung läuft die Erkennung über die *Schrift*. Bei einer Uhr liest die KI Zifferblatt und Referenznummer vom Gehäuseboden, bei einem Duft Name und Konzentration vom Etikett. Ist das Modell dadurch identifiziert, ergänzt Gemini die technischen Daten beziehungsweise die Duftpyramide aus seinem Wissen – das ist genauer als eine optische Schätzung. Ist es *nicht* identifiziert, bleiben die Felder leer, statt geraten zu werden; der Wizard sagt das offen.

**Inszenierung:** Wie Kleidungsstücke lassen sich Uhren und Flakons per KI als Studio-Produktfoto inszenieren. In Outfit-Vorschlägen wird das inszenierte Bild bevorzugt angezeigt, weil eine Kombination aus einheitlichen Studiofotos als Ganzes lesbar ist.

**Migration:** Früher war „Uhr" eine Kleidungskategorie unter den Accessoires. Beim Start zieht `migrate_legacy_watches()` bestehende Einträge einmalig nach `watches` um, übernimmt alle Bilder und markiert sie mit `needs_review`. In der App erscheint dann ein Hinweis mit dem Button „Jetzt per KI erfassen", weil die technischen Daten dort nie erfasst wurden.

**Kein Tragetagebuch:** Bewusst weggelassen. Rotationsstatistiken klingen gut, setzen aber voraus, dass täglich protokolliert wird – das macht in der Praxis niemand.

## Farbpalette

Warm, minimalistisch, clean:

| Rolle | Farbe |
|-------|-------|
| Hintergrund (sand) | `#faf8f5` |
| Karten / Akzentflächen | `#f3ede4` |
| Akzent (clay / Terrakotta) | `#b9734f` |
| Text (ink) | `#1c1916` |

## Lokal starten

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # GEMINI_API_KEY eintragen
uvicorn app.main:app --reload
```

Läuft auf `http://localhost:8000`. API-Doku unter `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL zeigt auf das Backend
npm run dev
```

Läuft auf `http://localhost:5173`.

## Gemini-Modell

Standardmäßig wird `gemini-3.5-flash-lite` (multimodal) verwendet. Das Modell ist über die Env-Variable `GEMINI_MODEL` frei wählbar, z. B. `gemini-3.6-flash` für höhere Qualität.

## Deployment auf Railway

Beide Ordner werden als **separate Services** deployt.

### Backend-Service

1. Neues Service aus dem `backend/`-Ordner (Root Directory = `backend`).
2. Railway erkennt Python via Nixpacks. Start-Command steht in `railway.json`.
3. Umgebungsvariablen setzen:
   - `GEMINI_API_KEY` – dein API-Key
   - `GEMINI_MODEL` – optional, Standard `gemini-3.5-flash-lite`
   - `DATABASE_URL` – Postgres-URL (Railway-Postgres-Plugin setzt sie automatisch)
   - `JWT_SECRET` – langes zufälliges Secret (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
   - `CORS_ORIGINS` – die öffentliche URL des Frontend-Service
4. Public Domain generieren.

> Bilder werden in der Datenbank gespeichert, nicht im Dateisystem. Damit ist kein Volume nötig und ein Redeploy verliert keine Daten.

### Frontend-Service

1. Neues Service aus dem `frontend/`-Ordner (Root Directory = `frontend`).
2. Build & Start stehen in `railway.json` (`npm run build` → `npm run preview`).
3. Umgebungsvariable setzen:
   - `VITE_API_URL` – die öffentliche URL des Backend-Service (muss zur Build-Zeit gesetzt sein).
4. Public Domain generieren.

Nach dem Deploy `CORS_ORIGINS` im Backend auf die Frontend-Domain aktualisieren.

## API-Überblick

Geschützte Endpunkte (🔒) erwarten den Header `Authorization: Bearer <token>`.

| Methode | Pfad | Zweck |
|---------|------|-------|
| GET | `/api/health` | Statuscheck |
| GET | `/api/meta` | Kategorien & Optionen |
| POST | `/api/auth/register` | Konto erstellen → Token |
| POST | `/api/auth/login` | Anmelden → Token |
| GET | `/api/auth/me` | 🔒 Aktueller Nutzer |
| POST | `/api/analyze/quick` | 🔒 Bild → Kategorie & Farbe |
| POST | `/api/analyze/detail` | 🔒 Bild → alle Metadaten |
| POST | `/api/analyze/product-shot` | 🔒 Bild → inszeniertes Studiofoto |
| POST | `/api/items` | 🔒 Bestätigtes Teil speichern |
| GET | `/api/items` | 🔒 Eigene Teile |
| GET | `/api/items/{id}/image` | Bild eines Teils (Binärdaten) |
| DELETE | `/api/items/{id}` | 🔒 Teil löschen |
| POST | `/api/recommend` | 🔒 Outfit-Empfehlung inkl. Uhr & Duft |
| POST | `/api/outfits/generate` | 🔒 Mehrere komplette Looks inkl. Uhr & Duft |
| POST | `/api/analyze/watch` | 🔒 Aufnahmen → Uhren-Daten |
| POST | `/api/analyze/watch-shot` | 🔒 Aufnahmen → inszeniertes Uhrenfoto |
| GET/POST | `/api/watches` | 🔒 Uhren lesen / anlegen |
| PATCH/DELETE | `/api/watches/{id}` | 🔒 Uhr ändern / löschen |
| POST | `/api/watches/{id}/reanalyze` | 🔒 Uhr per KI neu erfassen |
| POST | `/api/analyze/fragrance` | 🔒 Aufnahmen → Duft-Daten |
| POST | `/api/analyze/fragrance-shot` | 🔒 Aufnahmen → inszeniertes Flakonfoto |
| GET/POST | `/api/fragrances` | 🔒 Düfte lesen / anlegen |
| PATCH/DELETE | `/api/fragrances/{id}` | 🔒 Duft ändern / löschen |
| PATCH | `/api/fragrances/{id}/fill-level` | 🔒 Füllstand setzen |
| POST | `/api/fragrances/advice` | 🔒 „Welchen Duft heute?" |
| GET | `/api/analytics/watches` | 🔒 Uhren-Statistik |
| GET | `/api/analytics/fragrances` | 🔒 Duft-Statistik |
| GET | `/api/collections/pending-review` | 🔒 Migrierte Einträge ohne Daten |
| POST | `/api/chat` | 🔒 Beratung zu Stil, Uhren und Düften |
