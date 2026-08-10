from flask import Blueprint, render_template, g
from decorators import require_login

panel_bp = Blueprint('panel', __name__)

@panel_bp.route('/panel')
@require_login
def panel():
    if g.user.get('role') == 'admin': return render_template('admin/dashboard.html', username=g.user.get('username'))
    return render_template('user/dashboard.html', username=g.user.get('username'))