from flask import Flask, redirect
from config import Config
from models import db, User, EnvironmentalData, Cell
from flask_migrate import Migrate
from users.routes import users_bp
from echo.routes import echo_bp
from map.routes import map_bp
from flask_admin import Admin, AdminIndexView
from flask_admin.base import expose
from flask_admin.contrib.sqla import ModelView
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


#TODO AGGIUNGERE VERIFICA EMAIL
#TODO AGIIUNGERE SESSIONE LIMITATA (DA REFRESH A LOGIN)
#TODO 403 Forbidden - Oppure? - MAIL DOES NOT VERIFIED (FORBIDDEN)
#TODO passare ad https con Let's encrypt



app = Flask(__name__)
app.secret_key = 'akjakjHJGFG54655!ygjknkl_iqiqwwee64w4w5e32c'
app.config.from_object(Config)

# Limiter: limita richieste per IP
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "100 per hour", "60 per minute"]
)

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(users_bp)
app.register_blueprint(echo_bp)
app.register_blueprint(map_bp)


# Inizializzazione di Flask-Admin
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        return redirect(self.get_url('admin_user.index_view'))


admin = Admin(app, name='My Admin', template_mode='bootstrap3', index_view=MyAdminIndexView())


class EnvironmentalDataView(ModelView):
    # Mostra tutti i campi che ti interessano
    column_list = [
        'user_id', 'cell_id', 'battery_capacity', 'battery_lifetime',
        'temperature', 'humidity', 'co2_scd41', 'co2_stc31c', 'voc',
        'pm1_0', 'pm2_5', 'pm4_0', 'pm10', 'timestamp'
    ]

    # Opzionale: rendi alcuni campi non modificabili
    form_excluded_columns = ['user_id', 'cell_id', 'timestamp']

    # Opzionale: aggiungi filtri
    column_filters = ['user_id', 'cell_id', 'timestamp']


class UserView(ModelView):
    # Mostra tutti i campi del modello User
    column_list = [
        'id', 'email', 'google_user', 'punteggio',
        'nome', 'cognome', 'username', 'phone_number'
    ]

    # Opzionale: escludi campi dal form (es. password e salt)
    form_excluded_columns = ['password_hash', 'salt']

    # Filtri utili
    column_filters = ['id', 'email', 'google_user', 'punteggio', 'nome', 'cognome']

    # Abilita ricerca
    column_searchable_list = ['email', 'nome', 'cognome', 'username', 'id']


class CellView(ModelView):
    column_list = ['id', 'top_left_lon', 'top_left_lat', 'bottom_right_lon', 'bottom_right_lat', 'address', 'air_quality', 'last_aq_update']
    column_filters = ['address', 'air_quality']
    column_searchable_list = ['address']


# Aggiunta delle viste dei modelli con endpoint unici
admin.add_view(UserView(User, db.session, endpoint='admin_user'))
admin.add_view(EnvironmentalDataView(EnvironmentalData, db.session, endpoint='admin_environmental_data'))
admin.add_view(CellView(Cell, db.session, endpoint='admin_cell'))


@app.cli.command("reset-db")
def reset_db():
    """Elimina e ricrea tutte le tabelle del database."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database resettato.")


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
