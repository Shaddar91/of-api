"""Flask application factory."""

from flask import Flask
from flask_cors import CORS

from app.auth import bp as auth_bp
from app.cli import register_commands
from app.config import Config


def create_app() -> Flask:
    config = Config.from_env()
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_URL=config.database_url,
        TOKEN_TTL_SECONDS=config.token_ttl_seconds,
        CORS_ALLOWED_ORIGINS=config.cors_allowed_origins,
    )
    CORS(app, origins=config.cors_allowed_origins, supports_credentials=False)
    app.register_blueprint(auth_bp)
    register_commands(app)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/hello")
    def hello() -> dict[str, str]:
        return {"message": "hello"}

    return app
