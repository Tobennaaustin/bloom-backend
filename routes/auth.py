from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models.database import get_collection
from bson import ObjectId
from datetime import datetime, timezone
import re

auth_bp  = Blueprint("auth", __name__, url_prefix="/api/auth")
bcrypt   = Bcrypt()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _vendor_to_dict(doc: dict) -> dict:
    return {
        "id":          str(doc["_id"]),
        "name":        doc.get("name", ""),
        "email":       doc.get("email", ""),
        "storeName":   doc.get("storeName", ""),
        "storeType":   doc.get("storeType", ""),
        "products":    doc.get("products", []),
        "restockTime": doc.get("restockTime", ""),
        "location":    doc.get("location", "Crawford University"),
        "createdAt":   doc.get("createdAt", ""),
    }

def _validate_email(email: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

# ── Register ──────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    required = ["name", "email", "password", "storeName", "storeType"]
    for field in required:
        if not data.get(field, "").strip():
            return jsonify({"error": f"'{field}' is required"}), 400

    if not _validate_email(data["email"]):
        return jsonify({"error": "Invalid email address"}), 400

    if len(data["password"]) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    vendors = get_collection("vendors")

    # Handle no-DB mode
    if vendors is None:
        # Return mock token for demo/dev
        mock_user = {
            "id": "demo-user-001",
            "name": data["name"],
            "email": data["email"],
            "storeName": data["storeName"],
            "storeType": data["storeType"],
            "products": data.get("products", []),
            "restockTime": data.get("restockTime", ""),
            "location": data.get("location", "Crawford University"),
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        token = create_access_token(identity=mock_user["id"])
        return jsonify({"token": token, "user": mock_user}), 201

    # Check duplicate email
    if vendors.find_one({"email": data["email"].lower().strip()}):
        return jsonify({"error": "An account with this email already exists"}), 409

    pw_hash = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

    vendor_doc = {
        "name":        data["name"].strip(),
        "email":       data["email"].lower().strip(),
        "password":    pw_hash,
        "storeName":   data["storeName"].strip(),
        "storeType":   data["storeType"],
        "products":    data.get("products", []),
        "restockTime": data.get("restockTime", ""),
        "location":    data.get("location", "Crawford University, Igbesa"),
        "createdAt":   datetime.now(timezone.utc).isoformat(),
    }

    result = vendors.insert_one(vendor_doc)
    vendor_doc["_id"] = result.inserted_id

    token = create_access_token(identity=str(result.inserted_id))
    return jsonify({"token": token, "user": _vendor_to_dict(vendor_doc)}), 201

# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    email    = data.get("email", "").lower().strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    vendors = get_collection("vendors")

    # No-DB demo mode
    if vendors is None:
        if email == "demo@bloom.ng" and password == "demo123":
            mock_user = {
                "id": "demo-user-001",
                "name": "Demo Vendor",
                "email": email,
                "storeName": "Demo Store",
                "storeType": "provision",
                "products": ["Pure water (sachet)", "Soft drinks", "Bread"],
                "restockTime": "2-3days",
                "location": "Crawford University",
                "createdAt": "2026-01-01",
            }
            token = create_access_token(identity="demo-user-001")
            return jsonify({"token": token, "user": mock_user}), 200
        return jsonify({"error": "Invalid email or password"}), 401

    vendor = vendors.find_one({"email": email})
    if not vendor or not bcrypt.check_password_hash(vendor["password"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=str(vendor["_id"]))
    return jsonify({"token": token, "user": _vendor_to_dict(vendor)}), 200

# ── Me ────────────────────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    vendor_id = get_jwt_identity()
    vendors   = get_collection("vendors")

    if vendors is None:
        # Demo mode
        return jsonify({"user": {
            "id": vendor_id,
            "name": "Demo Vendor",
            "email": "demo@bloom.ng",
            "storeName": "Demo Store",
            "storeType": "provision",
            "products": ["Pure water (sachet)", "Soft drinks", "Bread"],
            "restockTime": "2-3days",
            "location": "Crawford University",
            "createdAt": "2026-01-01",
        }}), 200

    try:
        vendor = vendors.find_one({"_id": ObjectId(vendor_id)})
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    return jsonify({"user": _vendor_to_dict(vendor)}), 200
