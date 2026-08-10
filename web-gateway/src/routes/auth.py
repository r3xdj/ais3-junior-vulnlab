from flask import Blueprint, request, jsonify, redirect
import jwt # pyJWT
import json
from os import getenv
from datetime import datetime, timedelta, timezone

auth_bp = Blueprint('auth', __name__)
SECRET_KEY = getenv("JWT-Key", "ais3_defult_KEY")

@auth_bp.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '')
    password = request.form.get('password', '')

    body = '{' \
              + '"role": "' + "user" \
              + '", "username": "' + str(username) \
              + '"}'
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid username or password"}), 400

    now = datetime.now(timezone.utc)
    payload['iat'] = int(now.timestamp())
    payload['exp'] = int((now + timedelta(hours=2)).timestamp())   # 2 小時後過期
    payload['sub'] = user_id                             # 從 DB insert 拿到的 id

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    resp = jsonify({"message": "Registered successfully"})
    resp.set_cookie('session_token', token, httponly=True)
    return resp

@auth_bp.route('/panel')
def panel():
    token = request.cookies.get('session_token')
    if not token:
        return redirect('/login')
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return redirect('/login')

    if decoded.get('admin') == 'True':
        return render_admin_panel()  # 進入管理員面板
    return render_user_panel()       # 一般使用者面板