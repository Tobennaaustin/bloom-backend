"""
Bloom Admin API
Password-protected admin endpoints for Tobenna to manage the system.
"""

from flask import Blueprint, request, jsonify, Response
from models.database import get_collection, is_connected
from services.recommendation_engine import CAMPUS_DEMAND
from bson import ObjectId
from datetime import datetime, timezone
import csv, io, os

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

ADMIN_KEY = os.getenv("ADMIN_KEY", "bloom-admin-2026-crawford")


def _require_admin():
    key = request.headers.get("X-Admin-Key") or request.args.get("admin_key")
    if key != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    return None


def _vendor_safe(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id", ""))
    doc.pop("password", None)
    return doc


# ── Overview stats ─────────────────────────────────────────────────────────────

@admin_bp.route("/stats", methods=["GET"])
def admin_stats():
    err = _require_admin()
    if err: return err

    vendors = get_collection("vendors")
    plans   = get_collection("budget_plans")

    if vendors is None:
        return jsonify({
            "totalVendors": 7,
            "storeTypes": {"provision": 3, "food": 2, "drinks": 1, "stationery": 1},
            "totalBudgetPlans": 0,
            "dbConnected": False,
            "campusDemandProducts": len(CAMPUS_DEMAND),
        })

    total     = vendors.count_documents({})
    plan_count = plans.count_documents({}) if plans is not None else 0

    # Group by store type
    pipeline = [{"$group": {"_id": "$storeType", "count": {"$sum": 1}}}]
    type_counts = {r["_id"]: r["count"] for r in vendors.aggregate(pipeline)}

    # Recent registrations (last 7 days)
    from datetime import timedelta
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent = vendors.count_documents({"createdAt": {"$gte": week_ago}})

    return jsonify({
        "totalVendors":       total,
        "storeTypes":         type_counts,
        "recentRegistrations": recent,
        "totalBudgetPlans":   plan_count,
        "dbConnected":        True,
        "campusDemandProducts": len(CAMPUS_DEMAND),
    })


# ── List all vendors ───────────────────────────────────────────────────────────

@admin_bp.route("/vendors", methods=["GET"])
def list_vendors():
    err = _require_admin()
    if err: return err

    page  = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    search = request.args.get("search", "")
    store_type = request.args.get("storeType", "")

    vendors = get_collection("vendors")
    if vendors is None:
        return jsonify({"vendors": [], "total": 0, "page": page})

    query = {}
    if search:
        query["$or"] = [
            {"name":      {"$regex": search, "$options": "i"}},
            {"email":     {"$regex": search, "$options": "i"}},
            {"storeName": {"$regex": search, "$options": "i"}},
        ]
    if store_type:
        query["storeType"] = store_type

    total = vendors.count_documents(query)
    docs  = list(
        vendors.find(query, {"password": 0})
               .sort("createdAt", -1)
               .skip((page - 1) * limit)
               .limit(limit)
    )
    for d in docs:
        d["id"] = str(d.pop("_id"))

    return jsonify({"vendors": docs, "total": total, "page": page, "pages": -(-total // limit)})


# ── Get single vendor ──────────────────────────────────────────────────────────

@admin_bp.route("/vendors/<vendor_id>", methods=["GET"])
def get_vendor(vendor_id):
    err = _require_admin()
    if err: return err

    vendors = get_collection("vendors")
    if vendors is None:
        return jsonify({"error": "No database connected"}), 503

    try:
        doc = vendors.find_one({"_id": ObjectId(vendor_id)}, {"password": 0})
    except Exception:
        return jsonify({"error": "Invalid vendor ID"}), 400

    if not doc:
        return jsonify({"error": "Vendor not found"}), 404

    doc["id"] = str(doc.pop("_id"))
    return jsonify({"vendor": doc})


# ── Delete vendor ─────────────────────────────────────────────────────────────

@admin_bp.route("/vendors/<vendor_id>", methods=["DELETE"])
def delete_vendor(vendor_id):
    err = _require_admin()
    if err: return err

    vendors = get_collection("vendors")
    if vendors is None:
        return jsonify({"error": "No database connected"}), 503

    try:
        result = vendors.delete_one({"_id": ObjectId(vendor_id)})
    except Exception:
        return jsonify({"error": "Invalid vendor ID"}), 400

    if result.deleted_count == 0:
        return jsonify({"error": "Vendor not found"}), 404

    return jsonify({"message": "Vendor deleted successfully"})


# ── Export vendors as CSV ──────────────────────────────────────────────────────

@admin_bp.route("/export/vendors", methods=["GET"])
def export_vendors():
    err = _require_admin()
    if err: return err

    vendors = get_collection("vendors")
    if vendors is None:
        return jsonify({"error": "No database connected"}), 503

    docs = list(vendors.find({}, {"password": 0}).sort("createdAt", -1))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Name", "Email", "Store Name", "Store Type",
        "Products", "Restock Time", "Location", "Created At"
    ])
    for d in docs:
        writer.writerow([
            str(d.get("_id", "")),
            d.get("name", ""),
            d.get("email", ""),
            d.get("storeName", ""),
            d.get("storeType", ""),
            " | ".join(d.get("products", [])),
            d.get("restockTime", ""),
            d.get("location", ""),
            d.get("createdAt", ""),
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=bloom_vendors.csv"}
    )


# ── Export budget plans as CSV ─────────────────────────────────────────────────

@admin_bp.route("/export/budget-plans", methods=["GET"])
def export_budget_plans():
    err = _require_admin()
    if err: return err

    plans = get_collection("budget_plans")
    if plans is None:
        return jsonify({"error": "No database connected"}), 503

    docs = list(plans.find({}).sort("createdAt", -1))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Vendor ID", "Budget (₦)", "Spent (₦)", "Items Requested",
        "Items Bought", "Items Deferred", "Created At"
    ])
    for d in docs:
        r = d.get("result", {})
        s = r.get("summary", {})
        writer.writerow([
            d.get("vendorId", ""),
            d.get("budget", ""),
            r.get("totalSpent", ""),
            " | ".join(d.get("items", [])),
            s.get("itemsBought", ""),
            s.get("itemsDeferred", ""),
            d.get("createdAt", ""),
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=bloom_budget_plans.csv"}
    )


# ── DB health ─────────────────────────────────────────────────────────────────

@admin_bp.route("/health", methods=["GET"])
def admin_health():
    err = _require_admin()
    if err: return err

    vendors = get_collection("vendors")
    connected = vendors is not None

    return jsonify({
        "dbConnected": connected,
        "mongoUri": "configured" if os.getenv("MONGO_URI") else "using default localhost",
        "adminKey": "configured" if os.getenv("ADMIN_KEY") else "using default",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
