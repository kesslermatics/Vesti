# Thumbnail-System Implementation

## Problem
Vorschaubilder in der Garderobe-Ansicht (Grid & List) haben sehr langsam geladen, weil sie die vollauflösenden Originalbilder aus der Datenbank geladen haben.

## Lösung
Implementierung eines Thumbnail-Systems mit 400×400px JPEG-Thumbnails (Qualität 75) für schnelleres Laden in Übersichten.

## Änderungen

### Backend

#### 1. Modelle (`app/models.py`)
- ✅ `_create_thumbnail()` Funktion bereits vorhanden
- ✅ `ClothingItem.thumbnail_data` Spalte hinzugefügt (BLOB/BYTEA, nullable)
- ✅ `ItemImage.thumbnail_data` Spalte hinzugefügt (BLOB/BYTEA, nullable)

#### 2. Migrationen (`app/migrations.py`)
- ✅ Migration für `clothing_items.thumbnail_data` hinzugefügt
- ✅ Migration für `item_images.thumbnail_data` hinzugefügt
- Wird automatisch beim Backend-Start ausgeführt

#### 3. API-Endpunkte (`app/main.py`)
- ✅ `GET /api/items/{item_id}/thumbnail` - Thumbnail für Hauptbild
- ✅ `GET /api/item-images/{image_id}/thumbnail` - Thumbnail für Zusatzbild
- ✅ `_thumbnail_url()` und `_extra_thumbnail_url()` Hilfsfunktionen
- ✅ `_to_out()` erweitert um `thumbnail_url` und `thumbnail_urls`
- ✅ `create_item()` generiert Thumbnails beim Speichern

#### 4. Schemas (`app/schemas.py`)
- ✅ `ItemOut.thumbnail_url` hinzugefügt
- ✅ `ItemOut.thumbnail_urls` hinzugefügt

#### 5. Dependencies
- ✅ Pillow (PIL) bereits in `requirements.txt` vorhanden

### Frontend

#### 1. Hauptansicht (`frontend/src/App.jsx`)
- ✅ Grid-View: Verwendet `item.thumbnail_url` statt `item.image_url`
- ✅ List-View: Verwendet `item.thumbnail_url` statt `item.image_url`
- ✅ Fallback auf `item.image_url` wenn Thumbnail nicht verfügbar

#### 2. Detail-Ansicht (`frontend/src/components/ItemDetail.jsx`)
- ✅ Haupt-Display: Verwendet weiterhin Vollbilder (`image_urls`)
- ✅ Thumbnail-Leiste: Verwendet `thumbnail_urls` für schnelleres Laden
- ✅ Fallback-Logik implementiert

## Migration bestehender Daten

Für bereits existierende Bilder ohne Thumbnails:

```bash
cd backend
python generate_thumbnails.py
```

Dieses Script:
- Findet alle ClothingItems ohne `thumbnail_data`
- Findet alle ItemImages ohne `thumbnail_data`
- Generiert Thumbnails mit `_create_thumbnail()`
- Speichert sie in der Datenbank

## Technische Details

### Thumbnail-Generierung
- **Format**: JPEG (universelle Kompatibilität)
- **Größe**: max 400×400px (proportional verkleinert)
- **Qualität**: 75 (gute Balance zwischen Größe und Qualität)
- **Resampling**: LANCZOS (beste Qualität beim Verkleinern)
- **RGB-Konvertierung**: PNG/RGBA werden auf weißem Hintergrund konvertiert

### Performance-Vorteile
- **Grid-View**: ~10-20x kleinere Dateigröße pro Bild
- **List-View**: ~10-20x kleinere Dateigröße pro Thumbnail
- **Detail-View**: Nur Thumbnail-Leiste optimiert, Haupt-Display bleibt hochauflösend
- **Netzwerk**: Deutlich reduzierte Datenmenge beim initialen Laden

### Fallback-Strategie
- Frontend: Verwendet `thumbnail_url || image_url` → funktioniert auch ohne Backend-Update
- Backend: Endpoint liefert `thumbnail_data || image_data` → funktioniert auch für alte Daten

## Testing

### 1. Neue Bilder
- Neues Item hinzufügen → Thumbnail wird automatisch generiert
- Überprüfen in Grid/List-View → sollte schneller laden

### 2. Bestehende Bilder
- Migration-Script ausführen
- Backend neu starten
- Garderobe öffnen → sollte deutlich schneller laden

### 3. Fallback-Verhalten
- Items ohne Thumbnails sollten weiterhin funktionieren (mit Vollbildern)

## Deployment-Reihenfolge

1. ✅ Backend-Code deployen (mit Migrationen)
2. ✅ Backend-Neustart → Spalten werden automatisch hinzugefügt
3. ✅ Migration-Script ausführen (optional, für bestehende Daten)
4. ✅ Frontend deployen

## Rollback-Sicherheit

- Neue Spalten sind `nullable` → kein Breaking Change
- Alte Frontend-Versionen funktionieren weiterhin (nutzen `image_url`)
- Alte Backend-Versionen funktionieren weiterhin (liefern keine `thumbnail_url`)
- Keine Daten gehen verloren
