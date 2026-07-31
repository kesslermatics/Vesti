import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, auth } from "./api";
import AddItem from "./components/AddItem";
import ItemDetail from "./components/ItemDetail";
import Auth from "./components/Auth";
import Profile from "./components/Profile";
import Shopping from "./components/Shopping";
import Analytics from "./components/Analytics";
import Toast from "./components/Toast";
import OutfitGenerator from "./components/OutfitGenerator";
import Chat from "./components/Chat";

const TAB = {
  WARDROBE: "wardrobe",
  ANALYTICS: "analytics",
  SHOPPING: "shopping",
  CHAT: "chat",
  PROFILE: "profile",
};

const TABS = [
  { id: TAB.WARDROBE, label: "Garderobe", icon: "🧥" },
  { id: TAB.ANALYTICS, label: "Analyse", icon: "📊" },
  { id: TAB.SHOPPING, label: "Shopping", icon: "🛍️" },
  { id: TAB.CHAT, label: "Chat", icon: "💬" },
  { id: TAB.PROFILE, label: "Profil", icon: "👤" },
];

const GREETINGS = [
  "Dein Stil auf den Punkt gebracht.",
  "Unterstreiche heute deine Persönlichkeit.",
  "Trage, was dich stark macht. 🖤",
  "Selbstbewusstsein ist das beste Accessoire.",
  "Heute passt einfach alles zusammen.",
  "Bereit für einen stilvollen Auftritt?",
  "Dein Outfit sitzt, der Tag gehört dir. ✨",
  "Lass dein Outfit für dich sprechen.",
  "Klar. Elegant. Du.",
  "Zeitlose Eleganz für deinen Alltag. 🤍",
  "Ein guter Look ist der beste Start.",
  "Finde die perfekte Balance für heute.",
  "Welchen Eindruck hinterlässt du heute?",
  "Dein persönlicher Stil, ganz ohne Kompromisse.",
  "Fühl dich wohl, strahle es aus. ✨",
  "Die perfekte Kombination wartet schon.",
  "Klassisch, mutig oder entspannt? Du entscheidest.",
  "Mach das Anziehen zu deinem Ritual. ☕",
  "Gut gekleidet für jeden Moment.",
  "Zeig dich von deiner besten Seite.",
  "Mit dem richtigen Look in den Tag.",
  "Stil ist, wenn alles zusammenpasst. 🕶️",
  "Dein Tag, dein Outfit, deine Wahl.",
  "Entdecke heute neue Kombinationen.",
  "Ein Griff in den Kleiderschrank, unzählige Möglichkeiten.",
  "Bereit für das, was heute kommt. 💼",
  "Finde genau das, was heute zu dir passt.",
  "Qualität und Stil, die man sieht.",
  "Dein Look für heute steht fast fest.",
  "Kleidung ist Ausdruck. Was sagst du heute? 🖋️",
  "Stilbewusst durch den ganzen Tag.",
  "Heute überlassen wir nichts dem Zufall.",
  "Ein durchdachtes Outfit für einen erfolgreichen Tag.",
  "Weniger suchen, besser kleiden. 🧥",
  "Finde den Look, der dich heute begleitet.",
  "Eleganz beginnt bei der Auswahl.",
  "Mach den heutigen Tag zu deinem.",
  "Perfekt abgestimmt in den Tag starten.",
  "Dein Stil ist deine beste Visitenkarte.",
  "Zeit für einen Look, der genau zu dir passt."
];

function getRandomGreeting() {
  return GREETINGS[Math.floor(Math.random() * GREETINGS.length)];
}

const VIEW_MODE = {
  GRID: "grid",
  LIST: "list",
};

// Wählt die passende Vorschau-URL je nach Bildquelle-Präferenz
function pickThumb(item, useAiImages) {
  if (useAiImages && item.has_ai_image) {
    return item.ai_thumbnail_url || item.ai_image_url;
  }
  return item.thumbnail_url || item.image_url;
}

