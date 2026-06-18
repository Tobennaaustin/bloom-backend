"""
Bloom Recommendation Engine
Translates store type + product list into personalised inventory intelligence
powered by the Crawford University analysis outputs.
"""

from typing import List, Dict, Any

# ── Campus demand data (from analysis engine outputs) ─────────────────────────
CAMPUS_DEMAND = {
    "pure water (sachet)":        {"demand_score": 8.3, "purchase_rate_pct": 83.0, "weekly_units_base": 180},
    "soft drinks":                {"demand_score": 6.3, "purchase_rate_pct": 62.6, "weekly_units_base": 100},
    "rice / cooked food":         {"demand_score": 7.4, "purchase_rate_pct": 73.8, "weekly_units_base": 210},
    "bread":                      {"demand_score": 6.1, "purchase_rate_pct": 50.8, "weekly_units_base": 90},
    "biscuits / snacks":          {"demand_score": 5.3, "purchase_rate_pct": 52.7, "weekly_units_base": 70},
    "instant noodles (indomie)":  {"demand_score": 4.9, "purchase_rate_pct": 40.9, "weekly_units_base": 55},
    "printing / photocopy":       {"demand_score": 4.5, "purchase_rate_pct": 43.4, "weekly_units_base": 30},
    "airtime / data top-up":      {"demand_score": 4.0, "purchase_rate_pct": 34.0, "weekly_units_base": 60},
    "tea / milo / beverages":     {"demand_score": 3.4, "purchase_rate_pct": 28.6, "weekly_units_base": 25},
    "pens / pencils":             {"demand_score": 3.5, "purchase_rate_pct": 28.2, "weekly_units_base": 20},
    "provisions":                 {"demand_score": 3.0, "purchase_rate_pct": 22.6, "weekly_units_base": 18},
    "exercise books / notebooks": {"demand_score": 2.9, "purchase_rate_pct": 22.2, "weekly_units_base": 15},
    "toiletries":                 {"demand_score": 2.8, "purchase_rate_pct": 18.7, "weekly_units_base": 12},
    "phone accessories":          {"demand_score": 2.8, "purchase_rate_pct": 18.1, "weekly_units_base": 10},
    "energy drinks":              {"demand_score": 1.9, "purchase_rate_pct": 13.1, "weekly_units_base": 30},
    "medications":                {"demand_score": 1.5, "purchase_rate_pct": 8.8,  "weekly_units_base": 8},
    "gala / sausage roll":        {"demand_score": 5.3, "purchase_rate_pct": 52.0, "weekly_units_base": 80},
}

