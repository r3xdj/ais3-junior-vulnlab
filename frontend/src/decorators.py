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

def redirect_if_logged_in(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('session_token')
        if token:
            try:
                jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                return redirect('/panel')
            except jwt.InvalidTokenError:
                pass
        return f(*args, **kwargs)
    return wrapper

def redirect_if_admin(f):
    @wraps(f)
    @require_login_page
    def wrapper(*args, **kwargs):
        path = request.path
        admin_path = None

        if g.user.get('role') == 'admin':
            if path == '/user':
                admin_path = '/admin'
            elif path.startswith('/user/'):
                admin_path = '/admin' + path[len('/user'):]

        if admin_path is not None:
            query = request.query_string.decode('utf-8')
            if query:
                admin_path += '?' + query
            return redirect(admin_path)
        
        return f(*args, **kwargs)
    return wrapper