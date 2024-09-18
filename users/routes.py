# users/routes.py
from flask import Blueprint, request, jsonify, current_app, send_from_directory, url_for, session
from models import db, User
from google.oauth2 import id_token
from google.auth.transport import requests
import os
from decorators import login_required  # Importa il decoratore


WEB_CLIENT_ID = "813739084992-fqmluqgaip3tq8t9fdtptu3c8cdetala.apps.googleusercontent.com"


users_bp = Blueprint('user', __name__, url_prefix='/user')


################################################################
########################## REGISTRATION ########################
################################################################
@users_bp.route('/registration', methods=['POST'])
def registration():
    data = request.get_json()
    email = data.get('email')
    password = data.get('hashedPassword')
    salt = data.get('salt')
    google_user = False
    punteggio = data.get('points', 0)
    url_icon = data.get('profilePictureURI')

    # check icona
    try:
        nome_file = os.path.basename(url_icon)
        cartella_icone = "static/icons"
        percorso_completo = os.path.join(cartella_icone, nome_file)
        if os.path.exists(percorso_completo):
            pass
        else:
            return jsonify({"message": "Icon does not exist."}), 400
    except:
        return jsonify({"message": "Icon does not exist."}), 400

    nome = data.get('name')
    cognome = data.get('surname')
    username = data.get('username')
    phone_number = data.get('phoneNumber', '')  # Default a stringa vuota se non specificato

    # Verifica se l'utente esiste già per email o username
    existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
    if existing_user:
        return jsonify({"message": "User already exists"}), 400

    # Crea un nuovo utente
    new_user = User(email=email, password_hash=password, salt=salt,
                    google_user=google_user, punteggio=punteggio, url_icon=url_icon,
                    nome=nome, cognome=cognome, username=username, phone_number=phone_number, 
                    icon_type = 1)
    db.session.add(new_user)
    db.session.commit()

    # Prepara la risposta con i dati dell'utente
    user_data = {
        "email": email,
        "points": punteggio,
        "profilePictureURI": url_icon,
        "name": nome,
        "surname": cognome,
        "username": username,
        "phoneNumber": phone_number,
        "hashedPassword": "",  # Non restituire la password hashed
        "salt": ""  # Non restituire il salt
    }

    return jsonify(user_data), 200





################################################################
############################# LOGIN ############################
################################################################
@users_bp.route('/getSalt', methods=['GET'])
def getSalt():
    username = request.args.get('username')

    if not username:
        return jsonify({"message": "Username is required as query parameter"}), 400

    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    return user.salt, 200


@users_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    hashedPassword = data.get('hashedPassword')

    if not username or not hashedPassword:
        return jsonify({"message": "Username and password are required"}), 400

    # Cerca l'utente nel database per username
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"message": "Invalid username or password"}), 401

    # Controlla se l'utente è autenticato con Google
    if user.google_user:
        return jsonify({"message": "User authenticated with Google"}), 401

    # Controlla la password
    if not user.check_password(hashedPassword):
        return jsonify({"message": "Invalid username or password"}), 401
    

    # Se l'autenticazione ha successo, memorizza le informazioni di sessione
    session['user_id'] = user.id
    session['username'] = user.username


    # Se l'autenticazione ha successo, prepara la risposta JSON con tutti i campi dell'utente
    user_data = {
        "email": user.email,
        "points": user.punteggio,
        "profilePictureURI": user.url_icon,
        "name": user.nome,
        "surname": user.cognome,
        "username": user.username,
        "phoneNumber": user.phone_number,
        "hashedPassword": "",
        "salt": ""
    }

    return jsonify(user_data), 200