# ── Store-type profiles ────────────────────────────────────────────────────────
STORE_PROFILES = {
    "provision": {
        "must_stock":   ["pure water (sachet)", "soft drinks", "bread", "gala / sausage roll", "biscuits / snacks"],
        "add_these":    ["energy drinks", "phone accessories", "airtime / data top-up", "provisions"],
        "slow_movers":  ["tea / milo / beverages", "provisions"],
        "insight":      "Pure water is the single highest-demand item on campus (83% of students). "
                        "Cold drinks are the #1 item students cannot find. Energy drinks are an emerging "
                        "demand — add Predator or Power Horse to capture this segment.",
        "restock_lead": 2,
        "market_share": 0.18,
    },
    "food": {
        "must_stock":   ["rice / cooked food", "bread", "instant noodles (indomie)", "soft drinks", "pure water (sachet)"],
        "add_these":    ["swallow (eba/fufu)", "moi moi", "yam and egg", "pepper soup"],
        "slow_movers":  [],
        "insight":      "Food vendors face the highest stockout risk on campus. 65% of students buy "
                        "cooked food at least once a day. Swallow and moi moi are the most requested "
                        "additions. Ensure cold drinks are always available alongside food.",
        "restock_lead": 1,
        "market_share": 0.20,
    },
    "drinks": {
        "must_stock":   ["pure water (sachet)", "soft drinks", "energy drinks", "gala / sausage roll", "bread"],
        "add_these":    ["hollandia yoghurt / nutri milk", "bottled groundnut", "sugar sachets"],
        "slow_movers":  ["biscuits / snacks"],
        "insight":      "Pure water is your core product — never let stock fall below 50 bags. "
                        "Cold drinks are the #1 unavailable item reported by students. "
                        "Energy drinks are undersupplied on campus — strong growth opportunity.",
        "restock_lead": 2,
        "market_share": 0.18,
    },
    "stationery": {
        "must_stock":   ["pens / pencils", "exercise books / notebooks", "printing / photocopy", "airtime / data top-up"],
        "add_these":    ["stapler pins", "printing paper / A4", "cardboard / cardstock", "highlighters"],
        "slow_movers":  [],
        "insight":      "Printing and photocopy services have the highest stationery demand on campus. "
                        "Stapler pins are the most frequently requested item students cannot find. "
                        "Stock more at the start of each semester when demand surges.",
        "restock_lead": 5,
        "market_share": 0.15,
    },
    "toiletries": {
        "must_stock":   ["toiletries", "medications"],
        "add_these":    ["dettol hand sanitiser", "sanitary pads", "cotton wool", "pain relief tablets"],
        "slow_movers":  [],
        "insight":      "Toiletries and medications are undersupplied relative to demand. "
                        "Dettol hand sanitiser is a frequently requested item vendors don't stock. "
                        "First aid items like paracetamol have consistent low-volume but reliable demand.",
        "restock_lead": 7,
        "market_share": 0.12,
    },
    "mixed": {
        "must_stock":   ["pure water (sachet)", "soft drinks", "bread", "biscuits / snacks", "pens / pencils"],
        "add_these":    ["energy drinks", "phone accessories", "airtime / data top-up", "gala / sausage roll"],
        "slow_movers":  ["tea / milo / beverages"],
        "insight":      "As a mixed store, focus your capital on the 5 highest-demand items first. "
                        "Pure water and soft drinks drive the most footfall. "
                        "Phone accessories and airtime are high-frequency repeat purchases.",
        "restock_lead": 2,
        "market_share": 0.16,
    },
}

STUDENT_POP = 465  # survey respondents used as proxy for active campus buyers


def _normalise(name: str) -> str:
    return name.lower().strip()


def _match_demand(product_name: str) -> Dict[str, Any]:
    """Fuzzy-match a product name to the campus demand database."""
    name = _normalise(product_name)
    # Exact match
    if name in CAMPUS_DEMAND:
        return CAMPUS_DEMAND[name]
    # Partial match
    for key, data in CAMPUS_DEMAND.items():
        keywords = key.split(" / ")[0].split()[:2]
        if all(kw in name for kw in keywords):
            return data
        if any(kw in name for kw in keywords) and len(keywords) == 1:
            return data
    return {"demand_score": 2.0, "purchase_rate_pct": 10.0, "weekly_units_base": 10}


def _restock_point(weekly_units: int, lead_time: int) -> int:
    daily = weekly_units / 6
    return max(5, round(daily * lead_time * 1.5))


def _urgency(current: int, rp: int) -> str:
    ratio = current / rp if rp > 0 else 1
    if ratio < 0.8:   return "critical"
    if ratio < 1.0:   return "warning"
    return "ok"


