from flask import Blueprint, request, jsonify, g
import jwt # pyJWT
import json
import os
from datetime import datetime, timedelta, timezone
import bcrypt

from db import get_user_by_username, create_user
from psycopg2 import errors as pg_errors

from decorators import require_login

auth_bp = Blueprint('auth', __name__, url_prefix='/api')
SECRET_KEY = os.environ["JWT_SECRET_KEY"]

@auth_bp.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password: return jsonify({"error": "Missing fields"}), 400
    if get_user_by_username(username) is not None: return jsonify({"error": "Username already exists"}), 409

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try: user_id = create_user(username, hashed_pw)
    except pg_errors.UniqueViolation: return jsonify({"error": "Username already exists"}), 409

    body = '{' \
              + '"role": "' + "user" \
              + '", "username": "' + str(username) \
              + '"}'
    payload = json.loads(body)

    now = datetime.now(timezone.utc)
    payload['sub'] = user_id
    payload['iat'] = int(now.timestamp())
    payload['exp'] = int((now + timedelta(hours=2)).timestamp())

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    resp = jsonify({"message": "Registered successfully."})
    resp.set_cookie('session_token', token, httponly=True)
    return resp

@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password: return jsonify({"error": "Missing fields"}), 400

    user = get_user_by_username(username)
    if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        return jsonify({"error": "Invalid credentials"}), 401

    body = '{' \
              + '"role": "' + str(user['role']) \
              + '", "username": "' + str(user['username']) \
              + '"}'
    
    payload = json.loads(body)

    now = datetime.now(timezone.utc)
    payload['iat'] = int(now.timestamp())
    payload['exp'] = int((now + timedelta(hours=2)).timestamp())
    payload['sub'] = user['id']

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    resp = jsonify({"message": "Logged in successfully."})
    resp.set_cookie('session_token', token, httponly=True)
    return resp

@auth_bp.route('/me')
@require_login
def me():
    return jsonify({
        "username": g.user.get('username'),
        "role": g.user.get('role')
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    resp = jsonify({"message": "Logged out"})
    resp.set_cookie('session_token', '', expires=0)
    return resp