################################################################
####################### LOGIN WITH GOOGLE ######################
################################################################
@users_bp.route('/validate', methods=['POST'])
def validate_user():
    token = request.data.decode('utf-8')
    
    try:
        # Verifica del token con Google
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), WEB_CLIENT_ID)

        # Estrai informazioni dal token
        email = idinfo.get('email')
        given_name = idinfo.get('given_name')
        family_name = idinfo.get('family_name')
        picture = idinfo.get('picture')
        username = email.split('@')[0]

        # Controlla se l'utente esiste già nel database
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
                # Aggiorna il campo url_icon con la nuova immagine
                existing_user.url_icon = picture
                db.session.commit()

                # aggiungi sessione
                session['user_id'] = existing_user.id
                session['username'] = existing_user.username
    
                user_data = {
                    "email": existing_user.email,
                    "points": existing_user.punteggio,
                    "profilePictureURI": picture,
                    "name": existing_user.nome,
                    "surname": existing_user.cognome,
                    "username": existing_user.username,
                    "phoneNumber": existing_user.phone_number,
                    "hashedPassword": "",
                    "salt": ""
                }

                return jsonify(user_data), 200

        # Se l'utente non esiste, crealo
        new_user = User(
            email=email,
            password_hash='',  # Password vuota poiché è un utente Google
            salt='',  # Salt vuoto poiché è un utente Google
            google_user=True,
            punteggio=0,
            url_icon= picture,
            nome=given_name,
            cognome=family_name,
            username=username,
            phone_number='',
            icon_type = 0
        )
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['username'] = new_user.username

        user_data = {
                    "email": email,
                    "points": 0,
                    "profilePictureURI": picture,
                    "name": given_name,
                    "surname": family_name,
                    "username": username,
                    "phoneNumber": "",
                    "hashedPassword": "",
                    "salt": ""
                }            
        return jsonify(user_data), 200
    
    except ValueError as e:
        return jsonify({"message": "Token verification failed", "error": str(e)}), 400
    except KeyError as e:
        return jsonify({"message": "Missing key in token", "error": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500
    



################################################################
########################## USERS LIST ##########################
################################################################
@users_bp.route('/getUsersList', methods=['GET'])
@login_required  # Proteggi questa route
def getUsersList():
    users = User.query.all()

    users_list = []
    for user in users:
        user_data = {
            "email": user.email,
            "points": user.punteggio,
            "profilePictureURI": user.url_icon,
            "name": user.nome,
            "surname": user.cognome,
            "username": user.username,
            "phoneNumber": user.phone_number,
            # Puoi aggiungere altri campi se necessario
        }
        users_list.append(user_data)

    return jsonify(users_list)





################################################################
########################## USERS ICONS #########################
################################################################
@users_bp.route('/icons', methods=['GET'])
@login_required  # Proteggi questa route
def get_icons():
    # Directory delle icone
    icons_dir = os.path.join(current_app.static_folder, 'icons')
    
    # Ottieni l'elenco dei file di icone
    icons = [f for f in os.listdir(icons_dir) if os.path.isfile(os.path.join(icons_dir, f))]

    # Crea i link per accedere alle icone
    icon_links = [url_for('static', filename=f'icons/{icon}', _external=True) for icon in icons]

    return jsonify(icon_links)

# Servire singole icone
@users_bp.route('/icons/<filename>', methods=['GET'])
def serve_icon(filename):
    return send_from_directory(os.path.join(current_app.static_folder, 'icons'), filename)






################################################################
############################# LOGOUT ###########################
################################################################
@users_bp.route('/logout', methods=['GET'])
@login_required  # Proteggi questa route
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({"message": "Logout successful!"}), 200






################################################################
########################## CHECK LOGIN #########################
################################################################
@users_bp.route('/checkLogin', methods=['GET'])
@login_required  # Proteggi questa route
def checkLogin():
    if 'user_id' in session:
        user_id = session['user_id']
        username = session['username']
        existing_user = User.query.filter((User.id == user_id) | (User.username == username)).first()
        if existing_user:
                user_data = {
                    "email": existing_user.email,
                    "points": existing_user.punteggio,
                    "profilePictureURI": existing_user.url_icon,
                    "name": existing_user.nome,
                    "surname": existing_user.cognome,
                    "username": existing_user.username,
                    "phoneNumber": existing_user.phone_number,
                    "hashedPassword": "",
                    "salt": ""
                }

                return jsonify(user_data), 200
        else:
            return jsonify({"message": "User not found"}), 401
    else:
        return jsonify({"message": "User not found"}), 401
    





################################################################
####################### CHANGE USER ICON #######################
################################################################
@users_bp.route('/changeIcon', methods=['POST'])
@login_required  # Proteggi questa route
def changeIcon():
    url_icon = request.data.decode('utf-8')

    # Directory delle icone
    icons_dir = os.path.join(current_app.static_folder, 'icons')
    # Ottieni l'elenco dei file di icone
    icons = [f for f in os.listdir(icons_dir) if os.path.isfile(os.path.join(icons_dir, f))]
    # Crea i link per accedere alle icone
    icon_links = [url_for('static', filename=f'icons/{icon}', _external=True) for icon in icons]
    # Verifica se url_icon è presente in icon_links
    if url_icon in icon_links:
        pass
    else:
        return jsonify({"message": "Icon does not exist."}), 400
    

    if 'user_id' in session:
        user_id = session['user_id']
        username = session['username']
        existing_user = User.query.filter((User.id == user_id) | (User.username == username)).first()
        if existing_user:
                
                # Aggiorna il campo url_icon con la nuova immagine
                existing_user.url_icon = url_icon
                db.session.commit()

                user_data = {
                    "email": existing_user.email,
                    "points": existing_user.punteggio,
                    "profilePictureURI": existing_user.url_icon,
                    "name": existing_user.nome,
                    "surname": existing_user.cognome,
                    "username": existing_user.username,
                    "phoneNumber": existing_user.phone_number,
                    "hashedPassword": "",
                    "salt": ""
                }

                return jsonify(user_data), 200
        else:
            return jsonify({"message": "User not found"}), 401
    else:
        return jsonify({"message": "User not found"}), 401