async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;

    const res = await fetch(apiUrl('/api/admin/users'), { credentials: 'include' });
    if (res.status === 403) {
        document.body.innerHTML = '<div class="container py-5 text-center"><h1>403</h1><p>沒有權限存取此頁面</p></div>';
        return;
    }

    const users = await res.json();
    const totalUsers = document.getElementById('totalUsers');
    const adminUsers = document.getElementById('adminUsers');
    if (totalUsers) totalUsers.textContent = users.length;
    if (adminUsers) adminUsers.textContent = users.filter(u => u.role === 'admin').length;

    tbody.innerHTML = users.map(u => `
        <tr>
            <td>${u.id}</td>
            <td>${u.username}</td>
            <td>${u.role}</td>
            <td>${u.email || '-'}</td>
            <td>${u.created_at || '-'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" data-role-action data-user-id="${u.id}" data-role="${u.role === 'admin' ? 'user' : 'admin'}">
                    ${u.role === 'admin' ? '降為一般使用者' : '設為 admin'}
                </button>
            </td>
        </tr>
    `).join('');
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
    const btn = e.target.closest('[data-role-action]');
    if (!btn) return;

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
    loadUsers();
});