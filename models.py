# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    salt = db.Column(db.String(32), nullable=False)
    google_user = db.Column(db.Boolean, default=False)  # Nuovo campo booleano
    punteggio = db.Column(db.Integer)  # Nuovo campo intero
    url_icon = db.Column(db.String(200))  # Nuovo campo stringa per URL icona
    nome = db.Column(db.String(50))  # Nuovo campo stringa per nome
    cognome = db.Column(db.String(50))  # Nuovo campo stringa per cognome
    username = db.Column(db.String(50))  # Nuovo campo stringa per username
    phone_number = db.Column(db.String(20), default='')  # Nuovo campo stringa per numero
    icon_type = db.Column(db.Integer, default=0)  # 0 Google icon - 1 Avatar icon - 2 user icon


    def check_password(self, hashedPassword):
        print(self.password_hash)
        print(hashedPassword)
        if self.password_hash == hashedPassword:
            return True
        else:
            return False
        

class Cell(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    top_left_lon = db.Column(db.Float, nullable=False)
    top_left_lat = db.Column(db.Float, nullable=False)
    bottom_right_lon = db.Column(db.Float, nullable=False)
    bottom_right_lat = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(400), default='')
    air_quality = db.Column(db.Integer, default=0, nullable=False)
    last_aq_update = db.Column(db.DateTime, nullable=True, default=None)  # ⬅️ nuovo campo


class EnvironmentalData(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Relazione con la tabella User
    cell_id = db.Column(db.Integer, db.ForeignKey('cell.id'), nullable=False, index=True)
    battery_capacity = db.Column(db.Integer, nullable=False)  # Capacità residua della batteria (%)
    battery_lifetime = db.Column(db.Integer, nullable=False)  # Durata residua della batteria (minuti)
    temperature = db.Column(db.Float, nullable=False)  # Temperatura ambientale (°C)
    humidity = db.Column(db.Integer, nullable=False)  # Umidità ambientale (%RH)
    co2_scd41 = db.Column(db.Integer, nullable=False)  # CO2 ambientale (SCD41, ppm)
    co2_stc31c = db.Column(db.Integer, nullable=False)  # CO2 ambientale (STC31-C, vol%)
    voc = db.Column(db.Integer, nullable=False)  # VOC ambientale (ppm)
    pm1_0 = db.Column(db.Integer, nullable=False)  # PM1.0 (μg/m³)
    pm2_5 = db.Column(db.Integer, nullable=False)  # PM2.5 (μg/m³)
    pm4_0 = db.Column(db.Integer, nullable=False)  # PM4.0 (μg/m³)
    pm10 = db.Column(db.Integer, nullable=False)  # PM10 (μg/m³)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.now())  # Data e ora di raccolta del dato
    
    # Relazione con la tabella User
    user = db.relationship('User', backref=db.backref('environmental_data', lazy=True))
    cell = db.relationship('Cell', backref=db.backref('environmental_data', lazy=True))


