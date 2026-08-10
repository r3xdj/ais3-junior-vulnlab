from flask import Blueprint, render_template, g, request, jsonify
import requests
from decorators import require_login, require_admin

panel_bp = Blueprint('panel', __name__)

@panel_bp.route('/panel')
@require_login
def panel():
    if g.user.get('role') == 'admin':
        return render_admin_panel()
    return render_user_panel()

def render_user_panel():
    return render_template('user_panel.html', username=g.user.get('username'))

def render_admin_panel():
    return render_template('admin_panel.html', username=g.user.get('username'))

@panel_bp.route('/admin/fetch-report')
@require_admin
def fetch_report():
    """
    包裝成「管理員抓取內部報表/健康檢查資料」的功能,
    實際上是 SSRF 入口 —— 銜接 internal-services 攻擊面
    """
    target = request.args.get('url')
    if not target:
        return jsonify({"error": "Missing url parameter"}), 400

    # 半防護,故意留繞過空間(依你想要的難度調整)
    if '169.254.169.254' in target:
        return jsonify({"error": "Blocked target"}), 403

    try:
        r = requests.get(target, timeout=3)
        return jsonify({"status": r.status_code, "body": r.text[:2000]})
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500