async function loadDashboardStats() {
    const totalUsers = document.getElementById('totalUsers');
    const adminUsers = document.getElementById('adminUsers');

    if (!totalUsers && !adminUsers) return;

    try {
        const res = await fetch(apiUrl('/api/admin/users'), {
            credentials: 'include'
        });

        if (!res.ok) {
            console.error('Failed to load users:', res.status);
            return;
        }

        const users = await res.json();

        if (totalUsers) {
            totalUsers.textContent = users.length;
        }

        if (adminUsers) {
            adminUsers.textContent =
                users.filter(user => user.role === 'admin').length;
        }
    } catch (err) {
        console.error('Failed to load dashboard stats:', err);
    }
}

async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;

    const res = await fetch(apiUrl('/api/admin/users'), { credentials: 'include' });
    if (res.status === 403) {
        document.body.innerHTML = '<div class="container py-5 text-center"><h1>403</h1><p>沒有權限存取此頁面</p></div>';
        return;
    }

    const users = await res.json();

    window.__users = users;
    tbody.innerHTML = users.map(u => {
        const certStatus = u.certificate_status === 'issued'
            ? `<span class="badge text-bg-success">已核發 ${u.certificate_grade || ''}</span>`
            : u.certificate_status === 'pending'
                ? '<span class="badge text-bg-warning">產生中</span>'
                : u.certificate_status === 'failed'
                    ? '<span class="badge text-bg-danger">產生失敗</span>'
                    : '<span class="text-muted">尚未核發</span>';
        const certAction = u.role === 'user'
            ? `<button class="btn btn-sm btn-outline-success" data-certificate-action data-user-id="${u.id}">登記成績 / 核發</button>`
            : '<span class="text-muted">管理員不可核發</span>';
        return `
        <tr>
            <td>${u.id}</td>
            <td>${u.username}</td>
            <td>${u.role}</td>
            <td>${u.email || '-'}</td>
            <td>${u.created_at || '-'}</td>
            <td>${certStatus}</td>
            <td>
                ${certAction}
                <button class="btn btn-sm btn-outline-primary ms-1" data-role-action data-user-id="${u.id}" data-role="${u.role === 'admin' ? 'user' : 'admin'}">
                    ${u.role === 'admin' ? '降為一般使用者' : '設為 admin'}
                </button>
            </td>
        </tr>`;
    }).join('');
}

function openCertificateModal(user) {
    document.getElementById('certificateUserId').value = user.id;
    document.getElementById('certificateUserName').textContent = user.display_name || user.username;
    const scores = user.certificate_scores || {};
    ['web', 'pwn', 'crypto', 'reverse', 'forensics'].forEach(key => {
        document.getElementById(`score_${key}`).value = scores[key] ?? '';
    });
    bootstrap.Modal.getOrCreateInstance(document.getElementById('certificateModal')).show();
}

async function submitCertificate(event) {
    event.preventDefault();
    const userId = document.getElementById('certificateUserId').value;
    const scores = {};
    for (const key of ['web', 'pwn', 'crypto', 'reverse', 'forensics']) {
        const score = Number(document.getElementById(`score_${key}`).value);
        if (!Number.isFinite(score) || score < 0 || score > 100) {
            alert('所有成績都必須是 0 到 100 的數字。');
            return;
        }
        scores[key] = score;
    }

    const res = await fetch(apiUrl(`/api/admin/users/${userId}/certificate`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ scores })
    });
    const data = await res.json();
    if (!res.ok) {
        alert(data.error || '證書核發失敗');
        return;
    }
    bootstrap.Modal.getOrCreateInstance(document.getElementById('certificateModal')).hide();
    alert(`成績已登記，證書正在產生中（${data.certificate.grade}）。`);
    await loadUsers();
}

document.getElementById('fetchForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = document.getElementById('urlInput').value;
    const result = document.getElementById('result');
    result.textContent = '載入中...';

    try {
        const res = await fetch(apiUrl(`/api/admin/fetch-report?url=${encodeURIComponent(url)}`), {
            credentials: 'include'
        });
        const data = await res.json();
        result.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
        result.textContent = '請求失敗';
    }
});

document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-certificate-action], [data-role-action]');
    if (!btn) return;

    if (btn.hasAttribute('data-certificate-action')) {
        const user = (window.__users || []).find(u => String(u.id) === btn.getAttribute('data-user-id'));
        if (user) openCertificateModal(user);
        return;
    }

    const userId = btn.getAttribute('data-user-id');
    const nextRole = btn.getAttribute('data-role');

    const res = await fetch(apiUrl(`/api/admin/users/${userId}/role`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ role: nextRole })
    });

    if (res.ok) {
        await loadUsers();
    }
});

window.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadUsers();
    document.getElementById('certificateForm')?.addEventListener('submit', submitCertificate);
});
