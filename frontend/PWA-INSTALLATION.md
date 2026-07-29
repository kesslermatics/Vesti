# 📱 Vesti als App installieren

Vesti ist jetzt eine Progressive Web App (PWA) und kann auf Android und iOS als eigenständige App installiert werden!

## ✨ Features

- **Offline-Funktionalität**: Nutze die App auch ohne Internetverbindung
- **App-ähnliches Erlebnis**: Vollbildmodus ohne Browser-UI
- **Push-Benachrichtigungen**: (kann später erweitert werden)
- **Schneller Zugriff**: App-Icon auf dem Homescreen
- **Automatische Updates**: Die App aktualisiert sich automatisch

## 📲 Installation auf Android

1. Öffne die Vesti-Website in **Chrome** oder **Samsung Internet**
2. Tippe auf das **Menü** (⋮) oben rechts
3. Wähle **"Zum Startbildschirm hinzufügen"** oder **"App installieren"**
4. Bestätige die Installation
5. Die App erscheint auf deinem Homescreen! 🎉

**Alternative:**
- Suche nach dem **Banner unten** mit "Zur Startseite hinzufügen" und tippe darauf

## 🍎 Installation auf iOS (iPhone/iPad)

1. Öffne die Vesti-Website in **Safari** (wichtig!)
2. Tippe auf das **Teilen-Symbol** (□↑) unten in der Mitte
3. Scrolle runter und wähle **"Zum Home-Bildschirm"**
4. Gib einen Namen ein (z.B. "Vesti") und tippe auf **"Hinzufügen"**
5. Die App erscheint auf deinem Homescreen! 🎉

**Hinweis:** Auf iOS funktioniert die Installation nur in Safari, nicht in Chrome oder anderen Browsern.

## 💻 Installation auf Desktop

### Chrome, Edge, Brave (Windows/Mac/Linux)
1. Öffne die Vesti-Website
2. Klicke auf das **Install-Symbol** (⊕) in der Adressleiste rechts
3. Klicke auf **"Installieren"**
4. Die App öffnet sich in einem eigenen Fenster

### Safari (Mac)
Aktuell keine native Installation, aber du kannst ein Lesezeichen setzen.

## 🔧 Technische Details

- **Service Worker**: Cached statische Dateien für Offline-Zugriff
- **Manifest**: Definiert App-Name, Icons und Erscheinungsbild
- **Icons**: Automatisch generierte PNG-Icons in verschiedenen Größen (192x192, 512x512)
- **Cache-Strategie**: CacheFirst für Fonts, NetworkFirst für API-Calls

## 🛠️ Entwicklung

### Icons neu generieren
```bash
npm run generate-icons
```

### Build mit PWA
```bash
npm run build
```

Der Build-Prozess:
1. Generiert PNG-Icons aus dem SVG
2. Erstellt den Service Worker
3. Bundled die App mit Vite

### Testing
```bash
npm run preview
```

Teste die PWA lokal im Production-Mode vor dem Deployment.

## 🚀 Deployment

Nach dem Deployment kannst du prüfen, ob die PWA korrekt funktioniert:

1. **Chrome DevTools** → Application Tab → Manifest/Service Worker
2. **Lighthouse Audit** → PWA-Score sollte >90 sein
3. **Teste die Installation** auf echten Geräten

## 📝 Checkliste für Production

- [x] Icons in allen Größen vorhanden
- [x] Manifest korrekt konfiguriert
- [x] Service Worker registriert
- [x] HTTPS aktiviert (erforderlich für PWA)
- [x] Theme-Color definiert
- [x] iOS Meta-Tags gesetzt
- [ ] Icons auf echtem Gerät testen
- [ ] Offline-Funktionalität testen

## 🐛 Troubleshooting

**App wird nicht angezeigt zum Installieren:**
- Stelle sicher, dass die Seite über HTTPS läuft
- Prüfe, ob alle Icons vorhanden sind
- Lösche den Browser-Cache und lade neu

**iOS Installation funktioniert nicht:**
- Nutze Safari (nicht Chrome!)
- Stelle sicher, dass die Website über HTTPS läuft
- Prüfe die apple-touch-icon Meta-Tags

**Service Worker lädt nicht:**
- Prüfe in DevTools → Application → Service Workers
- Unregister alte Service Worker
- Hard Reload (Ctrl+Shift+R / Cmd+Shift+R)
