import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, auth } from "./api";
import AddItem from "./components/AddItem";
import AddCollectionItem from "./components/AddCollectionItem";
import ItemDetail from "./components/ItemDetail";
import { AccessoryDetail, FragranceDetail, WatchDetail } from "./components/CollectionDetail";
import CollectionView from "./components/CollectionView";
import Auth from "./components/Auth";
import Profile from "./components/Profile";
import Shopping from "./components/Shopping";
import Analytics from "./components/Analytics";
import OutfitGenerator from "./components/OutfitGenerator";
import Chat from "./components/Chat";
import ErrorBoundary from "./components/ErrorBoundary";
import SavedOutfits from "./components/SavedOutfits";
import OutfitBuilder from "./components/OutfitBuilder";

// Vier Haupteinträge in der Bottom-Bar. Die Sammlungen sind bewusst KEINE
// eigenen Tabs, sondern liegen als Segmented Control innerhalb von "Sammlung" –
// sieben Tabs wären auf einem Handy nicht mehr bedienbar.
const TAB = {
  COLLECTION: "collection",
  OUTFITS: "outfits",
  ANALYTICS: "analytics",
  SHOPPING: "shopping",
  CHAT: "chat",
};

const TABS = [
  { id: TAB.COLLECTION, label: "Sammlung", icon: "🧥" },
  { id: TAB.OUTFITS,    label: "Outfits",  icon: "👔" },
  { id: TAB.ANALYTICS,  label: "Analyse",  icon: "📊" },
  { id: TAB.SHOPPING,   label: "Shopping", icon: "🛍️" },
  { id: TAB.CHAT,       label: "Chat",     icon: "💬" },
];

const KIND = {
  CLOTHING: "clothing",
  WATCHES: "watches",
  ACCESSORIES: "accessories",
  FRAGRANCES: "fragrances",
};

const KINDS = [
  { id: KIND.CLOTHING,   label: "Kleidung",    icon: "👕" },
  { id: KIND.WATCHES,    label: "Uhren",        icon: "⌚" },
  { id: KIND.ACCESSORIES, label: "Accessoires", icon: "💎" },
  { id: KIND.FRAGRANCES, label: "Düfte",        icon: "🧴" },
];

const ADD_LABEL = {
  [KIND.CLOTHING]:   "Teil hinzufügen",
  [KIND.WATCHES]:    "Uhr hinzufügen",
  [KIND.ACCESSORIES]: "Accessoire hinzufügen",
  [KIND.FRAGRANCES]: "Duft hinzufügen",
};

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
  "Vom Hemd bis zum Duft – heute stimmt alles.",
  "Bereit für das, was heute kommt. 💼",
  "Finde genau das, was heute zu dir passt.",
  "Qualität und Stil, die man sieht.",
  "Dein Look für heute steht fast fest.",
  "Kleidung ist Ausdruck. Was sagst du heute? 🖋️",
  "Stilbewusst durch den ganzen Tag.",
  "Heute überlassen wir nichts dem Zufall.",
  "Die richtige Uhr macht den Unterschied. ⌚",
  "Weniger suchen, besser kleiden. 🧥",
  "Finde den Look, der dich heute begleitet.",
  "Eleganz beginnt bei der Auswahl.",
  "Mach den heutigen Tag zu deinem.",
  "Perfekt abgestimmt in den Tag starten.",
  "Dein Stil ist deine beste Visitenkarte.",
  "Zeit für einen Look, der genau zu dir passt.",
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
          <span className="block text-xs text-ink-700/50 truncate">{item.color}</span>
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
      <span className="text-ink-700/30 group-hover:text-ink-700/60 transition">→</span>
    </motion.button>
  );
}

