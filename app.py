"""
Bloom Backend — Flask API
Run: python app.py
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"]               = os.getenv("SECRET_KEY", "bloom-dev-secret-2026")
    app.config["JWT_SECRET_KEY"]           = os.getenv("JWT_SECRET_KEY", "bloom-jwt-dev-2026")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

    CORS(app, origins=[
        "http://localhost:5173",
        "https://bloom-theta-pink.vercel.app/",
        os.getenv("FRONTEND_URL", "https://bloom-theta-pink.vercel.app/"),
    ], supports_credentials=True)

    Bcrypt(app)
    JWTManager(app)

    # Init DB connection at startup
    from models.database import get_db
    get_db()

    # Register all blueprints
    from routes.auth      import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.budget    import budget_bp
    from routes.admin     import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(admin_bp)

    @app.route("/api/health")
    def health():
        from models.database import is_connected
        return jsonify({
            "status":     "ok",
            "app":        "Bloom API",
            "version":    "2.0.0",
            "university": "Crawford University",
            "dbConnected": is_connected(),
        })

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n  Bloom API  http://localhost:{port}")
    print(f"  Admin key: {os.getenv('ADMIN_KEY', 'bloom-admin-2026-crawford')}")
    print(f"  Demo mode: demo@bloom.ng / demo123  (when no MongoDB)\n")
    app.run(host="0.0.0.0", port=port,
            debug=os.getenv("FLASK_DEBUG", "True") == "True")
