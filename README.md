# Vesti 👔

Vesti ist eine smarte App zur digitalen Garderobenverwaltung. Mithilfe der Gemini-KI hilft dir die App nicht nur dabei, deinen Kleiderschrank zu organisieren, sondern generiert auch maßgeschneiderte Outfit-Vorschläge für jeden Anlass – basierend auf den Kleidungsstücken, die du bereits besitzt.

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
│       ├── main.py            REST-Endpunkte
│       ├── auth.py            Passwort-Hashing & JWT
│       ├── gemini_service.py  KI: Bildanalyse & Outfit-Empfehlung
│       ├── models.py          DB-Modelle (User, ClothingItem)
│       ├── schemas.py         Pydantic-Schemas
│       ├── categories.py      Kategorien & Metadaten-Optionen
│       ├── database.py        DB-Verbindung (SQLite / Postgres)
│       └── config.py          Einstellungen (Env)
└── frontend/         Vite + React + Tailwind + Framer Motion
    └── src/
        ├── App.jsx            Garderoben-Ansicht + Auth-Gating
        ├── api.js             API-Client + Token-Handling
        └── components/        Auth, AddItem, ItemDetail, Modal, Field
```

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
| POST | `/api/analyze` | 🔒 Bild → KI-Metadaten (noch nicht gespeichert) |
| POST | `/api/items` | 🔒 Bestätigtes Teil speichern |
| GET | `/api/items` | 🔒 Eigene Teile |
| GET | `/api/items/{id}/image` | Bild eines Teils (Binärdaten) |
| DELETE | `/api/items/{id}` | 🔒 Teil löschen |
| POST | `/api/recommend` | 🔒 Outfit-Empfehlung zu einem Teil |
