# users/routes.py
from flask import Blueprint, request

echo_bp = Blueprint('echo', __name__, url_prefix='/echo')



############ ECHO #############
@echo_bp.route('/', methods=['GET', 'POST'])
@echo_bp.route('/<path:subpath>', methods=['GET', 'POST'])
def echo(subpath=''):
    if request.method == 'POST':
        data = request.get_json()  # Per payloads JSON
        if data is None:
            data = request.form  # Per form data
    else:
        data = None
    return data or {}  # Restituisce un JSON vuoto se `data` è None

