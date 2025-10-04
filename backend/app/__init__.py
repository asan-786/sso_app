from flask import Flask, jsonify
from .config import Config
from .models import db
from .auth_routes import bp as auth_bp
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt
from .token_service import is_token_blacklisted

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    jwt = JWTManager(app)

    # Check token blacklist before allowing access
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        return is_token_blacklisted(jti)

    # register blueprints
    app.register_blueprint(auth_bp)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    return app
