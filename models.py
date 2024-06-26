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
    valore = db.Column(db.Integer, default=0, nullable=False)