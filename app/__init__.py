from flask import Flask, jsonify, render_template, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from .extensions import csrf, db, login_manager, migrate


def create_app(config_object=Config):
    app = Flask(__name__, template_folder="templates", static_folder="../assets", static_url_path="/assets")
    app.config.from_object(config_object)
    if app.config.get("FLASK_ENV") == "production" or app.config.get("ENV") == "production":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        if app.config.get("SECRET_KEY") in (None, "", "dev-only-change-me"):
            raise RuntimeError("SECRET_KEY must be set in production")
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    from . import models  # noqa: F401
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .participant import bp as participant_bp
    from .analytics import bp as analytics_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(participant_bp)
    app.register_blueprint(analytics_bp)

    @app.get("/")
    def home():
        return render_template("landing.html")

    @app.get("/style.css")
    def stylesheet():
        return send_from_directory(app.root_path + "/..", "style.css")

    @app.get("/app.css")
    def app_stylesheet():
        return send_from_directory(app.root_path + "/static", "app.css")

    @app.get("/health")
    def health():
        try:
            db.session.execute(db.text("SELECT 1"))
            return jsonify(status="ok", database="ok")
        except Exception:
            db.session.rollback()
            return jsonify(status="unavailable", database="unavailable"), 503

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="We couldn't find that page."), 404

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        return render_template("error.html", code=500, message="Something went wrong. Please try again."), 500

    return app
