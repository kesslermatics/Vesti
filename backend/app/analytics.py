"""Berechnet Statistiken ueber die Garderobe eines Nutzers.

Alle Auswertungen laufen rein rechnerisch (ohne KI), damit der Analyse-Tab
sofort laedt. Die KI-Einschaetzung kommt separat und optional dazu.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from .categories import CATEGORY_GROUPS

# Farb-Normalisierung: freie KI-Farbtexte auf Basisfarben mappen
COLOR_BUCKETS: dict[str, tuple[str, str]] = {
    # key-fragment -> (Anzeigename, Hex fuer die UI)
    "schwarz": ("Schwarz", "#1c1916"),
    "weiß": ("Weiß", "#f5f2ed"),
    "weiss": ("Weiß", "#f5f2ed"),
    "grau": ("Grau", "#9b968f"),
    "anthrazit": ("Grau", "#9b968f"),
    "silber": ("Grau", "#9b968f"),
    "blau": ("Blau", "#4a6fa5"),
    "navy": ("Blau", "#4a6fa5"),
    "denim": ("Blau", "#4a6fa5"),
    "türkis": ("Blau", "#4a6fa5"),
    "grün": ("Grün", "#6b8f63"),
    "gruen": ("Grün", "#6b8f63"),
    "oliv": ("Grün", "#6b8f63"),
    "khaki": ("Beige", "#c4b39a"),
    "beige": ("Beige", "#c4b39a"),
    "creme": ("Beige", "#c4b39a"),
    "sand": ("Beige", "#c4b39a"),
    "camel": ("Beige", "#c4b39a"),
    "braun": ("Braun", "#8a6a4f"),
    "cognac": ("Braun", "#8a6a4f"),
    "rot": ("Rot", "#b5453c"),
    "bordeaux": ("Rot", "#b5453c"),
    "weinrot": ("Rot", "#b5453c"),
    "rosa": ("Rosa", "#d3a1a8"),
    "pink": ("Rosa", "#d3a1a8"),
    "altrosa": ("Rosa", "#d3a1a8"),
    "gelb": ("Gelb", "#d9b64e"),
    "senf": ("Gelb", "#d9b64e"),
    "orange": ("Orange", "#c97f4a"),
    "lila": ("Lila", "#8a6f9e"),
    "violett": ("Lila", "#8a6f9e"),
    "gold": ("Metallic", "#b9973f"),
    "bunt": ("Bunt", "#a8867a"),
    "mehrfarbig": ("Bunt", "#a8867a"),
}

NEUTRAL_COLORS = {"Schwarz", "Weiß", "Grau", "Beige", "Braun"}

# Grobe Zuordnung Kategorie -> Outfit-Slot, um Luecken zu erkennen
SLOT_BY_GROUP = {
    "Oberteile": "Oberteil",
    "Pullover & Hoodies": "Oberteil",
    "Hosen": "Unterteil",
    "Röcke & Kleider": "Unterteil",
    "Jacken & Mäntel": "Oberbekleidung",
    "Anzüge & Sets": "Komplett",
    "Schuhe": "Schuhe",
    "Accessoires": "Accessoire",
    "Unterwäsche & Basics": "Basics",
    "Sport & Freizeit": "Sport",
    "Sonstiges": "Sonstiges",
}

GROUP_BY_CATEGORY: dict[str, str] = {
    item: grp["group"] for grp in CATEGORY_GROUPS for item in grp["items"]
}


def _bucket_color(raw: str) -> tuple[str, str] | None:
    """Mappt einen freien Farbtext auf eine Basisfarbe."""
    if not raw:
        return None
    low = raw.lower()
    for fragment, bucket in COLOR_BUCKETS.items():
        if fragment in low:
            return bucket
    return ("Sonstige", "#a8a29a")


def _counter_to_list(counter: Counter, total: int) -> list[dict[str, Any]]:
    return [
        {
            "label": label,
            "count": count,
            "share": round(count / total * 100) if total else 0,
        }
        for label, count in counter.most_common()
    ]


def compute_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Berechnet alle Kennzahlen fuer den Analyse-Tab."""
    total_entries = len(items)
    total_pieces = sum(int(i.get("quantity") or 1) for i in items)

    if total_entries == 0:
        return {
            "empty": True,
            "total_entries": 0,
            "total_pieces": 0,
        }

    # --- Zaehler aufbauen (gewichtet nach Stueckzahl) ---
    cat_counter: Counter = Counter()
    group_counter: Counter = Counter()
    slot_counter: Counter = Counter()
    color_counter: Counter = Counter()
    color_hex: dict[str, str] = {}
    material_counter: Counter = Counter()
    style_counter: Counter = Counter()
    season_counter: Counter = Counter()
    occasion_counter: Counter = Counter()
    brand_counter: Counter = Counter()

    for it in items:
        qty = int(it.get("quantity") or 1)
        cat = it.get("category") or "Sonstiges"
        grp = GROUP_BY_CATEGORY.get(cat, "Sonstiges")

        cat_counter[cat] += qty
        group_counter[grp] += qty
        slot_counter[SLOT_BY_GROUP.get(grp, "Sonstiges")] += qty

        bucket = _bucket_color(it.get("color") or "")
        if bucket:
            name, hexcode = bucket
            color_counter[name] += qty
            color_hex[name] = hexcode

        if it.get("material"):
            material_counter[it["material"]] += qty
        if it.get("style"):
            style_counter[it["style"]] += qty
        if it.get("season"):
            season_counter[it["season"]] += qty
        if it.get("occasion"):
            occasion_counter[it["occasion"]] += qty
        if it.get("brand"):
            brand_counter[it["brand"]] += qty

    # --- Farb-Verteilung mit Hex ---
    colors = [
        {
            "label": label,
            "count": count,
            "share": round(count / total_pieces * 100),
            "hex": color_hex.get(label, "#a8a29a"),
        }
        for label, count in color_counter.most_common()
    ]

    neutral_pieces = sum(c["count"] for c in colors if c["label"] in NEUTRAL_COLORS)
    neutral_share = round(neutral_pieces / total_pieces * 100) if total_pieces else 0

    # --- Vielfalt: wie viele verschiedene Kategorien / Farben ---
    diversity = {
        "categories": len(cat_counter),
        "colors": len(color_counter),
        "materials": len(material_counter),
        "brands": len(brand_counter),
    }

    # --- Kombinations-Potenzial: Oberteile x Unterteile x Schuhe ---
    tops = slot_counter.get("Oberteil", 0)
    bottoms = slot_counter.get("Unterteil", 0)
    shoes = slot_counter.get("Schuhe", 0)
    combinations = tops * bottoms * max(shoes, 1)

    # --- Luecken erkennen ---
    gaps: list[str] = []
    if tops == 0:
        gaps.append("Dir fehlen Oberteile – ohne die geht kein Outfit.")
    if bottoms == 0:
        gaps.append("Dir fehlen Hosen, Röcke oder Kleider.")
    if shoes == 0:
        gaps.append("Du hast noch keine Schuhe erfasst.")
    if slot_counter.get("Oberbekleidung", 0) == 0:
        gaps.append("Keine Jacke oder Mantel – für kühle Tage fehlt eine Schicht.")
    if tops and bottoms and tops < bottoms:
        gaps.append("Du hast mehr Unterteile als Oberteile – Oberteile begrenzen deine Kombinationen.")
    if bottoms and tops and bottoms * 3 < tops:
        gaps.append("Sehr viele Oberteile bei wenigen Hosen – ein weiteres Unterteil bringt viele neue Looks.")

    # Saison-Luecken
    seasonal = {s: 0 for s in ("Frühling", "Sommer", "Herbst", "Winter")}
    for label, count in season_counter.items():
        if label == "ganzjährig":
            for s in seasonal:
                seasonal[s] += count
        elif label in seasonal:
            seasonal[label] += count
    weakest_season = min(seasonal, key=lambda s: seasonal[s]) if any(seasonal.values()) else None
    if weakest_season and seasonal[weakest_season] < total_pieces * 0.15:
        gaps.append(f"Für {weakest_season} hast du auffällig wenig – hier lohnt sich Nachschub.")

    if neutral_share >= 85 and len(colors) > 1:
        gaps.append("Deine Garderobe ist fast komplett neutral – ein Farbakzent bringt Abwechslung.")

    # --- Duplikate: gleiche Kategorie + gleiche Farbe ---
    dup_counter: Counter = Counter()
    for it in items:
        bucket = _bucket_color(it.get("color") or "")
        color_name = bucket[0] if bucket else "?"
        dup_counter[(it.get("category") or "?", color_name)] += int(it.get("quantity") or 1)
    duplicates = [
        {"category": cat, "color": col, "count": cnt}
        for (cat, col), cnt in dup_counter.most_common(5)
        if cnt >= 3
    ]

    # --- Zuwachs der letzten 30 Tage ---
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    recent = 0
    for it in items:
        created = it.get("created_at")
        if isinstance(created, datetime):
            c = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
            if c >= cutoff:
                recent += int(it.get("quantity") or 1)

    # --- Vollständigkeit der Metadaten ---
    tracked = ("material", "style", "season", "occasion", "brand")
    filled = sum(1 for it in items for f in tracked if it.get(f))
    completeness = round(filled / (total_entries * len(tracked)) * 100) if total_entries else 0

    return {
        "empty": False,
        "total_entries": total_entries,
        "total_pieces": total_pieces,
        "diversity": diversity,
        "combinations": combinations,
        "slots": _counter_to_list(slot_counter, total_pieces),
        "groups": _counter_to_list(group_counter, total_pieces),
        "categories": _counter_to_list(cat_counter, total_pieces)[:12],
        "colors": colors,
        "neutral_share": neutral_share,
        "materials": _counter_to_list(material_counter, total_pieces)[:8],
        "styles": _counter_to_list(style_counter, total_pieces),
        "occasions": _counter_to_list(occasion_counter, total_pieces),
        "seasons": [
            {
                "label": s,
                "count": seasonal[s],
                "share": round(seasonal[s] / total_pieces * 100) if total_pieces else 0,
            }
            for s in ("Frühling", "Sommer", "Herbst", "Winter")
        ],
        "brands": _counter_to_list(brand_counter, total_pieces)[:8],
        "duplicates": duplicates,
        "gaps": gaps,
        "recent_30d": recent,
        "completeness": completeness,
    }
