import os
import jwt
from functools import wraps
from flask import request, g, jsonify

SECRET_KEY = os.environ['JWT_SECRET_KEY']

def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('session_token')
        if not token:
            return jsonify({"error": "Unauthorized"}), 401
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        g.user = decoded
        return f(*args, **kwargs)
    return wrapper

def require_admin(f):
    @wraps(f)
    @require_login
    def wrapper(*args, **kwargs):
        if g.user.get('role') != 'admin':
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return wrapper