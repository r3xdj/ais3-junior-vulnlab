// ---------- Profile 頁 ----------
async function loadProfile() {
    const res = await fetch(apiUrl('/api/user/profile'), { credentials: 'include' });
    if (!res.ok) { window.location.href = '/login'; return; }
    const user = await res.json();
    document.getElementById('email').value = user.email || '';
    document.getElementById('display_name').value = user.display_name || '';
}

document.getElementById('profileForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msgBox = document.getElementById('msgBox');
    const res = await fetch(apiUrl('/api/user/profile'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
            email: document.getElementById('email').value,
            display_name: document.getElementById('display_name').value
        })
    });
    const data = await res.json();
    if (msgBox) msgBox.textContent = res.ok ? '已儲存' : (data.error || '更新失敗');
});

if (document.getElementById('profileForm')) loadProfile();


// ---------- Activity 頁 ----------
async function loadActivity() {
    const list = document.getElementById('activityList');
    if (!list) return;

    const res = await fetch(apiUrl('/api/user/activity'), { credentials: 'include' });
    if (!res.ok) { window.location.href = '/login'; return; }
    const logs = await res.json();

    list.innerHTML = logs.length
        ? logs.map(l => `<li class="list-group-item d-flex justify-content-between">
                <span>${l.action}</span>
                <span class="text-muted small">${l.created_at}</span>
              </li>`).join('')
        : '<li class="list-group-item text-muted">尚無活動紀錄</li>';
}
loadActivity();


// ---------- Change Password 頁 ----------
document.getElementById('passwordForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msgBox = document.getElementById('msgBox');
    const oldPw = document.getElementById('old_password').value;
    const newPw = document.getElementById('new_password').value;
    const newPw2 = document.getElementById('new_password_confirm').value;

    if (newPw !== newPw2) {
        if (msgBox) msgBox.textContent = '兩次輸入的新密碼不一致';
        return;
    }

    const form = new FormData();
    form.append('old_password', oldPw);
    form.append('new_password', newPw);

    const res = await fetch(apiUrl('/api/user/change-password'), {
        method: 'POST',
        body: form,
        credentials: 'include'
    });
    const data = await res.json();
    if (msgBox) msgBox.textContent = res.ok ? '密碼已更新，請重新登入' : (data.error || '更新失敗');
    if (res.ok) setTimeout(() => { window.location.href = '/login'; }, 1500);
});