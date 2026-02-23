/**
 * API client for the admin backend.
 * Sends Telegram init data as auth header.
 */

const API_BASE = '/admin';

function getInitData() {
    try {
        return window.Telegram?.WebApp?.initData || '';
    } catch {
        return '';
    }
}

async function request(path, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': getInitData(),
        'X-Admin-Password': localStorage.getItem('admin_password') || '',
        ...options.headers,
    };

    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(error.detail || `HTTP ${res.status}`);
    }

    return res.json();
}

export const api = {
    // Dashboard
    getMe: () => request('/me'),
    getDashboard: (from, to) => {
        const params = new URLSearchParams();
        if (from) params.set('from_date', from);
        if (to) params.set('to_date', to);
        return request(`/dashboard?${params}`);
    },

    // Users
    getUsers: (search = '', offset = 0) =>
        request(`/users?search=${encodeURIComponent(search)}&offset=${offset}&limit=50`),
    getUser: (id) => request(`/users/${id}`),

    // Entries
    getEntries: (filters = {}) => {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
        return request(`/entries?${params}`);
    },

    // Events
    getEvents: (filters = {}) => {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
        return request(`/events?${params}`);
    },

    // Settings
    getSettings: () => request('/settings'),
    updateProviders: (data) => request('/settings/providers', { method: 'POST', body: JSON.stringify(data) }),
    updateSecrets: (data) => request('/settings/secrets', { method: 'POST', body: JSON.stringify(data) }),
    updatePrompts: (data) => request('/settings/prompts', { method: 'POST', body: JSON.stringify(data) }),

    // Plans
    getPlans: () => request('/plans'),
    upsertPlan: (data) => request('/plans', { method: 'POST', body: JSON.stringify(data) }),

    // Management
    createUser: (data) => request('/users', { method: 'POST', body: JSON.stringify(data) }),
    updateUser: (id, data) => request(`/users/${id}`, { method: 'POST', body: JSON.stringify(data) }),
    topUpUser: (id, amount) => request(`/users/${id}/topup`, { method: 'POST', body: JSON.stringify({ amount }) }),
    updateUserLimits: (id, limits) => request(`/users/${id}/limits`, { method: 'POST', body: JSON.stringify(limits) }),
    sendUserMessage: (id, text) => request(`/users/${id}/message`, { method: 'POST', body: JSON.stringify({ text }) }),
    summarizeWeek: (id) => request(`/users/${id}/summarize-week`, { method: 'POST' }),
    broadcastMessage: (text) => request('/broadcast', { method: 'POST', body: JSON.stringify({ text }) }),

    getEntries: (params) => request(`/entries?${new URLSearchParams(params)}`),
    createEntry: (data) => request('/entries', { method: 'POST', body: JSON.stringify(data) }),
    updateEntry: (id, data) => request(`/entries/${id}`, { method: 'POST', body: JSON.stringify(data) }),
    deleteEntry: (id) => request(`/entries/${id}`, { method: 'DELETE' }),

    getPayments: (params = {}) => {
        const p = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => { if (v) p.set(k, v); });
        return request(`/payments?${p}`);
    },

    getAffiliateStats: () => request('/affiliate/stats'),
    updateAffiliateSettings: (data) => request('/settings/affiliate', { method: 'POST', body: JSON.stringify(data) }),
    updatePaymentSettings: (data) => request('/settings/payments', { method: 'POST', body: JSON.stringify(data) }),
};