def generate_report(store_type: str, products: List[str], restock_time: str) -> Dict[str, Any]:
    """
    Core recommendation function.
    Returns the full dashboard payload for a vendor.
    """
    profile = STORE_PROFILES.get(store_type, STORE_PROFILES["mixed"])
    lead    = profile["restock_lead"]
    share   = profile["market_share"]

    # ── Top products ──────────────────────────────────────────────────────────
    top_products = []
    vendor_products_lower = [_normalise(p) for p in products]

    # Score each of their products
    for prod in products:
        demand_data = _match_demand(prod)
        weekly = max(5, round(demand_data["weekly_units_base"] * share * 1.2))
        rp = _restock_point(weekly, lead)
        score = demand_data["demand_score"]
        top_products.append({
            "name":         prod,
            "weeklyUnits":  weekly,
            "restockEvery": f"Every {lead} day{'s' if lead > 1 else ''}",
            "demandScore":  round(score, 1),
            "restockPoint": rp,
            "status":       "high" if score >= 6 else "medium" if score >= 4 else "low",
        })

    top_products.sort(key=lambda x: -x["demandScore"])

    # ── Restock alerts ────────────────────────────────────────────────────────
    restock_alerts = []
    for p in top_products:
        rp = p["restockPoint"]
        # Simulate current stock as a fraction of restock point for demo
        current = round(rp * 0.75) if p["status"] == "high" else round(rp * 1.3)
        urgency = _urgency(current, rp)
        if urgency != "ok" or p["demandScore"] >= 6:
            restock_alerts.append({
                "product":     p["name"],
                "currentStock": current,
                "restockPoint": rp,
                "urgency":     urgency,
                "restockEvery": p["restockEvery"],
            })

    restock_alerts.sort(key=lambda x: {"critical": 0, "warning": 1, "ok": 2}[x["urgency"]])

    # ── Recommendations ───────────────────────────────────────────────────────
    recommendations = []

    # Add these (items profile says to stock that vendor doesn't have)
    for item in profile["add_these"]:
        if not any(_normalise(item) in _normalise(vp) or _normalise(vp) in _normalise(item)
                   for vp in vendor_products_lower):
            demand = _match_demand(item)
            recommendations.append({
                "type":    "add",
                "product": item.title(),
                "reason":  f"Students demand this but most vendors don't stock it. "
                           f"Campus demand score: {demand['demand_score']}/10.",
                "weeklyUnits": round(demand["weekly_units_base"] * share * 1.2),
            })

    # Reduce these (slow movers in their current stock)
    for item in profile["slow_movers"]:
        if any(_normalise(item) in _normalise(vp) for vp in vendor_products_lower):
            recommendations.append({
                "type":    "reduce",
                "product": item.title(),
                "reason":  "Vendor survey data shows this is a slow mover on Crawford campus. "
                           "Reduce quantity by 30–40% to free up capital.",
            })

    # Maintain high performers
    for p in top_products[:2]:
        recommendations.append({
            "type":    "maintain",
            "product": p["name"],
            "reason":  f"Consistent high demand ({p['demandScore']}/10). "
                       f"Stock {p['weeklyUnits']} units weekly.",
        })

    # ── Gap analysis ──────────────────────────────────────────────────────────
    gap_analysis = [
        {"category": "Water",           "demandScore": 8.3, "supplyScore": 7.2,  "gapScore": 1.1,  "recommendation": "ADD / INCREASE STOCK"},
        {"category": "Soft drinks",     "demandScore": 6.3, "supplyScore": 4.1,  "gapScore": 2.2,  "recommendation": "ADD / INCREASE STOCK"},
        {"category": "Cooked food",     "demandScore": 7.4, "supplyScore": 6.8,  "gapScore": 0.6,  "recommendation": "ADD / INCREASE STOCK"},
        {"category": "Stationery",      "demandScore": 3.5, "supplyScore": 2.1,  "gapScore": 1.4,  "recommendation": "ADD / INCREASE STOCK"},
        {"category": "Biscuits/snacks", "demandScore": 5.3, "supplyScore": 5.8,  "gapScore": -0.5, "recommendation": "MAINTAIN"},
        {"category": "Beverages",       "demandScore": 3.4, "supplyScore": 4.9,  "gapScore": -1.5, "recommendation": "REDUCE STOCK"},
        {"category": "Toiletries",      "demandScore": 2.8, "supplyScore": 1.1,  "gapScore": 1.7,  "recommendation": "ADD / INCREASE STOCK"},
    ]

    # ── Overall demand score ──────────────────────────────────────────────────
    if top_products:
        avg_score = round(sum(p["demandScore"] for p in top_products) / len(top_products), 1)
    else:
        avg_score = 5.0

    return {
        "storeType":             store_type,
        "demandScore":           avg_score,
        "weeklyRevenuePotential": _revenue_estimate(store_type),
        "insight":               profile["insight"],
        "topProducts":           top_products,
        "restockAlerts":         restock_alerts[:5],
        "recommendations":       recommendations[:8],
        "addThese":              [r["product"] for r in recommendations if r["type"] == "add"][:5],
        "reduce":                [r["product"] for r in recommendations if r["type"] == "reduce"][:3],
        "gapAnalysis":           gap_analysis,
    }


def _revenue_estimate(store_type: str) -> str:
    mapping = {
        "provision": "₦35,000 – ₦65,000",
        "food":      "₦42,000 – ₦84,000",
        "drinks":    "₦28,000 – ₦52,000",
        "stationery":"₦18,000 – ₦35,000",
        "toiletries":"₦15,000 – ₦28,000",
        "mixed":     "₦40,000 – ₦75,000",
    }
    return mapping.get(store_type, "₦25,000 – ₦50,000")