// Multi-field fuzzy Suche – läuft komplett clientseitig, kein API-Call.
// Teilt die Query in einzelne Tokens und prüft ob alle im Such-String des Items vorkommen.
// Das fühlt sich semantisch an: "blaues leichtes Sommerhemd" findet auch ein Leinenhemd
// das als blau + leicht + Sommer klassifiziert ist, auch wenn der Name anders lautet.
function buildSearchString(item) {
  const fields = [
    item.name, item.category, item.color, item.material,
    item.pattern, item.style, item.occasion, item.season,
    item.description, item.brand,
    // Details-Objekt flach als Werte
    ...(item.details ? Object.values(item.details).map(String) : []),
    // Uhren-spezifisch
    item.model, item.reference, item.movement, item.case_material,
    item.dial_color, item.band_material, item.crystal,
    ...(item.complications || []), ...(item.occasions || []),
    // Düfte
    item.line, item.concentration, item.family, item.secondary_family,
    item.perfumer, item.audience,
    ...(item.top_notes || []), ...(item.heart_notes || []), ...(item.base_notes || []),
    ...(item.seasons || []),
    // Accessoires
    item.type, item.stone, item.secondary_material, item.color,
    item.condition,
  ];
  return fields.filter(Boolean).join(" ").toLowerCase();
}

