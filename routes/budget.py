"""
Bloom Budget Planner API
Vendor supplies their own unit prices.
System uses analysis engine demand data to prioritise allocation.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import get_collection
from services.recommendation_engine import STORE_PROFILES, _match_demand
from bson import ObjectId
from datetime import datetime, timezone

budget_bp = Blueprint("budget", __name__, url_prefix="/api/budget")


def _get_vendor(vendor_id: str):
    vendors = get_collection("vendors")
    if vendors is None:
        return {
            "_id": vendor_id,
            "storeType": "provision",
            "products": ["Pure water", "Soft drinks", "Bread"],
            "restockTime": "2-3days",
        }
    try:
        return vendors.find_one({"_id": ObjectId(vendor_id)})
    except Exception:
        return None


@budget_bp.route("/plan", methods=["POST"])
@jwt_required()
def create_budget_plan():
    """
    Budget planner — vendor provides their own unit prices.

    Request body:
    {
        "budget": 15000,
        "items": [
            { "name": "Carton of Indomie", "unitPrice": 4500, "quantity": 2 },
            { "name": "Bags of pure water", "unitPrice": 200,  "quantity": 10 },
            { "name": "Packs of bottle water", "unitPrice": 150, "quantity": 20 },
            { "name": "Breads", "unitPrice": 800, "quantity": 5 }
        ]
    }

    Each item requires: name (str), unitPrice (number), quantity (int >= 1)
    """
    vendor_id = get_jwt_identity()
    vendor    = _get_vendor(vendor_id)
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    budget = data.get("budget")
    items  = data.get("items", [])

    if not budget or float(budget) <= 0:
        return jsonify({"error": "Please provide a valid budget amount"}), 400
    if not items:
        return jsonify({"error": "Please add at least one item"}), 400
    if len(items) > 30:
        return jsonify({"error": "Maximum 30 items per plan"}), 400

    # ── Validate each item has required fields ────────────────────────────────
    for i, item in enumerate(items):
        if not item.get("name", "").strip():
            return jsonify({"error": f"Item {i+1} is missing a name"}), 400
        if not isinstance(item.get("unitPrice"), (int, float)) or item["unitPrice"] <= 0:
            return jsonify({"error": f"'{item.get('name', f'Item {i+1}')}' needs a valid unit price"}), 400
        if not isinstance(item.get("quantity"), int) or item["quantity"] < 1:
            return jsonify({"error": f"'{item.get('name')}' needs a quantity of at least 1"}), 400

    budget     = float(budget)
    store_type = vendor.get("storeType", "mixed")
    profile    = STORE_PROFILES.get(store_type, STORE_PROFILES["mixed"])

    # ── Step 1: Enrich each item with demand data ─────────────────────────────
    enriched = []
    for item in items:
        name       = item["name"].strip()
        unit_price = float(item["unitPrice"])
        quantity   = int(item["quantity"])
        total_cost = unit_price * quantity

        # Get campus demand data
        dem = _match_demand(name)

        # Is this a must-stock item for their store type?
        is_must_stock = any(
            ms.lower() in name.lower() or name.lower() in ms.lower()
            for ms in profile["must_stock"]
        )

        # Priority score: demand (60%) + must-stock urgency (40%)
        urgency_bonus = 2.0 if is_must_stock else 0.0
        priority_score = round(dem["demand_score"] * 0.6 + urgency_bonus * 0.4, 2)

        enriched.append({
            "name":            name,
            "unitPrice":       unit_price,
            "quantity":        quantity,
            "totalCost":       round(total_cost, 2),
            "demandScore":     dem["demand_score"],
            "purchaseRatePct": dem["purchase_rate_pct"],
            "priorityScore":   priority_score,
            "isMustStock":     is_must_stock,
        })

    # ── Step 2: Sort by priority score (highest first) ────────────────────────
    enriched.sort(key=lambda x: (-x["priorityScore"], -x["demandScore"]))

    # ── Step 3: Greedy budget allocation ──────────────────────────────────────
    remaining  = budget
    buy_now    = []
    defer      = []
    total_spent = 0.0

    for item in enriched:
        full_cost = item["totalCost"]

        if full_cost <= remaining:
            # Can afford the full requested quantity
            remaining   -= full_cost
            total_spent += full_cost
            buy_now.append({
                **item,
                "buyQty":   item["quantity"],
                "subtotal": round(full_cost, 2),
                "decision": "buy",
                "buyFull":  True,
            })

        else:
            # Can we afford at least 1 unit?
            if item["unitPrice"] <= remaining:
                affordable_qty = int(remaining // item["unitPrice"])
                subtotal       = round(affordable_qty * item["unitPrice"], 2)
                remaining      -= subtotal
                total_spent    += subtotal
                buy_now.append({
                    **item,
                    "buyQty":   affordable_qty,
                    "subtotal": subtotal,
                    "shortfall": item["quantity"] - affordable_qty,
                    "decision": "partial",
                    "buyFull":  False,
                })
            else:
                # Cannot afford even 1 unit
                defer.append({**item, "decision": "defer"})

    # ── Step 4: Suggestions for deferred items ────────────────────────────────
    suggestions = []
    for d in defer:
        if d["demandScore"] >= 6.0:
            urgency = "high"
            reason  = (
                f"High campus demand ({d['demandScore']}/10 — {d['purchaseRatePct']}% of students buy this). "
                f"Save ₦{d['totalCost']:,.0f} and prioritise this in your next restock."
            )
        elif d["demandScore"] >= 4.0:
            urgency = "medium"
            reason  = (
                f"Moderate demand ({d['demandScore']}/10). "
                f"Can wait 1–2 cycles, but don't skip more than that."
            )
        else:
            urgency = "low"
            reason  = (
                f"Low campus demand ({d['demandScore']}/10). "
                f"Consider whether you truly need this item or if the capital is better spent elsewhere."
            )
        suggestions.append({
            "product": d["name"],
            "reason":  reason,
            "urgency": urgency,
            "cost":    d["totalCost"],
        })

    defer_cost_total = round(sum(d["totalCost"] for d in defer), 2)
    amount_to_save   = max(0, defer_cost_total - remaining)
    utilisation      = round(total_spent / budget * 100, 1) if budget > 0 else 0

    plan_result = {
        "budget":          budget,
        "totalSpent":      round(total_spent, 2),
        "remaining":       round(remaining, 2),
        "utilisation":     utilisation,
        "buyNow":          buy_now,
        "defer":           defer,
        "deferCostTotal":  defer_cost_total,
        "amountToSave":    round(amount_to_save, 2),
        "suggestions":     suggestions,
        "summary": {
            "itemsBought":   len([b for b in buy_now if b["decision"] == "buy"]),
            "itemsPartial":  len([b for b in buy_now if b["decision"] == "partial"]),
            "itemsDeferred": len(defer),
            "totalItems":    len(items),
        },
        "advice": _build_advice(budget, total_spent, defer, remaining),
    }

    # ── Step 5: Persist to DB (best effort) ───────────────────────────────────
    plans = get_collection("budget_plans")
    if plans is not None:
        try:
            plans.insert_one({
                "vendorId":  vendor_id,
                "budget":    budget,
                "items":     items,
                "result":    plan_result,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass

    return jsonify(plan_result), 200


def _build_advice(budget: float, spent: float, defer: list, remaining: float) -> str:
    pct = spent / budget * 100 if budget > 0 else 0

    if not defer:
        return (
            f"Your ₦{budget:,.0f} covers everything on your list. "
            f"₦{spent:,.0f} allocated ({pct:.0f}% of budget), "
            f"₦{remaining:,.0f} left over."
        )

    high_priority = [d for d in defer if d["demandScore"] >= 6.0]
    if high_priority:
        names      = ", ".join(d["name"] for d in high_priority[:2])
        extra_cost = sum(d["totalCost"] for d in high_priority)
        return (
            f"Your ₦{budget:,.0f} covers your priority items (₦{spent:,.0f} spent). "
            f"However, {names} {'are' if len(high_priority) > 1 else 'is'} high-demand "
            f"and couldn't fit. Try to raise an extra ₦{extra_cost:,.0f} before your next market trip."
        )

    return (
        f"₦{spent:,.0f} of your ₦{budget:,.0f} budget is allocated ({pct:.0f}%). "
        f"{len(defer)} lower-priority item{'s' if len(defer) > 1 else ''} "
        f"can wait until you have more funds — they won't significantly hurt your sales."
    )


@budget_bp.route("/history", methods=["GET"])
@jwt_required()
def get_budget_history():
    vendor_id = get_jwt_identity()
    plans     = get_collection("budget_plans")

    if plans is None:
        return jsonify({"plans": [], "total": 0}), 200

    results = list(
        plans.find({"vendorId": vendor_id}, {"_id": 0})
             .sort("createdAt", -1)
             .limit(10)
    )
    return jsonify({"plans": results, "total": len(results)}), 200