// 顯示右上角目前登入者名稱 + 角色,所有登入後頁面共用
window.addEventListener('DOMContentLoaded', async () => {
    const label = document.getElementById('usernameLabel');
    if (!label) return; // 該頁面沒有這個元素(例如行銷頁)就跳過

    try {
        const res = await fetch(apiUrl('/api/me'), { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();
        label.textContent = `${data.username} (${data.role})`;
    } catch (err) {
        // 靜默失敗即可,不影響頁面其他功能
    }
});