from flask import Flask
from config import Config
from models import db
from flask_migrate import Migrate
from users.routes import users_bp
from echo.routes import echo_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(users_bp)
app.register_blueprint(echo_bp)


@app.cli.command("reset-db")
def reset_db():
    """Elimina e ricrea tutte le tabelle del database."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database resettato.")


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
