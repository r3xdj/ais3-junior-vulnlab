(async () => {
    try {
        const res = await fetch(apiUrl('/api/me'), { credentials: 'include' });
        if (res.ok) {
            window.location.href = '/panel';
        }
        // 401/其他狀況 → 什麼都不做,留在原頁面讓使用者登入/註冊
    } catch (err) {
        // 網路錯誤也留在原頁面,不影響正常使用
    }
})();

document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorBox = document.getElementById('errorBox');
    if (errorBox) errorBox.textContent = '';

    const res = await fetch(apiUrl('/api/login'), {
        method: 'POST',
        body: new FormData(e.target),
        credentials: 'include'
    });
    const data = await res.json();

    if (!res.ok) {
        if (errorBox) errorBox.textContent = data.error || '登入失敗';
        return;
    }
    window.location.href = '/panel';
});

document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorBox = document.getElementById('errorBox');
    if (errorBox) errorBox.textContent = '';

    const res = await fetch(apiUrl('/api/register'), {
        method: 'POST',
        body: new FormData(e.target),
        credentials: 'include'
    });
    const data = await res.json();

    if (!res.ok) {
        if (errorBox) errorBox.textContent = data.error || '註冊失敗';
        return;
    }
    window.location.href = '/panel';
});

document.getElementById('logoutBtn')?.addEventListener('click', async () => {
    await fetch(apiUrl('/api/logout'), { method: 'POST', credentials: 'include' });
    window.location.href = '/login';
});