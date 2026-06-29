"""
Bloom Seasonal Demand Engine
Adds dynamic, context-aware demand on top of the static survey-based scores.

Two layers run together:
  1. Weather season  (rainy / harmattan)  -> based on month
  2. Academic period (resumption, mid-semester, exam, closing, normal) -> based on month

Seasonal products are boosted by a factor (default 2.5x) during their window,
then fall back to normal automatically. An admin override can force any period
for demonstration purposes.

Calendar mapping (Crawford University, as described by the student):
  September  -> Summer / resit          (low season)
  October    -> Resumption (1st sem)
  November   -> Normal lectures + mid-semester signals
  December   -> First CA test           (exam/test)
  January    -> Revision + lectures      (normal)
  Jan/Feb    -> First semester exams     (exam)
  February   -> Holiday break            (closing/vacation)
  March      -> Second semester begins   (resumption)
  April      -> CA                       (exam/test)
  May        -> Revision                 (exam approach)
  June       -> Revision + exam          (exam)
  July/Aug   -> Long vacation            (closing/vacation)
"""

from datetime import datetime, timezone
from typing import Dict, List, Any

# Boost factor applied to seasonal products in their active window
SEASONAL_BOOST = 2.5

# ── Weather season by month (Nigeria) ─────────────────────────────────────────
# Rainy season: April to October. Harmattan/dry: November to March.
def _weather_season(month: int) -> str:
    if 4 <= month <= 10:
        return "rainy"
    return "harmattan"

# ── Academic period by month (Crawford calendar) ──────────────────────────────
def _academic_period(month: int) -> str:
    mapping = {
        1:  "normal",       # January - revision + lectures
        2:  "exam",         # Jan/Feb first semester exams (Feb also break, exam takes priority for stocking)
        3:  "resumption",   # March - second semester begins
        4:  "exam",         # April - CA / test
        5:  "exam",         # May - revision toward exams
        6:  "exam",         # June - revision + exam
        7:  "closing",      # July - long vacation
        8:  "closing",      # August - long vacation
        9:  "summer",       # September - summer / resit (low season)
        10: "resumption",   # October - resumption first semester
        11: "midsemester",  # November - mid-semester, students' supplies finishing
        12: "exam",         # December - first CA test
    }
    return mapping.get(month, "normal")

# ── Seasonal product catalogues ───────────────────────────────────────────────
# Each entry: the products that spike during that trigger, with a short reason.
SEASONAL_PRODUCTS = {
    # Weather-driven
    "rainy": {
        "label": "Rainy Season",
        "products": ["Umbrella", "Raincoat", "Rubber slippers", "Rain boots"],
        "reason": "It is the rainy season, so students need rain protection items.",
    },
    "harmattan": {
        "label": "Harmattan / Dry Season",
        "products": ["Body cream", "Lip balm", "Body lotion", "Tissue", "Lozenges (cough drops)", "Vaseline"],
        "reason": "The dry harmattan weather raises demand for skincare and cold-relief items.",
    },
    # Academic-period-driven
    "resumption": {
        "label": "Resumption Period",
        "products": ["Padlock", "Door catcher (door lock)", "Bucket", "Bedsheet", "Hanger", "Broom", "Bowl / plate set", "Provisions"],
        "reason": "Students are resuming and setting up their rooms, so hostel essentials are in high demand.",
    },
    "midsemester": {
        "label": "Mid-Semester Period",
        "products": ["Bathing soap", "Perfume", "Deodorant", "Detergent", "Sanitary pads", "Toothpaste", "Body spray"],
        "reason": "By mid-semester, students' personal supplies are finishing, so toiletries spike.",
    },
    "exam": {
        "label": "Examination / Test Period",
        "products": ["Pens", "Foolscap sheets", "Energy drinks", "Glucose", "Printing / photocopy", "Highlighters", "Biros"],
        "reason": "During tests and exams, writing materials, printing, and energy boosters are in high demand.",
    },
    "closing": {
        "label": "Closing / Vacation Period",
        "products": ["Travelling bags (all sizes)", "Ghana-must-go bags", "Padlock", "Box locks", "Cartons"],
        "reason": "As the school prepares to close, students need travelling bags and packing items.",
    },
    "summer": {
        "label": "Summer / Resit Period",
        "products": ["Printing / photocopy", "Pens", "Provisions", "Bathing soap"],
        "reason": "A quieter period with mostly resit students on campus, so demand is modest.",
    },
    "normal": {
        "label": "Normal Lecture Period",
        "products": [],
        "reason": "A regular teaching period with no special seasonal spike.",
    },
}

