import os
import jwt
from functools import wraps
from flask import request, render_template, g, redirect

SECRET_KEY = os.environ['JWT_SECRET_KEY']

def require_login_page(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('session_token')
        if not token:
            return redirect(f'/login?next={request.path}')
        try:
            g.user = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return redirect(f'/login?next={request.path}')
        return f(*args, **kwargs)
    return wrapper

def require_admin_page(f):
    @wraps(f)
    @require_login_page
    def wrapper(*args, **kwargs):
        if g.user.get('role') != 'admin':
            return render_template('errors/403.html'), 403
        return f(*args, **kwargs)
    return wrapper