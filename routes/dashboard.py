from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import get_collection
from services.recommendation_engine import generate_report
from bson import ObjectId

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

def _get_vendor(vendor_id: str):
    vendors = get_collection("vendors")
    if vendors is None:
        # Demo mode
        return {
            "_id": vendor_id,
            "storeType": "provision",
            "products": ["Pure water (sachet)", "Soft drinks", "Bread", "Gala", "Biscuits"],
            "restockTime": "2-3days",
        }
    try:
        return vendors.find_one({"_id": ObjectId(vendor_id)})
    except Exception:
        return None

# ── Full dashboard data ───────────────────────────────────────────────────────

@dashboard_bp.route("", methods=["GET"])
@jwt_required()
def get_dashboard():
    vendor_id = get_jwt_identity()
    vendor    = _get_vendor(vendor_id)
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    report = generate_report(
        store_type   = vendor.get("storeType", "mixed"),
        products     = vendor.get("products", []),
        restock_time = vendor.get("restockTime", "weekly"),
    )
    return jsonify(report), 200

# ── Products ──────────────────────────────────────────────────────────────────

@dashboard_bp.route("/products", methods=["GET"])
@jwt_required()
def get_products():
    vendor_id = get_jwt_identity()
    vendor    = _get_vendor(vendor_id)
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    report = generate_report(
        store_type   = vendor.get("storeType", "mixed"),
        products     = vendor.get("products", []),
        restock_time = vendor.get("restockTime", "weekly"),
    )
    return jsonify({"products": report["topProducts"]}), 200

@dashboard_bp.route("/products", methods=["PUT"])
@jwt_required()
def update_products():
    vendor_id = get_jwt_identity()
    data      = request.get_json()
    products  = data.get("products", [])

    vendors = get_collection("vendors")
    if vendors is None:
        return jsonify({"message": "Products updated (demo mode)"}), 200

    try:
        vendors.update_one({"_id": ObjectId(vendor_id)}, {"$set": {"products": products}})
    except Exception:
        return jsonify({"error": "Update failed"}), 500

    return jsonify({"message": "Products updated successfully"}), 200

# ── Alerts ────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/alerts", methods=["GET"])
@jwt_required()
def get_alerts():
    vendor_id = get_jwt_identity()
    vendor    = _get_vendor(vendor_id)
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    report = generate_report(
        store_type   = vendor.get("storeType", "mixed"),
        products     = vendor.get("products", []),
        restock_time = vendor.get("restockTime", "weekly"),
    )
    return jsonify({"alerts": report["restockAlerts"]}), 200

# ── Recommendations ───────────────────────────────────────────────────────────

@dashboard_bp.route("/recommendations", methods=["GET"])
@jwt_required()
def get_recommendations():
    vendor_id = get_jwt_identity()
    vendor    = _get_vendor(vendor_id)
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    report = generate_report(
        store_type   = vendor.get("storeType", "mixed"),
        products     = vendor.get("products", []),
        restock_time = vendor.get("restockTime", "weekly"),
    )
    return jsonify({
        "recommendations": report["recommendations"],
        "addThese":        report["addThese"],
        "reduce":          report["reduce"],
        "insight":         report["insight"],
    }), 200

# ── Gap Analysis ──────────────────────────────────────────────────────────────

@dashboard_bp.route("/gap-analysis", methods=["GET"])
@jwt_required()
def get_gap_analysis():
    vendor_id = get_jwt_identity()
    vendor    = _get_vendor(vendor_id)
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    report = generate_report(
        store_type   = vendor.get("storeType", "mixed"),
        products     = vendor.get("products", []),
        restock_time = vendor.get("restockTime", "weekly"),
    )
    return jsonify({"gapAnalysis": report["gapAnalysis"]}), 200
