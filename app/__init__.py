from flask import Flask, session
from config import Config

def create_app(config_class=Config):
    # Adjust template and static folders to root directories since we will move them
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.users import users_bp
    from app.blueprints.chat import chat_bp
    from app.blueprints.spaces import spaces_bp
    from app.blueprints.tasks import tasks_bp
    from app.blueprints.Subtask import subtask_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(spaces_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(subtask_bp)

    @app.context_processor
    def inject_role():
        return {
            "current_role": session.get("role", "member"),
            "is_admin": session.get("role", "member") == "admin",
        }

    return app