# Valid override values the admin can set
VALID_PERIODS = ["auto", "resumption", "midsemester", "exam", "closing", "summer", "normal"]
VALID_SEASONS = ["auto", "rainy", "harmattan"]


def get_active_context(now: datetime = None,
                       period_override: str = "auto",
                       season_override: str = "auto") -> Dict[str, Any]:
    """
    Work out the current season and academic period.
    Admin overrides take priority over the automatic date-based detection.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    month = now.month

    # Determine season
    if season_override and season_override != "auto" and season_override in SEASONAL_PRODUCTS:
        season = season_override
    else:
        season = _weather_season(month)

    # Determine academic period
    if period_override and period_override != "auto" and period_override in SEASONAL_PRODUCTS:
        period = period_override
    else:
        period = _academic_period(month)

    return {
        "month": month,
        "monthName": now.strftime("%B"),
        "season": season,
        "seasonLabel": SEASONAL_PRODUCTS[season]["label"],
        "period": period,
        "periodLabel": SEASONAL_PRODUCTS[period]["label"],
        "isAutoSeason": season_override in (None, "", "auto"),
        "isAutoPeriod": period_override in (None, "", "auto"),
    }


def get_seasonal_products(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build the combined list of boosted seasonal products from both the
    active weather season and the active academic period.
    """
    season = context["season"]
    period = context["period"]

    items = []
    seen = set()

    for trigger in (season, period):
        info = SEASONAL_PRODUCTS.get(trigger, {})
        for product in info.get("products", []):
            key = product.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "product":   product,
                "boost":     SEASONAL_BOOST,
                "trigger":   info["label"],
                "reason":    info["reason"],
                # synthetic demand score so seasonal items can rank against normal ones
                "demandScore": round(min(10.0, 4.0 * SEASONAL_BOOST), 2),
            })
    return items


def build_seasonal_banner(context: Dict[str, Any], seasonal_products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a short banner the frontend can display, summarising what is in
    season right now and which products to push.
    """
    if not seasonal_products:
        headline = f"{context['monthName']}: {context['periodLabel']}"
        message = "No strong seasonal demand right now. Stick to your usual top sellers."
        return {"active": False, "headline": headline, "message": message, "products": []}

    top_names = [p["product"] for p in seasonal_products[:6]]
    reasons = []
    # Collect the distinct reasons (season + period)
    season_info = SEASONAL_PRODUCTS.get(context["season"], {})
    period_info = SEASONAL_PRODUCTS.get(context["period"], {})
    if season_info.get("products"):
        reasons.append(season_info["reason"])
    if period_info.get("products"):
        reasons.append(period_info["reason"])

    headline = f"In season now: {context['seasonLabel']} + {context['periodLabel']}"
    message = " ".join(reasons) + " Consider stocking: " + ", ".join(top_names) + "."

    return {
        "active": True,
        "headline": headline,
        "message": message,
        "products": top_names,
        "season": context["seasonLabel"],
        "period": context["periodLabel"],
    }


def apply_seasonal_boost(products: List[Dict[str, Any]],
                         seasonal_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply the seasonal boost to any of the vendor's existing products that
    match a seasonal item, and add new seasonal items they don't yet stock.
    Returns a re-sorted list with seasonal items lifted toward the top.
    """
    seasonal_lookup = {s["product"].lower(): s for s in seasonal_products}

    # Boost existing products that match
    boosted = []
    matched_keys = set()
    for prod in products:
        name_key = prod["name"].lower()
        match = None
        for skey, sval in seasonal_lookup.items():
            if skey in name_key or name_key in skey:
                match = sval
                break
        if match:
            new_score = round(min(10.0, prod["demandScore"] * SEASONAL_BOOST), 2)
            boosted.append({
                **prod,
                "demandScore": new_score,
                "seasonal": True,
                "seasonalReason": match["reason"],
            })
            matched_keys.add(match["product"].lower())
        else:
            boosted.append({**prod, "seasonal": False})

    # Re-sort so seasonal items rise to the top
    boosted.sort(key=lambda x: (-(1 if x.get("seasonal") else 0), -x["demandScore"]))
    return boosted