from flask import Flask, render_template, redirect
from decorators import require_login_page, require_admin_page, redirect_if_logged_in

app = Flask(__name__)

# ---- 公開行銷頁面 ----
@app.route('/')
def index():
    return render_template('public/index.html')

@app.route('/about')
def about():
    return render_template('public/about.html')

# ---- 認證頁面(畫面殼,邏輯打 web-gateway 的 API)----
@app.route('/login')
@redirect_if_logged_in
def login_page():
    return render_template('public/login.html')

@app.route('/register')
@redirect_if_logged_in
def register_page():
    return render_template('public/register.html')

# ---- 登入後導流(前端路由層,只影響 UX,不是安全邊界)----
@app.route('/panel')
def panel():
    return render_template('panel_redirect.html')  # 頁面內 JS 打 /api/me 決定導去哪

from decorators import require_login_page, require_admin_page

# ---- Admin 頁面殼 ----
@app.route('/admin/dashboard')
@require_admin_page
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/reports')
@require_admin_page
def admin_reports():
    return render_template('admin/reports.html')

@app.route('/admin/manage-users')
@require_admin_page
def admin_users():
    return render_template('admin/users.html')

@app.route('/admin/profile')
@require_admin_page
def admin_profile():
    return render_template('admin/profile.html')

@app.route('/admin/activity')
@require_admin_page
def admin_activity():
    return render_template('admin/activity.html')

@app.route('/admin/change-password')
@require_admin_page
def admin_password():
    return render_template('admin/password.html')

# ---- User 頁面殼,一般登入即可(admin 也能用,前面討論過)----
@app.route('/user/dashboard')
@require_login_page
def user_dashboard():
    return render_template('user/dashboard.html')

@app.route('/user/profile')
@require_login_page
def user_profile():
    return render_template('user/profile.html')

@app.route('/user/activity')
@require_login_page
def user_activity():
    return render_template('user/activity.html')

@app.route('/user/change-password')
@require_login_page
def user_password():
    return render_template('user/password.html')

# ---- rickroll ----
@app.route('/robots.txt')
def robots_txt():
    return redirect('https://youtu.be/-so1CRzBB7s', code=302)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)