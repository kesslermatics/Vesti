"""Statistiken fuer die Uhren- und Duftsammlung.

Bewusst getrennt von analytics.py: dort werden Outfit-Kombinationen aus
Oberteil x Unterteil x Schuhe gerechnet, was fuer Uhren und Duefte keinen Sinn
ergibt. Alles hier laeuft rein rechnerisch, damit der Analyse-Tab sofort laedt.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from .fragrances import FRAGRANCE_SEASONS, shelf_life_months
from .watches import wrist_size_advice

# Ab diesem Fuellstand gilt ein Flakon als knapp
LOW_STOCK_PERCENT = 15
# Standard-Serviceintervall fuer mechanische Uhren in Jahren
DEFAULT_SERVICE_INTERVAL = 5
# Serviceintervall greift nur bei mechanischen Werken
MECHANICAL_MOVEMENTS = {"Automatik", "Handaufzug", "Spring Drive"}


def _counter_to_list(counter: Counter, total: int) -> list[dict[str, Any]]:
    return [
        {
            "label": label,
            "count": count,
            "share": round(count / total * 100) if total else 0,
        }
        for label, count in counter.most_common()
    ]


def _as_utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# ══════════════════════════════════════════════════════════════════════
#  Uhren
# ══════════════════════════════════════════════════════════════════════

def service_due_date(watch: dict[str, Any]) -> datetime | None:
    """Wann der naechste Service faellig ist, falls berechenbar.

    Basis ist der letzte Service, sonst das Kaufdatum. Quarzuhren brauchen kein
    Revisionsintervall, deshalb wird dort nichts berechnet.
    """
    movement = watch.get("movement") or ""
    if movement and movement not in MECHANICAL_MOVEMENTS:
        return None

    start = _as_utc(watch.get("serviced_at")) or _as_utc(watch.get("purchase_date"))
    if not start:
        return None

    years = watch.get("service_interval_years") or DEFAULT_SERVICE_INTERVAL
    try:
        years = max(1, int(years))
    except (ValueError, TypeError):
        years = DEFAULT_SERVICE_INTERVAL

    # 365,25 Tage pro Jahr genuegt fuer eine Faelligkeitsanzeige
    return start + timedelta(days=round(365.25 * years))


def compute_watch_stats(
    watches: list[dict[str, Any]],
    wrist_cm: float | None = None,
) -> dict[str, Any]:
    """Kennzahlen der Uhrensammlung."""
    total = len(watches)
    if total == 0:
        return {"empty": True, "total": 0}

    style_counter: Counter = Counter()
    brand_counter: Counter = Counter()
    movement_counter: Counter = Counter()
    case_counter: Counter = Counter()
    band_counter: Counter = Counter()
    dial_counter: Counter = Counter()
    occasion_counter: Counter = Counter()
    complication_counter: Counter = Counter()

    diameters: list[float] = []
    total_purchase = 0.0
    total_value = 0.0
    has_purchase_prices = False
    has_values = False

    now = datetime.now(timezone.utc)
    service_soon: list[dict[str, Any]] = []
    warranty_active: list[dict[str, Any]] = []
    needs_review = 0

    for w in watches:
        if w.get("style"):
            style_counter[w["style"]] += 1
        if w.get("brand"):
            brand_counter[w["brand"]] += 1
        if w.get("movement"):
            movement_counter[w["movement"]] += 1
        if w.get("case_material"):
            case_counter[w["case_material"]] += 1
        if w.get("band_material"):
            band_counter[w["band_material"]] += 1
        if w.get("dial_color"):
            dial_counter[w["dial_color"]] += 1
        for occ in w.get("occasions") or []:
            occasion_counter[occ] += 1
        for comp in w.get("complications") or []:
            complication_counter[comp] += 1

        if w.get("case_diameter"):
            try:
                diameters.append(float(w["case_diameter"]))
            except (ValueError, TypeError):
                pass

        if w.get("purchase_price"):
            try:
                total_purchase += float(w["purchase_price"])
                has_purchase_prices = True
            except (ValueError, TypeError):
                pass

        # Fuer den Sammlungswert zaehlt der aktuelle Wert, sonst der Kaufpreis
        value = w.get("current_value") or w.get("purchase_price")
        if value:
            try:
                total_value += float(value)
                has_values = True
            except (ValueError, TypeError):
                pass

        due = service_due_date(w)
        if due:
            days_left = (due - now).days
            # Faellig oder innerhalb der naechsten sechs Monate
            if days_left <= 183:
                service_soon.append(
                    {
                        "id": w.get("id"),
                        "name": w.get("name") or w.get("brand") or "Uhr",
                        "due_date": due,
                        "overdue": days_left < 0,
                        "days_left": days_left,
                    }
                )

        warranty = _as_utc(w.get("warranty_until"))
        if warranty and warranty > now:
            warranty_active.append(
                {
                    "id": w.get("id"),
                    "name": w.get("name") or w.get("brand") or "Uhr",
                    "until": warranty,
                }
            )

        if w.get("needs_review"):
            needs_review += 1

    avg_diameter = round(sum(diameters) / len(diameters), 1) if diameters else None

    # --- Luecken erkennen ---
    gaps: list[str] = []
    styles_present = set(style_counter)
    dressy = {"Dress / Elegant", "Business"}
    sporty = {"Sport", "Taucheruhr", "Rennsport", "Feld / Military"}

    if total >= 2 and not styles_present & dressy:
        gaps.append(
            "Für formelle Termine fehlt eine flache, elegante Uhr – "
            "alles in der Sammlung ist eher sportlich."
        )
    if total >= 2 and not styles_present & sporty:
        gaps.append(
            "Eine robuste Uhr für Sport, Urlaub oder Wasser fehlt noch."
        )
    if total >= 3 and len(styles_present) == 1:
        only = next(iter(styles_present))
        gaps.append(
            f"Alle Uhren fallen in denselben Stil ({only}) – "
            "eine andere Richtung würde die Sammlung deutlich vielseitiger machen."
        )
    if total >= 3 and len(brand_counter) == 1:
        gaps.append(
            f"Alle Uhren stammen von {next(iter(brand_counter))}. "
            "Kein Problem, aber eine zweite Handschrift bringt Abwechslung."
        )
    if total >= 2 and not band_counter.get("Kalbsleder") and not any(
        "leder" in b.lower() for b in band_counter
    ):
        gaps.append(
            "Kein Lederband in der Sammlung – ein Wechselband aus Leder verändert "
            "den Charakter einer Uhr sofort und kostet wenig."
        )

    diving = sum(1 for w in watches if (w.get("water_resistance") or 0) >= 100)
    if total >= 2 and diving == 0:
        gaps.append(
            "Keine Uhr ist mit 100 m oder mehr angegeben – für Schwimmen und "
            "Wassersport fehlt damit eine unbesorgt tragbare Option."
        )

    service_soon.sort(key=lambda s: s["days_left"])

    return {
        "empty": False,
        "total": total,
        "styles": _counter_to_list(style_counter, total),
        "brands": _counter_to_list(brand_counter, total),
        "movements": _counter_to_list(movement_counter, total),
        "case_materials": _counter_to_list(case_counter, total),
        "band_materials": _counter_to_list(band_counter, total),
        "dial_colors": _counter_to_list(dial_counter, total),
        "occasions": _counter_to_list(occasion_counter, total),
        "complications": _counter_to_list(complication_counter, total)[:10],
        "diversity": {
            "styles": len(style_counter),
            "brands": len(brand_counter),
            "movements": len(movement_counter),
            "case_materials": len(case_counter),
        },
        "avg_diameter": avg_diameter,
        "smallest_diameter": min(diameters) if diameters else None,
        "largest_diameter": max(diameters) if diameters else None,
        "wrist_advice": wrist_size_advice(wrist_cm, avg_diameter),
        "total_purchase": round(total_purchase, 2) if has_purchase_prices else None,
        "total_value": round(total_value, 2) if has_values else None,
        "value_change": (
            round(total_value - total_purchase, 2)
            if has_values and has_purchase_prices
            else None
        ),
        "service_soon": service_soon,
        "warranty_active": warranty_active,
        "needs_review": needs_review,
        "gaps": gaps,
    }


# ══════════════════════════════════════════════════════════════════════
#  Duefte
# ══════════════════════════════════════════════════════════════════════

def expiry_date(fragrance: dict[str, Any]) -> datetime | None:
    """Wann der Duft nach dem Oeffnen voraussichtlich gekippt ist."""
    opened = _as_utc(fragrance.get("opened_at"))
    if not opened:
        return None
    months = shelf_life_months(fragrance.get("family") or "")
    return opened + timedelta(days=round(30.44 * months))


def compute_fragrance_stats(fragrances: list[dict[str, Any]]) -> dict[str, Any]:
    """Kennzahlen der Duftsammlung."""
    total = len(fragrances)
    if total == 0:
        return {"empty": True, "total": 0}

    family_counter: Counter = Counter()
    note_counter: Counter = Counter()
    base_note_counter: Counter = Counter()
    concentration_counter: Counter = Counter()
    brand_counter: Counter = Counter()
    occasion_counter: Counter = Counter()
    time_counter: Counter = Counter()
    audience_counter: Counter = Counter()
    season_counter: Counter = Counter()

    total_ml = 0
    total_spend = 0.0
    has_spend = False
    now = datetime.now(timezone.utc)

    low_stock: list[dict[str, Any]] = []
    expiring: list[dict[str, Any]] = []
    needs_review = 0

    for f in fragrances:
        qty = max(1, int(f.get("quantity") or 1))

        # Bewusst NICHT nach Stueckzahl gewichtet: zwei Flakons desselben Dufts
        # erweitern das Duftprofil nicht und wuerden die Anteile ueber 100 %
        # treiben, weil `total` die Anzahl der Duefte ist. Die Stueckzahl zaehlt
        # nur beim Bestand (Flakons, Volumen).
        if f.get("family"):
            family_counter[f["family"]] += 1
        if f.get("secondary_family"):
            family_counter[f["secondary_family"]] += 1
        if f.get("concentration"):
            concentration_counter[f["concentration"]] += 1
        if f.get("brand"):
            brand_counter[f["brand"]] += 1
        if f.get("time_of_day"):
            time_counter[f["time_of_day"]] += 1
        if f.get("audience"):
            audience_counter[f["audience"]] += 1

        for key in ("top_notes", "heart_notes", "base_notes"):
            for note in f.get(key) or []:
                note_counter[note] += 1
        for note in f.get("base_notes") or []:
            base_note_counter[note] += 1

        for occ in f.get("occasions") or []:
            occasion_counter[occ] += 1
        for season in f.get("seasons") or []:
            season_counter[season] += 1

        if f.get("bottle_size"):
            try:
                total_ml += int(f["bottle_size"]) * qty
            except (ValueError, TypeError):
                pass

        if f.get("purchase_price"):
            try:
                total_spend += float(f["purchase_price"])
                has_spend = True
            except (ValueError, TypeError):
                pass

        fill = f.get("fill_level")
        if fill is not None:
            try:
                fill_int = int(fill)
                if fill_int <= LOW_STOCK_PERCENT:
                    low_stock.append(
                        {
                            "id": f.get("id"),
                            "name": f.get("name") or "Duft",
                            "brand": f.get("brand") or "",
                            "fill_level": fill_int,
                        }
                    )
            except (ValueError, TypeError):
                pass

        expires = expiry_date(f)
        if expires:
            days_left = (expires - now).days
            # Abgelaufen oder innerhalb der naechsten sechs Monate
            if days_left <= 183:
                expiring.append(
                    {
                        "id": f.get("id"),
                        "name": f.get("name") or "Duft",
                        "brand": f.get("brand") or "",
                        "expires_at": expires,
                        "expired": days_left < 0,
                        "days_left": days_left,
                    }
                )

        if f.get("needs_review"):
            needs_review += 1

    # --- Saison-Abdeckung: "ganzjährig" zaehlt fuer alle vier ---
    seasonal = {s: 0 for s in ("Frühling", "Sommer", "Herbst", "Winter")}
    for label, count in season_counter.items():
        if label == "ganzjährig":
            for s in seasonal:
                seasonal[s] += count
        elif label in seasonal:
            seasonal[label] += count

    # --- Luecken und Dopplungen ---
    gaps: list[str] = []

    fresh_families = {"Frisch / Zitrisch", "Aquatisch / Marin", "Grün"}
    warm_families = {
        "Orientalisch / Amber",
        "Gourmand",
        "Holzig",
        "Tabak",
        "Ledrig",
        "Räucherig / Weihrauch",
    }
    present_families = set(family_counter)

    if total >= 2 and not present_families & fresh_families:
        gaps.append(
            "Nichts Frisches oder Zitrisches in der Sammlung – für warme Tage fehlt "
            "damit eine leichte Option."
        )
    if total >= 2 and not present_families & warm_families:
        gaps.append(
            "Keine wärmende Basis wie Holz, Amber oder Tabak – im Winter wirken "
            "frische Düfte schnell dünn."
        )

    weakest = min(seasonal, key=lambda s: seasonal[s]) if any(seasonal.values()) else None
    if weakest and seasonal[weakest] == 0:
        gaps.append(f"Für {weakest} ist bisher kein Duft hinterlegt.")

    if total >= 2 and not occasion_counter.get("Büro") and not occasion_counter.get("Business"):
        gaps.append(
            "Kein Duft ist fürs Büro markiert – dort ist ein zurückhaltender, "
            "dezent projizierender Duft die sichere Wahl."
        )

    # Dopplungen: gleiche Familie mit ueberlappenden Basisnoten
    duplicates: list[dict[str, Any]] = []
    for family, count in family_counter.items():
        if count < 2:
            continue
        members = [
            f
            for f in fragrances
            if family in {f.get("family"), f.get("secondary_family")}
        ]
        if len(members) < 2:
            continue
        shared: Counter = Counter()
        for f in members:
            for note in set(f.get("base_notes") or []):
                shared[note] += 1
        overlap = [note for note, c in shared.items() if c >= 2]
        if overlap:
            duplicates.append(
                {
                    "family": family,
                    "count": len(members),
                    "shared_notes": overlap[:4],
                    "names": [f.get("name") or "Duft" for f in members][:4],
                }
            )

    if duplicates:
        worst = max(duplicates, key=lambda d: d["count"])
        gaps.append(
            f"{worst['count']} Düfte in der Familie {worst['family']} teilen sich "
            f"{', '.join(worst['shared_notes'])} in der Basis – für Außenstehende "
            "riechen die sehr ähnlich."
        )

    low_stock.sort(key=lambda entry: entry["fill_level"])
    expiring.sort(key=lambda entry: entry["days_left"])

    top_notes_list = _counter_to_list(note_counter, total)

    return {
        "empty": False,
        "total": total,
        "total_bottles": sum(max(1, int(f.get("quantity") or 1)) for f in fragrances),
        "families": _counter_to_list(family_counter, total),
        "notes": top_notes_list[:15],
        "base_notes": _counter_to_list(base_note_counter, total)[:10],
        "concentrations": _counter_to_list(concentration_counter, total),
        "brands": _counter_to_list(brand_counter, total),
        "occasions": _counter_to_list(occasion_counter, total),
        "times": _counter_to_list(time_counter, total),
        "audiences": _counter_to_list(audience_counter, total),
        "seasons": [
            {
                "label": s,
                "count": seasonal[s],
                "share": round(seasonal[s] / total * 100) if total else 0,
            }
            for s in ("Frühling", "Sommer", "Herbst", "Winter")
        ],
        "diversity": {
            "families": len(family_counter),
            "notes": len(note_counter),
            "brands": len(brand_counter),
        },
        "total_ml": total_ml or None,
        "total_spend": round(total_spend, 2) if has_spend else None,
        "low_stock": low_stock,
        "expiring": expiring,
        "duplicates": duplicates[:5],
        "needs_review": needs_review,
        "gaps": gaps,
        "all_seasons": FRAGRANCE_SEASONS,
    }
