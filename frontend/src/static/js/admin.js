// ---------- Report Viewer ----------
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


// ---------- Users 管理頁 ----------
async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;

    const res = await fetch(apiUrl('/api/admin/users'), { credentials: 'include' });
    if (res.status === 403) {
        document.body.innerHTML = '<div class="container py-5 text-center"><h1>403</h1><p>沒有權限存取此頁面</p></div>';
        return;
    }
    const users = await res.json();

    tbody.innerHTML = users.map(u => `
        <tr>
            <td>${u.id}</td>
            <td>${u.username}</td>
            <td>${u.role}</td>
            <td>${u.created_at}</td>
        </tr>
    `).join('');
}
loadUsers();