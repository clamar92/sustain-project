# config.py
class Config:
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:faketrublo22@localhost:5432/Sustain-project"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True