from functools import wraps
from flask import session, jsonify
from models import User

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"message": "User not authenticated"}), 401
        
        # Verifica se l'utente esiste nel database
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 401
        
        # Aggiungi l'utente agli argomenti della funzione
        return f(*args, **kwargs)
    return decorated_function
