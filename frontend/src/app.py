from flask import Flask, render_template

app = Flask(__name__)

# ---- 公開行銷頁面 ----
@app.route('/')
def index():
    return render_template('public/index.html')

@app.route('/product')
def product():
    return render_template('public/product.html')

@app.route('/about')
def about():
    return render_template('public/about.html')

@app.route('/careers')
def careers():
    return render_template('public/careers.html')

@app.route('/blog')
def blog():
    return render_template('public/blog.html')

# ---- 認證頁面(畫面殼,邏輯打 web-gateway 的 API)----
@app.route('/login')
def login_page():
    return render_template('auth/login.html')

@app.route('/register')
def register_page():
    return render_template('auth/register.html')

# ---- 登入後導流(前端路由層,只影響 UX,不是安全邊界)----
@app.route('/panel')
def panel():
    return render_template('user/panel_redirect.html')  # 頁面內 JS 打 /api/me 決定導去哪

# ---- User 頁面殼 ----
@app.route('/user/dashboard')
def user_dashboard():
    return render_template('user/dashboard.html')

@app.route('/user/profile')
def user_profile():
    return render_template('user/profile.html')

@app.route('/user/activity')
def user_activity():
    return render_template('user/activity.html')

@app.route('/user/change-password')
def user_password():
    return render_template('user/password.html')

# ---- Admin 頁面殼 ----
@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/reports')
def admin_reports():
    return render_template('admin/reports.html')

@app.route('/admin/users')
def admin_users():
    return render_template('admin/users.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)