function fuzzySearch(items, query) {
  if (!query.trim()) return items;
  const tokens = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return items.filter((item) => {
    const haystack = buildSearchString(item);
    return tokens.every((token) => haystack.includes(token));
  });
}
function KindSwitcher({ kind, setKind, counts }) {
  const [open, setOpen] = useState(false);
  const current = KINDS.find((k) => k.id === kind);

  return (
    <div className="border-t border-sand-100 px-5 py-2.5 relative">
      {/* Trigger */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 group"
      >
        <span className="text-base leading-none">{current.icon}</span>
        <span className="text-sm font-semibold text-ink-900">{current.label}</span>
        {counts[kind] > 0 && (
          <span className="text-xs text-ink-700/40 tabular-nums">{counts[kind]}</span>
        )}
        <motion.svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 16 16"
          fill="currentColor"
          className="w-3.5 h-3.5 text-ink-700/40 ml-0.5"
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.18 }}
        >
          <path fillRule="evenodd" d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
        </motion.svg>
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: -6, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.97 }}
              transition={{ duration: 0.15 }}
              className="absolute left-4 top-full mt-1.5 z-50 bg-white rounded-2xl shadow-lg border border-sand-100 overflow-hidden min-w-[180px]"
            >
              {KINDS.map((k, i) => {
                const active = kind === k.id;
                return (
                  <button
                    key={k.id}
                    onClick={() => { setKind(k.id); setOpen(false); }}
                    className={`w-full flex items-center justify-between gap-3 px-4 py-3 text-sm transition
                      ${i > 0 ? "border-t border-sand-50" : ""}
                      ${active ? "bg-clay-500/5 text-clay-600" : "text-ink-800 hover:bg-sand-50"}`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className={active ? "" : "opacity-60"}>{k.icon}</span>
                      <span className={active ? "font-semibold" : "font-medium"}>{k.label}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {counts[k.id] > 0 && (
                        <span className={`text-xs tabular-nums ${active ? "text-clay-500" : "text-ink-700/30"}`}>
                          {counts[k.id]}
                        </span>
                      )}
                      {active && (
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5 text-clay-500">
                          <path fillRule="evenodd" d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                  </button>
                );
              })}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Konto-Sheet: alles Sekundäre wandert aus dem Header hierher ──
function AccountSheet({ open, user, onClose, onOpenProfile, onLogout }) {
  const initials = (user.name || user.email || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div
            className="absolute inset-0 bg-ink-900/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            className="relative w-full sm:max-w-sm bg-sand-50 rounded-t-3xl sm:rounded-3xl shadow-soft p-5"
            style={{ paddingBottom: "max(env(safe-area-inset-bottom), 1.25rem)" }}
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
          >
            <div className="flex items-center gap-3 pb-4 border-b border-sand-100">
              <div className="w-12 h-12 rounded-full bg-clay-500 text-white flex items-center justify-center font-semibold">
                {initials}
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-ink-900 truncate">
                  {user.name || "Dein Konto"}
                </p>
                <p className="text-xs text-ink-700/60 truncate">{user.email}</p>
              </div>
            </div>

            <div className="pt-3 space-y-1">
              <button
                onClick={() => {
                  onClose();
                  onOpenProfile();
                }}
                className="w-full text-left px-3 py-3 rounded-xl hover:bg-sand-100 transition flex items-center gap-3"
              >
                <span className="text-lg">👤</span>
                <div>
                  <p className="text-sm font-medium text-ink-900">Profil & Maße</p>
                  <p className="text-xs text-ink-700/50">
                    Körpermaße, Größen und Stil-Notizen
                  </p>
                </div>
              </button>
              <button
                onClick={onLogout}
                className="w-full text-left px-3 py-3 rounded-xl hover:bg-clay-500/5 transition flex items-center gap-3"
              >
                <span className="text-lg">🚪</span>
                <p className="text-sm font-medium text-clay-600">Abmelden</p>
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(true);
  const [tab, setTab] = useState(TAB.COLLECTION);
  const [kind, setKind] = useState(() => {
    const saved = localStorage.getItem("vesti-collection-kind");
    return Object.values(KIND).includes(saved) ? saved : KIND.CLOTHING;
  });
  const [viewMode, setViewMode] = useState(() => {
    const saved = localStorage.getItem("vesti-view-mode");
    return saved === VIEW_MODE.LIST ? VIEW_MODE.LIST : VIEW_MODE.GRID;
  });
  const [useAiImages, setUseAiImages] = useState(
    () => localStorage.getItem("vesti-image-source") === "ai"
  );

  const [meta, setMeta] = useState(null);
  const [items, setItems] = useState([]);
  const [watches, setWatches] = useState([]);
  const [accessories, setAccessories] = useState([]);
  const [fragrances, setFragrances] = useState([]);
  const [pending, setPending] = useState({ watches: 0, fragrances: 0, total: 0 });
  const [loading, setLoading] = useState(true);

  const [addOpen, setAddOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [selectedWatch, setSelectedWatch] = useState(null);
  const [selectedAccessory, setSelectedAccessory] = useState(null);
  const [selectedFragrance, setSelectedFragrance] = useState(null);
  const [accountOpen, setAccountOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [outfitBuilderOpen, setOutfitBuilderOpen] = useState(false);
  const [outfitBuilderPrefill, setOutfitBuilderPrefill] = useState(null);
  const [error, setError] = useState("");
  const [greeting, setGreeting] = useState(getRandomGreeting());

  const anyOverlay =
    selectedItem || selectedWatch || selectedAccessory || selectedFragrance || addOpen || profileOpen;

  // Android/iOS Zurück-Button: Overlay schließen statt App verlassen
  useEffect(() => {
    function onPopState() {
      if (selectedItem) return setSelectedItem(null);
      if (selectedWatch) return setSelectedWatch(null);
      if (selectedAccessory) return setSelectedAccessory(null);
      if (selectedFragrance) return setSelectedFragrance(null);
      if (profileOpen) return setProfileOpen(false);
      if (addOpen) return setAddOpen(false);
      history.pushState({ overlay: false }, "");
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [selectedItem, selectedWatch, selectedFragrance, addOpen, profileOpen]);

  useEffect(() => {
    if (anyOverlay) history.pushState({ overlay: true }, "");
  }, [anyOverlay]);

  useEffect(() => {
    if (tab === TAB.COLLECTION) setGreeting(getRandomGreeting());
  }, [tab]);

  useEffect(() => {
    localStorage.setItem("vesti-view-mode", viewMode);
  }, [viewMode]);

  useEffect(() => {
    localStorage.setItem("vesti-image-source", useAiImages ? "ai" : "own");
  }, [useAiImages]);

  useEffect(() => {
    localStorage.setItem("vesti-collection-kind", kind);
  }, [kind]);

  // Beim Start: Token prüfen und Nutzer laden
  useEffect(() => {
    (async () => {
      if (!auth.token) {
        setBooting(false);
        return;
      }
      try {
        setUser(await api.me());
      } catch {
        auth.clear();
      } finally {
        setBooting(false);
      }
    })();
  }, []);

  useEffect(() => {
    const handler = () => setUser(null);
    window.addEventListener("vesti-unauthorized", handler);
    return () => window.removeEventListener("vesti-unauthorized", handler);
  }, []);

  // Alle drei Sammlungen parallel laden
  useEffect(() => {
    if (!user) return;
    setLoading(true);
    (async () => {
      try {
        const [m, list, watchList, fragranceList, accessoryList] = await Promise.all([
          api.getMeta(),
          api.listItems(),
          api.listWatches(),
          api.listFragrances(),
          api.listAccessories(),
        ]);
        setMeta(m);
        setItems(list);
        setWatches(watchList);
        setFragrances(fragranceList);
        setAccessories(accessoryList);
        api.getPendingReview().then(setPending).catch(() => {});
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
    setWatches([]);
    setAccessories([]);
    setFragrances([]);
    setSelectedItem(null);
    setSelectedWatch(null);
    setSelectedAccessory(null);
    setSelectedFragrance(null);
    setAccountOpen(false);
    setProfileOpen(false);
    setTab(TAB.COLLECTION);
  }, []);

  // Kleidung nach Kategorie-Gruppen, Favoriten zuerst, neu vor alt
  const grouped = useMemo(() => {
    if (!meta) return { favorites: [], groups: [] };

    const sorted = [...items].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );
    const filtered = fuzzySearch(sorted, searchQuery);
    const favorites = filtered.filter((it) => it.favorite);
    const nonFavorites = filtered.filter((it) => !it.favorite);

    const groupMap = new Map();
    for (const item of nonFavorites) {
      const metaGroup = meta.category_groups.find((g) =>
        g.items.includes(item.category)
      );
      const groupName = metaGroup ? metaGroup.group : "Sonstiges";
      if (!groupMap.has(groupName)) groupMap.set(groupName, []);
      groupMap.get(groupName).push(item);
    }

    const groups = meta.category_groups
      .filter((g) => groupMap.has(g.group))
      .map((g) => ({ group: g.group, items: groupMap.get(g.group) }));

    // Kategorien die nicht mehr im Vokabular stehen (z.B. nach einer Umbenennung)
    for (const [name, list] of groupMap) {
      if (!groups.some((g) => g.group === name)) {
        groups.push({ group: name, items: list });
      }
    }

    return { favorites, groups };
  }, [items, meta, searchQuery]);

  const counts = {
    [KIND.CLOTHING]: items.reduce((sum, i) => sum + (i.quantity || 1), 0),
    [KIND.WATCHES]: watches.length,
    [KIND.ACCESSORIES]: accessories.length,
    [KIND.FRAGRANCES]: fragrances.length,
  };

  // ── Handler pro Sammlung ──
  function upsert(setter) {
    return (entry) =>
      setter((prev) => {
        const exists = prev.some((e) => e.id === entry.id);
        return exists ? prev.map((e) => (e.id === entry.id ? entry : e)) : [entry, ...prev];
      });
  }

  const addWatch = upsert(setWatches);
  const addAccessory = upsert(setAccessories);
  const addFragrance = upsert(setFragrances);

  function refreshPending() {
    api.getPendingReview().then(setPending).catch(() => {});
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

  if (!user) return <Auth onAuth={setUser} />;

  const initials = (user.name || user.email || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");

  const addKind =
    kind === KIND.WATCHES ? "watch"
    : kind === KIND.ACCESSORIES ? "accessory"
    : kind === KIND.FRAGRANCES ? "fragrance"
    : "clothing";

  return (
    <div className="min-h-full pb-32">
      {/* Header */}
      <header
        className="sticky z-30 bg-sand-50/80 backdrop-blur-md border-b border-sand-100"
        style={{ top: "env(safe-area-inset-top, 0)" }}
      >
        <div
          className="max-w-3xl mx-auto px-5 flex items-center justify-between gap-3"
          style={{
            paddingTop: "max(env(safe-area-inset-top), 1rem)",
            paddingBottom: "1rem",
          }}
        >
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-tight text-ink-900">Vesti</h1>
            <p className="text-xs text-ink-700/60 truncate">
              {tab === TAB.COLLECTION
                ? greeting
                : user.name
                ? `Hallo, ${user.name}`
                : "Deine digitale Garderobe"}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {tab === TAB.COLLECTION && (
              <button
                onClick={() => {
                  setSearchOpen((v) => !v);
                  setSearchQuery("");
                }}
                aria-label="Suchen"
                className={`w-10 h-10 rounded-full flex items-center justify-center transition ${
                  searchOpen
                    ? "bg-clay-500 text-white"
                    : "bg-sand-100 text-ink-700/70 hover:bg-sand-200"
                }`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4.5 h-4.5 w-[18px] h-[18px]">
                  <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.452 4.391l3.328 3.329a.75.75 0 1 1-1.06 1.06l-3.329-3.328A7 7 0 0 1 2 9Z" clipRule="evenodd" />
                </svg>
              </button>
            )}
            <button
              onClick={() => setAccountOpen(true)}
              className="w-10 h-10 flex-shrink-0 rounded-full bg-clay-500 text-white text-sm font-semibold flex items-center justify-center hover:bg-clay-600 transition"
              aria-label="Konto und Profil"
            >
              {initials}
            </button>
          </div>
        </div>

        {/* Suchleiste – aufklappbar */}
        <AnimatePresence>
          {tab === TAB.COLLECTION && searchOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="overflow-hidden"
            >
              <div className="max-w-3xl mx-auto px-5 pb-3">
                <div className="relative">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"
                    className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ink-700/40 pointer-events-none">
                    <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.452 4.391l3.328 3.329a.75.75 0 1 1-1.06 1.06l-3.329-3.328A7 7 0 0 1 2 9Z" clipRule="evenodd" />
                  </svg>
                  <input
                    autoFocus
                    type="search"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={
                      kind === KIND.CLOTHING ? "z.B. blaues Leinenhemd, Sommer, Nike…"
                      : kind === KIND.WATCHES ? "z.B. Rolex, Automatik, Stahl…"
                      : kind === KIND.FRAGRANCES ? "z.B. holzig, Dior, EdP…"
                      : "z.B. Leder, Ring, Gucci…"
                    }
                    className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-sand-200 bg-white text-sm focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery("")}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-700/40 hover:text-ink-700"
                    >
                      ×
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {tab === TAB.COLLECTION && (
          <div className="max-w-3xl mx-auto">
            <KindSwitcher kind={kind} setKind={setKind} counts={counts} />
          </div>
        )}
      </header>

      <main className="max-w-3xl mx-auto px-5 pt-6">
        {error && (
          <div className="rounded-xl bg-clay-500/10 text-clay-600 text-sm px-4 py-3 mb-4">
            {error}
          </div>
        )}

        <ErrorBoundary resetKey={tab}>
        <AnimatePresence mode="wait">
          {/* ─────────── Sammlung ─────────── */}
          {tab === TAB.COLLECTION && (
            <motion.div
              key="collection"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              {/* Hinweis auf migrierte Einträge ohne technische Daten */}
              {pending.total > 0 && kind === KIND.WATCHES && pending.watches > 0 && (
                <div className="rounded-2xl bg-amber-400/10 px-4 py-3 mb-6">
                  <p className="text-sm text-ink-800">
                    {pending.watches === 1
                      ? "Eine Uhr wurde aus der Kleidungs-Garderobe übernommen und wartet noch auf die KI-Erfassung."
                      : `${pending.watches} Uhren wurden aus der Kleidungs-Garderobe übernommen und warten noch auf die KI-Erfassung.`}{" "}
                    Öffne sie und tippe auf „Jetzt per KI erfassen".
                  </p>
                </div>
              )}
              {pending.total > 0 && kind === KIND.ACCESSORIES && pending.accessories > 0 && (
                <div className="rounded-2xl bg-amber-400/10 px-4 py-3 mb-6">
                  <p className="text-sm text-ink-800">
                    {pending.accessories === 1
                      ? "Ein Accessoire wurde aus der Kleidungs-Garderobe übernommen und wartet noch auf die KI-Erfassung."
                      : `${pending.accessories} Accessoires wurden aus der Kleidungs-Garderobe übernommen und warten noch auf die KI-Erfassung.`}{" "}
                    Öffne es und tippe auf „Jetzt per KI erfassen".
                  </p>
                </div>
              )}

              {/* ── Kleidung ── */}
              {kind === KIND.CLOTHING && (
                <>
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
                        Füge dein erstes Kleidungsstück hinzu – ein Foto genügt, den Rest
                        erledigt die KI.
                      </p>
                    </motion.div>
                  )}

                  {!loading && items.length > 0 && (
                    <>
                      <OutfitGenerator
                        meta={meta}
                        useAiImages={useAiImages}
                        onItemClick={(id) => {
                          const item = items.find((it) => it.id === id);
                          if (item) setSelectedItem(item);
                        }}
                        onWatchClick={(id) => {
                          const w = watches.find((it) => it.id === id);
                          if (w) setSelectedWatch(w);
                        }}
                        onAccessoryClick={(id) => {
                          const a = accessories.find((it) => it.id === id);
                          if (a) setSelectedAccessory(a);
                        }}
                        onFragranceClick={(id) => {
                          const f = fragrances.find((it) => it.id === id);
                          if (f) setSelectedFragrance(f);
                        }}
                        onExport={(outfit) => {
                          setOutfitBuilderPrefill(outfit);
                          setOutfitBuilderOpen(true);
                          setTab(TAB.OUTFITS);
                        }}
                      />

                      <div className="flex items-center justify-between gap-2 mb-4">
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
                        {/* Keine Treffer bei aktiver Suche */}
                        {searchQuery && grouped.favorites.length === 0 && grouped.groups.length === 0 && (
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="text-center py-16"
                          >
                            <div className="text-4xl mb-3">🔍</div>
                            <p className="text-sm font-medium text-ink-900">Keine Treffer für „{searchQuery}"</p>
                            <p className="text-xs text-ink-700/50 mt-1">Versuch andere Begriffe – Farbe, Material, Anlass oder Marke</p>
                          </motion.div>
                        )}
                        {grouped.favorites.length > 0 && (
                          <section>
                            <div className="flex items-center gap-3 mb-3">
                              <h2 className="text-sm font-semibold text-ink-900 uppercase tracking-wide">
                                ⭐ Favoriten
                              </h2>
                              <span className="text-xs text-ink-700/40">
                                {grouped.favorites.length}
                              </span>
                              <div className="flex-1 h-px bg-sand-100" />
                            </div>
                            <div
                              className={
                                viewMode === VIEW_MODE.GRID
                                  ? "grid grid-cols-2 sm:grid-cols-3 gap-3"
                                  : "space-y-2"
                              }
                            >
                              <AnimatePresence>
                                {grouped.favorites.map((item) => (
                                  <ItemCard
                                    key={item.id}
                                    item={item}
                                    onSelect={setSelectedItem}
                                    viewMode={viewMode}
                                    useAiImages={useAiImages}
                                  />
                                ))}
                              </AnimatePresence>
                            </div>
                          </section>
                        )}

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
                                <span className="text-xs text-ink-700/40">
                                  {groupTotal}
                                </span>
                                <div className="flex-1 h-px bg-sand-100" />
                              </div>
                              <div
                                className={
                                  viewMode === VIEW_MODE.GRID
                                    ? "grid grid-cols-2 sm:grid-cols-3 gap-3"
                                    : "space-y-2"
                                }
                              >
                                <AnimatePresence>
                                  {group.items.map((item) => (
                                    <ItemCard
                                      key={item.id}
                                      item={item}
                                      onSelect={setSelectedItem}
                                      viewMode={viewMode}
                                      useAiImages={useAiImages}
                                    />
                                  ))}
                                </AnimatePresence>
                              </div>
                            </section>
                          );
                        })}
                      </div>
                    </>
                  )}
                </>
              )}

              {/* ── Uhren ── */}
              {kind === KIND.WATCHES && (
                <CollectionView
                  kind="watch"
                  entries={fuzzySearch(watches, searchQuery)}
                  meta={meta}
                  loading={loading}
                  viewMode={viewMode}
                  setViewMode={setViewMode}
                  useAiImages={useAiImages}
                  setUseAiImages={setUseAiImages}
                  onSelect={setSelectedWatch}
                  onSelectId={(id) => {
                    const w = watches.find((it) => it.id === id);
                    if (w) setSelectedWatch(w);
                  }}
                />
              )}

              {/* ── Accessoires ── */}
              {kind === KIND.ACCESSORIES && (
                <CollectionView
                  kind="accessory"
                  entries={fuzzySearch(accessories, searchQuery)}
                  meta={meta}
                  loading={loading}
                  viewMode={viewMode}
                  setViewMode={setViewMode}
                  useAiImages={useAiImages}
                  setUseAiImages={setUseAiImages}
                  onSelect={setSelectedAccessory}
                  onSelectId={(id) => {
                    const a = accessories.find((it) => it.id === id);
                    if (a) setSelectedAccessory(a);
                  }}
                />
              )}

              {/* ── Düfte ── */}
              {kind === KIND.FRAGRANCES && (
                <CollectionView
                  kind="fragrance"
                  entries={fuzzySearch(fragrances, searchQuery)}
                  meta={meta}
                  loading={loading}
                  viewMode={viewMode}
                  setViewMode={setViewMode}
                  useAiImages={useAiImages}
                  setUseAiImages={setUseAiImages}
                  onSelect={setSelectedFragrance}
                  onSelectId={(id) => {
                    const f = fragrances.find((it) => it.id === id);
                    if (f) setSelectedFragrance(f);
                  }}
                />
              )}
            </motion.div>
          )}

          {/* ─────────── Outfits ─────────── */}
          {tab === TAB.OUTFITS && (
            <motion.div
              key="outfits"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <SavedOutfits
                items={items}
                watches={watches}
                fragrances={fragrances}
                accessories={accessories}
                meta={meta}
                useAiImages={useAiImages}
              />
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
              <Analytics
                hasWatches={watches.length > 0}
                hasFragrances={fragrances.length > 0}
                hasAccessories={accessories.length > 0}
              />
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
              <Chat hasWatches={watches.length > 0} hasFragrances={fragrances.length > 0} />
            </motion.div>
          )}
        </AnimatePresence>
        </ErrorBoundary>
      </main>

      {/* Kontextsensitiver Add-Button */}
      <AnimatePresence>
        {tab === TAB.COLLECTION && (
          <motion.button
            key={kind}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            onClick={() => setAddOpen(true)}
            whileTap={{ scale: 0.92 }}
            className="fixed bottom-24 left-1/2 -translate-x-1/2 z-40 bg-clay-500 text-white rounded-full shadow-soft px-6 py-3.5 font-medium flex items-center gap-2 hover:bg-clay-600 transition"
          >
            <span className="text-xl leading-none">+</span> {ADD_LABEL[kind]}
          </motion.button>
        )}
        {tab === TAB.OUTFITS && (
          <motion.button
            key="new-outfit"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            onClick={() => { setOutfitBuilderPrefill(null); setOutfitBuilderOpen(true); }}
            whileTap={{ scale: 0.92 }}
            className="fixed bottom-24 left-1/2 -translate-x-1/2 z-40 bg-clay-500 text-white rounded-full shadow-soft px-6 py-3.5 font-medium flex items-center gap-2 hover:bg-clay-600 transition"
          >
            <span className="text-xl leading-none">+</span> Outfit erstellen
          </motion.button>
        )}
      </AnimatePresence>

      {/* Globaler OutfitBuilder (für Export aus OutfitGenerator) */}
      <OutfitBuilder
        open={outfitBuilderOpen}
        onClose={() => { setOutfitBuilderOpen(false); setOutfitBuilderPrefill(null); }}
        onSaved={() => {}}
        items={items}
        watches={watches}
        fragrances={fragrances}
        accessories={accessories}
        meta={meta}
        useAiImages={useAiImages}
        prefill={outfitBuilderPrefill}
      />

      {/* Bottom-Bar */}
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
                <span
                  className={`text-lg leading-none ${
                    active ? "" : "opacity-50 grayscale"
                  }`}
                >
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

      {/* Erfassung: Kleidung bzw. Uhren/Düfte */}
      {meta && addKind === "clothing" && (
        <AddItem
          open={addOpen}
          onClose={() => setAddOpen(false)}
          meta={meta}
          onCreated={(item) => setItems((prev) => [item, ...prev])}
        />
      )}
      {meta && addKind !== "clothing" && (
        <AddCollectionItem
          open={addOpen}
          kind={addKind}
          onClose={() => setAddOpen(false)}
          meta={meta}
          onCreated={(entry) => {
            if (addKind === "watch") addWatch(entry);
            else if (addKind === "accessory") addAccessory(entry);
            else addFragrance(entry);
          }}
        />
      )}

      {/* Detail-Ansichten */}
      {meta && (
        <ItemDetail
          item={selectedItem}
          meta={meta}
          useAiImages={useAiImages}
          onClose={() => setSelectedItem(null)}
          onDeleted={(id) => {
            setItems((prev) => prev.filter((i) => i.id !== id));
            setSelectedItem(null);
          }}
          onUpdated={(updated) => {
            setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
            setSelectedItem(updated);
          }}
        />
      )}

      <WatchDetail
        watch={selectedWatch}
        meta={meta}
        onClose={() => setSelectedWatch(null)}
        onDeleted={(id) => {
          setWatches((prev) => prev.filter((w) => w.id !== id));
          setSelectedWatch(null);
          refreshPending();
        }}
        onUpdated={(updated) => {
          addWatch(updated);
          setSelectedWatch(updated);
          refreshPending();
        }}
      />

      <AccessoryDetail
        accessory={selectedAccessory}
        meta={meta}
        onClose={() => setSelectedAccessory(null)}
        onDeleted={(id) => {
          setAccessories((prev) => prev.filter((a) => a.id !== id));
          setSelectedAccessory(null);
          refreshPending();
        }}
        onUpdated={(updated) => {
          addAccessory(updated);
          setSelectedAccessory(updated);
          refreshPending();
        }}
      />

      <FragranceDetail
        fragrance={selectedFragrance}
        meta={meta}
        onClose={() => setSelectedFragrance(null)}
        onDeleted={(id) => {
          setFragrances((prev) => prev.filter((f) => f.id !== id));
          setSelectedFragrance(null);
          refreshPending();
        }}
        onUpdated={(updated) => {
          addFragrance(updated);
          setSelectedFragrance(updated);
          refreshPending();
        }}
      />

      {/* Konto */}
      <AccountSheet
        open={accountOpen}
        user={user}
        onClose={() => setAccountOpen(false)}
        onOpenProfile={() => setProfileOpen(true)}
        onLogout={logout}
      />

      {/* Profil als Vollbild-Overlay, damit es kein eigener Tab sein muss */}
      <AnimatePresence>
        {profileOpen && (
          <motion.div
            className="fixed inset-0 z-50 flex flex-col bg-sand-50"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          >
            <div
              className="flex-shrink-0 px-5 pb-3 border-b border-sand-100 bg-sand-50/90 backdrop-blur-md flex items-center justify-between"
              style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
            >
              <h2 className="text-xl font-bold text-ink-900 tracking-tight">
                Profil & Maße
              </h2>
              <button
                onClick={() => setProfileOpen(false)}
                className="w-9 h-9 rounded-full bg-sand-100 text-ink-700 flex items-center justify-center text-xl leading-none hover:bg-sand-200 transition"
                aria-label="Schließen"
              >
                ×
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-5">
              <div className="max-w-3xl mx-auto">
                <Profile user={user} onUpdated={setUser} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
