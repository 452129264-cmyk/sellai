async function apiCall(path, options = {}) {
    const url = CONFIG.API_BASE + path;
    try {
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error('[API]', url, e);
        return null;
    }
}

async function loadOpportunities() {
    const data = await apiCall('/opportunities?min_margin=30&limit=20');
    return data;
}

async function loadAvatars() {
    const data = await apiCall('/avatars');
    return data;
}

async function sendMessage(avatarId, content) {
    return await apiCall(`/avatars/${avatarId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content }),
    });
}
