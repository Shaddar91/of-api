from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/api/v1/hello")
    def hello():
        return {"message": "hello"}

    return app
