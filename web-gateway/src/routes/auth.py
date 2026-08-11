from flask import Blueprint, request, jsonify, g
import jwt # pyJWT
import json
import os
from datetime import datetime, timedelta, timezone
import bcrypt

import db
from psycopg2 import errors as pg_errors

from decorators import require_login

auth_bp = Blueprint('auth', __name__, url_prefix='/api')
SECRET_KEY = os.environ["JWT_SECRET_KEY"]

EXAM_TYPES = {'web', 'pwn', 'crypto'}

@auth_bp.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    email = request.form.get('email', '').strip() or None
    exam_type = request.form.get('exam_type', '').strip() or None

    if not username or not password: return jsonify({"error": "Missing fields"}), 400
    if exam_type is not None and exam_type not in EXAM_TYPES:
        return jsonify({"error": "Invalid exam_type"}), 400
    if db.get_user_by_username(username) is not None: return jsonify({"error": "Username already exists"}), 409

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        user_id = db.create_user(username, hashed_pw, email, exam_type)
    except pg_errors.UniqueViolation:
        return jsonify({"error": "Username already exists"}), 409

    db.create_activity_log(user_id, 'Registered account')

    body = '{' \
              + '"role": "' + "user" \
              + '", "username": "' + str(username) \
              + '"}'

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid username format"}), 400

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

    user = db.get_user_by_username(username)
    if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        return jsonify({"error": "Invalid credentials"}), 401

    db.create_activity_log(user['id'], 'Logged in')

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

@auth_bp.route('/logout', methods=['POST'])
def logout():
    resp = jsonify({"message": "Logged out"})
    resp.set_cookie('session_token', '', expires=0)
    return resp

@auth_bp.route('/me')
@require_login
def me():
    return jsonify({
        "username": g.user.get('username'),
        "role": g.user.get('role')
    })