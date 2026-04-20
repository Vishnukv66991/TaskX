from flask import Flask
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(spaces_bp)

    return app
