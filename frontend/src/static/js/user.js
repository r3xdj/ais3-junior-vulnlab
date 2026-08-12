const EXAM_TYPE_LABELS = {
    web: 'Web 安全與滲透測試組',
    pwn: '二進位系統安全 (Pwn) 組',
    crypto: '密碼學與資安應用組'
};

async function loadProfile() {
    const emailInput = document.getElementById('email');
    const nameInput = document.getElementById('display_name');
    if (!emailInput || !nameInput) return;

    const res = await fetch(apiUrl('/api/user/profile'), { credentials: 'include' });
    if (!res.ok) { window.location.href = '/login'; return; }
    const user = await res.json();
    emailInput.value = user.email || '';
    nameInput.value = user.display_name || '';

    const examTypeInput = document.getElementById('exam_type');
    if (examTypeInput) {
        examTypeInput.value = user.exam_type ? (EXAM_TYPE_LABELS[user.exam_type] || user.exam_type) : '未設定';
    }
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
    if (res.ok) await loadProfile();
});

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

window.addEventListener('DOMContentLoaded', async () => {
    if (document.getElementById('profileForm')) await loadProfile();
    if (document.getElementById('activityList')) await loadActivity();
});

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
    if (res.ok) {
        e.target.reset();
        await fetch(apiUrl('/api/logout'), { method: 'POST', credentials: 'include' });
        setTimeout(() => { window.location.href = '/login'; }, 1500);
    }
});

async function loadCertificate() {
    const button = document.getElementById('certificateDownloadBtn');
    const summary = document.getElementById('certificateSummary');
    if (!button || !summary) return;

    const res = await fetch(apiUrl('/api/user/certificate'), { credentials: 'include' });
    if (!res.ok) {
        button.disabled = true;
        button.textContent = '無法取得狀態';
        return;
    }
    const data = await res.json();
    if (data.issued) {
        summary.textContent = `已核發｜平均 ${data.average_score}｜${data.grade}`;
        button.disabled = false;
        button.textContent = '下載證書 PDF';
        button.onclick = () => { window.location.href = apiUrl('/api/user/certificate/download'); };
    } else if (data.status === 'pending') {
        summary.textContent = '管理員已核發，證書 PDF 正在產生中。';
        button.disabled = true;
        button.textContent = '產生中...';
        setTimeout(loadCertificate, 3000);
    } else if (data.status === 'failed') {
        summary.textContent = '證書產生失敗，請聯絡管理員。';
        button.disabled = true;
        button.textContent = '無法下載';
    } else {
        summary.textContent = '尚未核發證書。';
        button.disabled = true;
        button.textContent = '尚未取得';
    }
}

window.addEventListener('DOMContentLoaded', loadCertificate);