// Item Card Component
function ItemCard({ item, onSelect, viewMode, useAiImages }) {
  const thumb = pickThumb(item, useAiImages);
  if (viewMode === VIEW_MODE.GRID) {
    return (
      <motion.button
        layout
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        whileTap={{ scale: 0.97 }}
        onClick={() => onSelect(item)}
        className="group text-left relative"
      >
        {item.favorite && (
          <div className="absolute top-2 left-2 z-10 bg-amber-400 rounded-full w-6 h-6 flex items-center justify-center shadow-sm">
            <span className="text-sm">⭐</span>
          </div>
        )}
        <div className="relative aspect-square rounded-2xl overflow-hidden bg-white shadow-soft">
          <img
            src={thumb}
            alt={item.name}
            className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
          />
          {useAiImages && item.has_ai_image && (
            <span className="absolute bottom-2 left-2 bg-clay-500/90 text-white text-[10px] font-medium rounded-full px-2 py-0.5 backdrop-blur-sm">
              ✨ Inszeniert
            </span>
          )}
          {(item.quantity || 1) > 1 && (
            <span className="absolute top-2 right-2 bg-ink-900/80 text-white text-xs font-medium rounded-full px-2 py-0.5 backdrop-blur-sm">
              ×{item.quantity}
            </span>
          )}
        </div>
        <span className="mt-1.5 block text-sm text-ink-800 truncate">
          {item.name || item.category}
        </span>
        {item.color && (
          <span className="block text-xs text-ink-700/50 truncate">
            {item.color}
          </span>
        )}
      </motion.button>
    );
  }

  // List view
  return (
    <motion.button
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(item)}
      className="w-full group text-left bg-white rounded-xl p-3 shadow-soft hover:shadow-md transition flex items-center gap-3"
    >
      {/* Thumbnail */}
      <div className="relative w-14 h-14 flex-shrink-0 rounded-lg overflow-hidden bg-sand-50">
        <img
          src={thumb}
          alt={item.name}
          className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
        />
        {item.favorite && (
          <div className="absolute top-0.5 left-0.5 bg-amber-400 rounded-full w-4 h-4 flex items-center justify-center">
            <span className="text-[10px]">⭐</span>
          </div>
        )}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="font-medium text-ink-900 truncate">
            {item.name || item.category}
          </span>
          {(item.quantity || 1) > 1 && (
            <span className="text-xs text-ink-700/50 flex-shrink-0">
              ×{item.quantity}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5 text-xs text-ink-700/50">
          {item.color && <span>{item.color}</span>}
          {item.color && item.brand && <span>·</span>}
          {item.brand && <span>{item.brand}</span>}
          {(item.color || item.brand) && item.material && <span>·</span>}
          {item.material && <span>{item.material}</span>}
        </div>
      </div>
      <span className="text-ink-700/30 group-hover:text-ink-700/60 transition">
        →
      </span>
    </motion.button>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(true);
  const [tab, setTab] = useState(TAB.WARDROBE);
  const [viewMode, setViewMode] = useState(() => {
    // Load saved view mode from localStorage
    const saved = localStorage.getItem("vesti-view-mode");
    return saved === VIEW_MODE.LIST ? VIEW_MODE.LIST : VIEW_MODE.GRID;
  });
  const [useAiImages, setUseAiImages] = useState(() => {
    // KI-Bilder oder eigene Fotos anzeigen
    return localStorage.getItem("vesti-image-source") === "ai";
  });
  const [meta, setMeta] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [toastMessage, setToastMessage] = useState("");
  const [greeting, setGreeting] = useState(getRandomGreeting());

  // Neue Begrüßung beim Tab-Wechsel zur Garderobe
  useEffect(() => {
    if (tab === TAB.WARDROBE) {
      setGreeting(getRandomGreeting());
    }
  }, [tab]);

  // Save view mode to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("vesti-view-mode", viewMode);
  }, [viewMode]);

  // Save image source preference
  useEffect(() => {
    localStorage.setItem("vesti-image-source", useAiImages ? "ai" : "own");
  }, [useAiImages]);

  // Beim Start: Token pruefen und Nutzer laden
  useEffect(() => {
    (async () => {
      if (!auth.token) {
        setBooting(false);
        return;
      }
      try {
        const me = await api.me();
        setUser(me);
      } catch {
        auth.clear();
      } finally {
        setBooting(false);
      }
    })();
  }, []);

  // Bei 401 irgendwo -> ausloggen
  useEffect(() => {
    const handler = () => setUser(null);
    window.addEventListener("vesti-unauthorized", handler);
    return () => window.removeEventListener("vesti-unauthorized", handler);
  }, []);

  // Daten laden sobald eingeloggt
  useEffect(() => {
    if (!user) return;
    setLoading(true);
    (async () => {
      try {
        const [m, list] = await Promise.all([api.getMeta(), api.listItems()]);
        setMeta(m);
        setItems(list);
      } catch (err) {
        setError(err.message || "Verbindung zum Server fehlgeschlagen.");
      } finally {
        setLoading(false);
      }
    })();
  }, [user?.id]);

  const logout = useCallback(() => {
    auth.clear();
    setUser(null);
    setItems([]);
    setSelected(null);
    setTab(TAB.WARDROBE);
  }, []);

  // Nach Kategorie-Gruppen gruppieren (intelligent sortiert)
  // Sortierung: neu → alt (created_at DESC)
  const grouped = useMemo(() => {
    if (!meta) return { favorites: [], groups: [] };
    
    // Sortiere Items: neueste zuerst
    const sortedItems = [...items].sort((a, b) => 
      new Date(b.created_at) - new Date(a.created_at)
    );
    
    // Trenne Favoriten
    const favorites = sortedItems.filter(it => it.favorite);
    const nonFavorites = sortedItems.filter(it => !it.favorite);
    
    // Gruppiere nach Meta-Gruppen (z.B. "Oberteile", "Schuhe", etc.)
    const groupMap = new Map();
    
    for (const item of nonFavorites) {
      // Finde die Gruppe für diese Kategorie
      const metaGroup = meta.category_groups.find(g => 
        g.items.includes(item.category)
      );
      const groupName = metaGroup ? metaGroup.group : "Sonstiges";
      
      if (!groupMap.has(groupName)) {
        groupMap.set(groupName, []);
      }
      groupMap.get(groupName).push(item);
    }
    
    // Konvertiere zu Array in der Reihenfolge der Meta-Gruppen
    const groups = meta.category_groups
      .filter(g => groupMap.has(g.group))
      .map(g => ({
        group: g.group,
        items: groupMap.get(g.group)
      }));
    
    return { favorites, groups };
  }, [items, meta]);

  // Gesamtzahl inkl. Stückzahlen
  const totalPieces = useMemo(
    () => items.reduce((sum, i) => sum + (i.quantity || 1), 0),
    [items]
  );

  function handleCreated(item) {
    setItems((prev) => [item, ...prev]);
    // Toast mit Welcome-Message anzeigen
    console.log("Item created:", item);
    const message = item.welcome_message || `✨ ${item.name || item.category} wurde hinzugefügt!`;
    console.log("Toast message:", message);
    setToastMessage(message);
  }

  function handleDeleted(id) {
    setItems((prev) => prev.filter((i) => i.id !== id));
    setSelected(null);
  }

  function handleUpdated(updated) {
    setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
    setSelected(updated);
  }

  // Boot-Splash
  if (booting) {
    return (
      <div className="min-h-full flex items-center justify-center">
        <motion.span
          className="inline-block w-6 h-6 border-2 border-clay-500 border-t-transparent rounded-full"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
        />
      </div>
    );
  }

  // Nicht eingeloggt -> Auth-Screen
  if (!user) {
    return <Auth onAuth={setUser} />;
  }

  const activeTab = TABS.find((t) => t.id === tab);

  return (
    <div className="min-h-full pb-32">
      {/* Header */}
      <header 
        className="sticky z-30 bg-sand-50/80 backdrop-blur-md border-b border-sand-100"
        style={{ top: "env(safe-area-inset-top, 0)" }}
      >
        <div 
          className="max-w-3xl mx-auto px-5 flex items-center justify-between"
          style={{
            paddingTop: "max(env(safe-area-inset-top), 1rem)",
            paddingBottom: "1rem"
          }}
        >
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-ink-900">Vesti</h1>
            <p className="text-xs text-ink-700/60">
              {tab === TAB.WARDROBE
                ? greeting
                : user.name
                ? `Hallo, ${user.name}`
                : "Deine digitale Garderobe"}
            </p>
          </div>
          <button
            onClick={logout}
            className="text-xs font-medium text-ink-700/60 hover:text-clay-600 border border-sand-200 rounded-full px-3 py-1.5 transition"
          >
            Abmelden
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-5 pt-6">
        {error && (
          <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3 mb-4">
            {error}
          </div>
        )}

        <AnimatePresence mode="wait">
          {/* ─────────── Garderobe ─────────── */}
          {tab === TAB.WARDROBE && (
            <motion.div
              key="wardrobe"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              {loading && (
                <div className="flex justify-center py-20 text-ink-700/50">
                  <motion.span
                    className="inline-block w-6 h-6 border-2 border-clay-500 border-t-transparent rounded-full"
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                  />
                </div>
              )}

              {!loading && items.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-20"
                >
                  <div className="text-5xl mb-4">🧥</div>
                  <h2 className="text-lg font-semibold text-ink-900">
                    Deine Garderobe ist noch leer
                  </h2>
                  <p className="text-sm text-ink-700/60 mt-1 max-w-xs mx-auto">
                    Füge dein erstes Kleidungsstück hinzu – ein Foto genügt, den Rest erledigt
                    die KI.
                  </p>
                </motion.div>
              )}

              {!loading && items.length > 0 && (
                <>
                  {/* Outfit-Generator */}
                  <OutfitGenerator 
                    meta={meta} 
                    onItemClick={(id) => {
                      const item = items.find(it => it.id === id);
                      if (item) setSelected(item);
                    }} 
                  />

                  {/* Toggles: Bildquelle + Ansichtsmodus */}
                  <div className="flex items-center justify-between gap-2 mb-4">
                    {/* Bildquelle: eigene Fotos vs. KI-Produktfotos */}
                    <div className="inline-flex items-center gap-1 bg-sand-100 rounded-xl p-1">
                      <button
                        onClick={() => setUseAiImages(false)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                          !useAiImages
                            ? "bg-white text-ink-900 shadow-sm"
                            : "text-ink-700/60 hover:text-ink-900"
                        }`}
                      >
                        <span className="mr-1">📷</span> Eigene
                      </button>
                      <button
                        onClick={() => setUseAiImages(true)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                          useAiImages
                            ? "bg-white text-ink-900 shadow-sm"
                            : "text-ink-700/60 hover:text-ink-900"
                        }`}
                      >
                        <span className="mr-1">✨</span> Inszeniert
                      </button>
                    </div>

                    {/* Ansichtsmodus */}
                    <div className="inline-flex items-center gap-1 bg-sand-100 rounded-xl p-1">
                      <button
                        onClick={() => setViewMode(VIEW_MODE.GRID)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                          viewMode === VIEW_MODE.GRID
                            ? "bg-white text-ink-900 shadow-sm"
                            : "text-ink-700/60 hover:text-ink-900"
                        }`}
                      >
                        <span className="mr-1">▦</span> Grid
                      </button>
                      <button
                        onClick={() => setViewMode(VIEW_MODE.LIST)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                          viewMode === VIEW_MODE.LIST
                            ? "bg-white text-ink-900 shadow-sm"
                            : "text-ink-700/60 hover:text-ink-900"
                        }`}
                      >
                        <span className="mr-1">☰</span> Liste
                      </button>
                    </div>
                  </div>

                  <div className="space-y-8">
                    {/* Favoriten-Sektion */}
                    {grouped.favorites && grouped.favorites.length > 0 && (
                      <section>
                        <div className="flex items-center gap-3 mb-3">
                          <h2 className="text-sm font-semibold text-ink-900 uppercase tracking-wide">
                            ⭐ Favoriten
                          </h2>
                          <span className="text-xs text-ink-700/40">{grouped.favorites.length}</span>
                          <div className="flex-1 h-px bg-sand-100" />
                        </div>

                        {viewMode === VIEW_MODE.GRID && (
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                            <AnimatePresence>
                              {grouped.favorites.map((item) => (
                                <ItemCard key={item.id} item={item} onSelect={setSelected} viewMode={viewMode} useAiImages={useAiImages} />
                              ))}
                            </AnimatePresence>
                          </div>
                        )}

                        {viewMode === VIEW_MODE.LIST && (
                          <div className="space-y-2">
                            <AnimatePresence>
                              {grouped.favorites.map((item) => (
                                <ItemCard key={item.id} item={item} onSelect={setSelected} viewMode={viewMode} useAiImages={useAiImages} />
                              ))}
                            </AnimatePresence>
                          </div>
                        )}
                      </section>
                    )}

                    {/* Kategorien-Gruppen */}
                    {grouped.groups.map((group) => {
                      const groupTotal = group.items.reduce(
                        (s, i) => s + (i.quantity || 1),
                        0
                      );
                      return (
                        <section key={group.group}>
                          <div className="flex items-center gap-3 mb-3">
                            <h2 className="text-sm font-semibold text-ink-900 uppercase tracking-wide">
                              {group.group}
                            </h2>
                            <span className="text-xs text-ink-700/40">{groupTotal}</span>
                            <div className="flex-1 h-px bg-sand-100" />
                          </div>

                          {/* Grid-Ansicht */}
                          {viewMode === VIEW_MODE.GRID && (
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                              <AnimatePresence>
                                {group.items.map((item) => (
                                  <ItemCard key={item.id} item={item} onSelect={setSelected} viewMode={viewMode} useAiImages={useAiImages} />
                                ))}
                              </AnimatePresence>
                            </div>
                          )}

                          {/* Listen-Ansicht */}
                          {viewMode === VIEW_MODE.LIST && (
                            <div className="space-y-2">
                              <AnimatePresence>
                                {group.items.map((item) => (
                                  <ItemCard key={item.id} item={item} onSelect={setSelected} viewMode={viewMode} useAiImages={useAiImages} />
                                ))}
                              </AnimatePresence>
                            </div>
                          )}
                        </section>
                      );
                    })}
                  </div>
                </>
              )}
            </motion.div>
          )}

          {/* ─────────── Analyse ─────────── */}
          {tab === TAB.ANALYTICS && (
            <motion.div
              key="analytics"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <Analytics />
            </motion.div>
          )}

          {/* ─────────── Shopping ─────────── */}
          {tab === TAB.SHOPPING && (
            <motion.div
              key="shopping"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <Shopping />
            </motion.div>
          )}

          {/* ─────────── Chat ─────────── */}
          {tab === TAB.CHAT && (
            <motion.div
              key="chat"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="h-[calc(100vh-12rem)]"
            >
              <Chat />
            </motion.div>
          )}

          {/* ─────────── Profil ─────────── */}
          {tab === TAB.PROFILE && (
            <motion.div
              key="profile"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <Profile user={user} onUpdated={setUser} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Floating Add-Button nur in der Garderobe */}
      <AnimatePresence>
        {tab === TAB.WARDROBE && (
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            onClick={() => setAddOpen(true)}
            whileTap={{ scale: 0.92 }}
            className="fixed bottom-24 left-1/2 -translate-x-1/2 z-40 bg-clay-500 text-white rounded-full shadow-soft px-6 py-3.5 font-medium flex items-center gap-2 hover:bg-clay-600 transition"
          >
            <span className="text-xl leading-none">+</span> Teil hinzufügen
          </motion.button>
        )}
      </AnimatePresence>

      {/* Tab-Bar unten */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 bg-sand-50/90 backdrop-blur-md border-t border-sand-100 pb-[env(safe-area-inset-bottom)]">
        <div className="max-w-3xl mx-auto flex">
          {TABS.map((t) => {
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className="flex-1 relative py-3 flex flex-col items-center gap-0.5 transition min-w-0"
              >
                <span className={`text-lg leading-none ${active ? "" : "opacity-50 grayscale"}`}>
                  {t.icon}
                </span>
                <span
                  className={`text-[10px] sm:text-[11px] font-medium truncate w-full px-1 ${
                    active ? "text-clay-600" : "text-ink-700/50"
                  }`}
                >
                  {t.label}
                </span>
                {active && (
                  <motion.div
                    layoutId="tab-indicator"
                    className="absolute top-0 left-1/2 -translate-x-1/2 w-10 h-0.5 bg-clay-500 rounded-full"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {meta && (
        <AddItem
          open={addOpen}
          onClose={() => setAddOpen(false)}
          meta={meta}
          onCreated={handleCreated}
        />
      )}

      {meta && (
        <ItemDetail
          item={selected}
          meta={meta}
          onClose={() => setSelected(null)}
          onDeleted={handleDeleted}
          onUpdated={handleUpdated}
        />
      )}

      {/* Toast für Welcome-Messages */}
      <Toast message={toastMessage} onClose={() => setToastMessage("")} />
    </div>
  );
}
