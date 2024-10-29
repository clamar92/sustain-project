from flask import Flask
from config import Config
from models import db, User, EnvironmentalData
from flask_migrate import Migrate
from users.routes import users_bp
from echo.routes import echo_bp
from map.routes import map_bp
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView


app = Flask(__name__)
app.secret_key = 'akjakjHJGFG54655!ygjknkl_iqiqwwee64w4w5e32c'
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(users_bp)
app.register_blueprint(echo_bp)
app.register_blueprint(map_bp)


# Inizializzazione di Flask-Admin
admin = Admin(app, name='My Admin', template_mode='bootstrap4')

# Aggiunta delle viste dei modelli con endpoint unici
#admin.add_view(ModelView(User, db.session, endpoint='admin_user'))
admin.add_view(ModelView(EnvironmentalData, db.session, endpoint='admin_environmental_data'))


@app.cli.command("reset-db")
def reset_db():
    """Elimina e ricrea tutte le tabelle del database."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database resettato.")


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
