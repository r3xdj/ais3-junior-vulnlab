// 統一管理 API base URL,開發模式(frontend 獨立跑在 3000)跟正式環境(經 Apache 反代)自動切換
const API_BASE = (window.location.port === '3000')
    ? 'http://localhost:5000'
    : '';

function apiUrl(path) {
    return `${API_BASE}${path}`;
}