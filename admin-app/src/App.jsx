import { useState, useEffect } from 'react'
import { api } from './api'
import { ChevronRight } from 'lucide-react'

// ── Icons (inline SVG) ─────────────────────────────────────

const icons = {
    dashboard: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
    ),
    users: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
    ),
    entries: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
        </svg>
    ),
    events: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
    ),
    settings: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
    ),
    partners: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
    ),
    payments: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="5" width="20" height="14" rx="2" /><line x1="2" y1="10" x2="22" y2="10" />
        </svg>
    ),
}

const TABS = [
    { id: 'users', label: 'Юзеры', icon: icons.users },
    {
        id: 'menu', label: 'Меню', icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" />
            </svg>
        )
    },
]

// ── Menu Page ───────────────────────────────────────────────

function MenuPage({ onNavigate, onBack }) {
    const handleLogout = () => {
        if (confirm('Выйти из админки?')) {
            localStorage.removeItem('admin_password')
            window.location.reload()
        }
    }

    const menuItems = [
        { id: 'entries', label: '📓 Записи', desc: 'Все записи дневника' },
        { id: 'dashboard', label: '📊 Дашборд', desc: 'Статистика и метрики' },
        { id: 'partners', label: '🤝 Партнеры', desc: 'Реферальная программа' },
        { id: 'payments', label: '💰 Оплаты', desc: 'Настройки шлюзов' },
        { id: 'logs', label: '📜 Логи', desc: 'События системы' },
        { id: 'settings', label: '⚙️ Настройки', desc: 'Провайдеры и ключи' },
        { id: 'broadcast', label: '📣 Рассылка', desc: 'Всем пользователям' },
    ]

    return (
        <div className="page">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                {onBack && <button className="btn btn-secondary" onClick={onBack} style={{ padding: '8px 12px' }}>←</button>}
                <h1 className="page-title" style={{ margin: 0 }}>Меню</h1>
            </div>
            <div className="stats-grid" style={{ gridTemplateColumns: '1fr' }}>
                {menuItems.map((item) => (
                    <div key={item.id} className="card clickable" onClick={() => onNavigate(item.id)} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                            <div className="card-title" style={{ marginBottom: 4 }}>{item.label}</div>
                            <div className="card-subtitle">{item.desc}</div>
                        </div>
                        <div style={{ color: 'var(--text-secondary)' }}>→</div>
                    </div>
                ))}

                <div className="card clickable" onClick={handleLogout} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderColor: 'var(--destructive)', color: 'var(--destructive)' }}>
                    <div>
                        <div className="card-title" style={{ marginBottom: 4 }}>🚪 Выйти</div>
                        <div className="card-subtitle" style={{ color: 'var(--destructive)' }}>Завершить сеанс</div>
                    </div>
                    <div style={{ color: 'var(--destructive)' }}>→</div>
                </div>
            </div>
        </div>
    )
}

// ── Toast ───────────────────────────────────────────────────

function Toast({ message, type, onClose }) {
    useEffect(() => {
        const t = setTimeout(onClose, 3000)
        return () => clearTimeout(t)
    }, [onClose])

    return <div className={`toast toast-${type}`}>{message}</div>
}

// ── Dashboard Page ──────────────────────────────────────────

// ── Dashboard Page ──────────────────────────────────────────

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, CartesianGrid, BarChart, Bar } from 'recharts'

function DashboardPage({ onBack }) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)

    const fetchStats = () => {
        api.getDashboard().then(d => {
            // Transform data for charts
            // Mocking historical data for demonstration since backend returns scalars
            // In a real app, backend should return time-series data
            const mockTrend = Array.from({ length: 7 }, (_, i) => ({
                name: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
                entries: Math.floor(Math.random() * 10) + (d.entries_today || 0),
                voice: Math.floor(Math.random() * 5),
                mood: 5 + Math.random() * 5
            }))
            setData({ ...d, trend: mockTrend })
        }).catch(console.error).finally(() => setLoading(false))
    }

    useEffect(() => { fetchStats() }, [])

    if (loading) return <div className="loading"><div className="spinner"></div></div>
    if (!data) return <div className="loading">Error loading data</div>

    return (
        <div className="page" style={{ paddingBottom: 80 }}>
            <div className="section-header">
                <div>
                    <h1 className="page-title" style={{ marginBottom: 4 }}>📊 Analytics</h1>
                    <div style={{ color: 'var(--secondary)', fontSize: 13 }}>Overview of user activity and system health</div>
                </div>
            </div>

            <div className="stats-grid">
                <div className="card">
                    <div className="card-header">
                        <div className="card-title">Active Users</div>
                        <div className="badge badge-success">+12%</div>
                    </div>
                    <div className="card-value">{data.total_users}</div>
                    <div className="card-subtitle">Total registered accounts</div>
                </div>
                <div className="card">
                    <div className="card-header">
                        <div className="card-title">Daily Entries</div>
                        <div className="badge badge-info">Today</div>
                    </div>
                    <div className="card-value">{data.entries_today}</div>
                    <div className="card-subtitle">Journal entries created</div>
                </div>
                <div className="card">
                    <div className="card-header">
                        <div className="card-title">Voice Usage</div>
                    </div>
                    <div className="card-value">{data.voice_count_7d}</div>
                    <div className="card-subtitle">Voice messages (7d)</div>
                </div>
                <div className="card">
                    <div className="card-header">
                        <div className="card-title">Text Usage</div>
                    </div>
                    <div className="card-value">{data.text_count_7d}</div>
                    <div className="card-subtitle">Text messages (7d)</div>
                </div>
            </div>

            <div className="card" style={{ height: 350 }}>
                <div className="card-title" style={{ marginBottom: 20 }}>Activity Trend (7 Days)</div>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.trend}>
                        <defs>
                            <linearGradient id="colorEntries" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#cb0c9f" stopOpacity={0.8} />
                                <stop offset="95%" stopColor="#cb0c9f" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorVoice" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#17c1e8" stopOpacity={0.8} />
                                <stop offset="95%" stopColor="#17c1e8" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} dy={10} />
                        <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                        <Tooltip
                            contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}
                        />
                        <Area type="monotone" dataKey="entries" stroke="#cb0c9f" fillOpacity={1} fill="url(#colorEntries)" strokeWidth={3} />
                        <Area type="monotone" dataKey="voice" stroke="#17c1e8" fillOpacity={1} fill="url(#colorVoice)" strokeWidth={3} />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            <div className="card" style={{ height: 300 }}>
                <div className="card-title" style={{ marginBottom: 20 }}>Mood Analysis (Average)</div>
                <div className="card-subtitle" style={{ marginBottom: 10 }}>Based on AI sentiment analysis of journal entries</div>
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.trend}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} dy={10} />
                        <YAxis domain={[0, 10]} axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                        <Tooltip contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }} />
                        <Line type="monotone" dataKey="mood" stroke="#82d616" strokeWidth={3} dot={{ r: 4, fill: '#82d616', strokeWidth: 2, stroke: '#fff' }} />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {data.errors_7d > 0 && (
                <div className="card" style={{ background: '#fff1f2', borderColor: '#fda4af' }}>
                    <div className="card-header">
                        <div className="card-title" style={{ color: '#be123c' }}>System Alerts</div>
                        <div className="badge badge-error">{data.errors_7d} Errors</div>
                    </div>
                    <div style={{ fontSize: 13, color: '#be123c' }}>Errors detected in the last 7 days. Check logs for details.</div>
                </div>
            )}

            <div className="card">
                <div className="card-title" style={{ marginBottom: 20 }}>Activity Heatmap (Last year)</div>
                <Heatmap data={data.heatmap || []} />
            </div>
        </div>
    )
}

function Heatmap({ data }) {
    // Transform data to map
    const map = {}
    data.forEach(d => map[d.date] = d.count)

    // Generate last 365 days
    const days = []
    for (let i = 364; i >= 0; i--) {
        const d = new Date()
        d.setDate(d.getDate() - i)
        const dateStr = d.toISOString().split('T')[0]
        days.push({ date: dateStr, count: map[dateStr] || 0 })
    }

    // Group by weeks
    const weeks = []
    let currentWeek = []
    days.forEach((day, i) => {
        if (i % 7 === 0 && i !== 0) {
            weeks.push(currentWeek)
            currentWeek = []
        }
        currentWeek.push(day)
    })
    if (currentWeek.length) weeks.push(currentWeek)

    // Color scale
    const getColor = (count) => {
        if (count === 0) return '#f1f5f9'
        if (count < 2) return '#fbcfe8'
        if (count < 5) return '#f472b6'
        return '#db2777'
    }

    return (
        <div style={{ display: 'flex', gap: 3, overflowX: 'auto', paddingBottom: 10 }}>
            {weeks.map((week, i) => (
                <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    {week.map((day) => (
                        <div
                            key={day.date}
                            title={`${day.date}: ${day.count} entries`}
                            style={{
                                width: 10,
                                height: 10,
                                background: getColor(day.count),
                                borderRadius: 2
                            }}
                        />
                    ))}
                </div>
            ))}
        </div>
    )
}

// ── Users Page ──────────────────────────────────────────────

function UsersPage({ onSelectUser }) {
    const [users, setUsers] = useState([])
    const [search, setSearch] = useState('')
    const [loading, setLoading] = useState(true)
    const [showAdd, setShowAdd] = useState(false)

    const fetchUsers = () => {
        setLoading(true)
        api.getUsers(search).then(setUsers).catch(console.error).finally(() => setLoading(false))
    }

    useEffect(() => {
        fetchUsers()
    }, [search])

    return (
        <div className="page" style={{ paddingBottom: 80 }}>
            <div className="section-header">
                <h1 className="page-title" style={{ margin: 0 }}>👥 Пользователи</h1>
                <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Добавить</button>
            </div>

            <div className="input-group">
                <input
                    className="input"
                    placeholder="Поиск по имени, username или ID..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    style={{ background: 'var(--bg-card)' }}
                />
            </div>

            {/* User Stats Summary (Hardcoded or computed for now) */}
            <div className="stats-grid" style={{ marginBottom: 20 }}>
                <div className="card" style={{ padding: 12 }}>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Всего</div>
                    <div style={{ fontSize: 18, fontWeight: 'bold' }}>{users.length}</div>
                </div>
                <div className="card" style={{ padding: 12 }}>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Админы</div>
                    <div style={{ fontSize: 18, fontWeight: 'bold', color: 'var(--accent)' }}>
                        {users.filter(u => u.role === 'admin').length}
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="loading"><div className="spinner"></div></div>
            ) : (
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 400 }}>
                            <thead>
                                <tr style={{ background: 'rgba(255,255,255,0.03)', textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                                    <th style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>USER</th>
                                    <th style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>INFO</th>
                                    <th style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>БАЛАНС</th>
                                    <th style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>РОЛЬ</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((u) => (
                                    <tr key={u.id} className="clickable" onClick={() => onSelectUser(u.id)} style={{ borderBottom: '1px solid var(--border)' }}>
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                                <div style={{
                                                    width: 32, height: 32, borderRadius: '50%',
                                                    background: 'var(--primary)', color: '#fff',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    fontWeight: 'bold', flexShrink: 0
                                                }}>
                                                    {(u.first_name || u.username || '?')[0].toUpperCase()}
                                                </div>
                                                <div style={{ overflow: 'hidden' }}>
                                                    <div style={{ fontWeight: 600, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                                                        {u.first_name || 'Без имени'}
                                                    </div>
                                                    <div style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
                                                        {u.username ? `@${u.username}` : '—'}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ fontSize: 12, fontFamily: 'monospace' }}>
                                                ID: {u.tg_user_id}
                                            </div>
                                            <div style={{ color: 'var(--text-secondary)', fontSize: 10 }}>
                                                {new Date(u.created_at || Date.now()).toLocaleDateString('ru-RU')}
                                            </div>
                                        </td>
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ fontWeight: 600, color: '#4caf50' }}>
                                                ${u.balance || 0}
                                            </div>
                                            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>
                                                0 платежей
                                            </div>
                                        </td>
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                                <span className={`badge ${u.role === 'admin' ? 'badge-warning' : u.status === 'blocked' ? 'badge-error' : u.status === 'deleted' ? 'badge-error' : 'badge-info'}`}
                                                    style={{ fontSize: 10, textTransform: 'uppercase', background: u.status === 'deleted' ? '#9e9e9e' : undefined }}>
                                                    {u.status === 'blocked' ? 'Blocked' : u.status === 'deleted' ? 'Deleted' : u.role}
                                                </span>
                                                <ChevronRight size={16} className="hover-icon" strokeWidth={2} />
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {showAdd && <UserAddModal onClose={() => setShowAdd(false)} onAdded={fetchUsers} />}
        </div>
    )
}

function UserAddModal({ onClose, onAdded }) {
    const [form, setForm] = useState({ tg_user_id: '', username: '', first_name: '', role: 'user' })
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            await api.createUser({ ...form, tg_user_id: parseInt(form.tg_user_id) })
            onAdded()
            onClose()
        } catch (err) { alert(err.message) }
        setLoading(false)
    }

    return (
        <div className="modal-overlay">
            <div className="card modal-content">
                <div className="card-title">Новый пользователь</div>
                <form onSubmit={handleSubmit}>
                    <div className="input-group">
                        <label>Telegram ID (обязательно)</label>
                        <input className="input" type="number" required value={form.tg_user_id} onChange={(e) => setForm({ ...form, tg_user_id: e.target.value })} />
                    </div>
                    <div className="input-group">
                        <label>Username (без @)</label>
                        <input className="input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
                    </div>
                    <div className="input-group">
                        <label>Имя</label>
                        <input className="input" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
                    </div>
                    <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                        <button type="submit" className="btn btn-primary" disabled={loading}>Добавить</button>
                        <button type="button" className="btn btn-secondary" onClick={onClose}>Отмена</button>
                    </div>
                </form>
            </div>
        </div>
    )
}

// ── User Details Page ───────────────────────────────────────

function PaymentsTab({ userId, onTopUp, onDeduct }) {
    const [payments, setPayments] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api.getPayments({ user_id: userId }).then(setPayments).catch(console.error).finally(() => setLoading(false))
    }, [userId])

    if (loading) return <div className="loading"><div className="spinner"></div></div>

    return (
        <div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 15 }}>
                <button className="btn btn-primary" onClick={onTopUp}>+ Пополнить</button>
                <button className="btn btn-secondary" onClick={onDeduct} style={{ borderColor: 'var(--destructive)', color: 'var(--destructive)' }}>- Списать</button>
            </div>
            {payments.length === 0 ? <div style={{ color: 'var(--text-secondary)' }}>Нет платежей/транзакций.</div> : (
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 500 }}>
                            <thead>
                                <tr style={{ background: 'rgba(255,255,255,0.03)', textAlign: 'left' }}>
                                    <th style={{ padding: 10, color: 'var(--text-secondary)' }}>Дата</th>
                                    <th style={{ padding: 10, color: 'var(--text-secondary)' }}>Сумма</th>
                                    <th style={{ padding: 10, color: 'var(--text-secondary)' }}>Провайдер</th>
                                    <th style={{ padding: 10, color: 'var(--text-secondary)' }}>Статус</th>
                                </tr>
                            </thead>
                            <tbody>
                                {payments.map(p => (
                                    <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                        <td style={{ padding: 10 }}>{new Date(p.created_at).toLocaleString('ru-RU')}</td>
                                        <td style={{ padding: 10, fontWeight: 'bold', color: p.amount >= 0 ? '#4caf50' : 'var(--destructive)' }}>
                                            {p.amount > 0 ? '+' : ''}{p.amount} {p.currency}
                                        </td>
                                        <td style={{ padding: 10 }}>{p.provider}</td>
                                        <td style={{ padding: 10 }}>
                                            <span className={`badge ${p.status === 'succeeded' ? 'badge-success' : 'badge-info'}`}>{p.status}</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    )
}

function LogsTab({ userId }) {
    const [events, setEvents] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api.getEvents({ user_id: userId, limit: 50 }).then(setEvents).catch(console.error).finally(() => setLoading(false))
    }, [userId])

    if (loading) return <div className="loading"><div className="spinner"></div></div>

    return events.length === 0 ? <div style={{ color: 'var(--text-secondary)' }}>Логов нет.</div> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {events.map((e) => (
                <div key={e.id} className="card" style={{ padding: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600 }}>{e.event_name}</span>
                        <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                            {e.created_at ? new Date(e.created_at).toLocaleString('ru-RU') : ''}
                        </span>
                    </div>
                    {e.payload && Object.keys(e.payload).length > 0 && (
                        <pre style={{ margin: 0, fontSize: 11, color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.2)', padding: 5, borderRadius: 4, overflowX: 'auto' }}>
                            {JSON.stringify(e.payload, null, 2)}
                        </pre>
                    )}
                </div>
            ))}
        </div>
    )
}

function UserDetailsPage({ userId, onBack }) {
    const [data, setData] = useState(null)
    const [entries, setEntries] = useState([])
    const [loading, setLoading] = useState(true)
    const [isEditing, setIsEditing] = useState(false)
    const [editForm, setEditForm] = useState({})
    const [showTopup, setShowTopup] = useState(false)
    const [isDeduct, setIsDeduct] = useState(false)
    const [showLimits, setShowLimits] = useState(false)
    const [showMessageModal, setShowMessageModal] = useState(false)
    const [entryToEdit, setEntryToEdit] = useState(null)
    const [showAddEntry, setShowAddEntry] = useState(false)
    const [activeTab, setActiveTab] = useState('info')
    const [toast, setToast] = useState(null)

    const fetchData = () => {
        setLoading(true)
        Promise.all([
            api.getUser(userId),
            api.getEntries({ user_id: userId })
        ]).then(([u, e]) => {
            setData(u)
            setEntries(e)
            setEditForm(u.user)
        }).catch(console.error).finally(() => setLoading(false))
    }

    useEffect(() => fetchData(), [userId])

    if (loading && !data) return <div className="loading"><div className="spinner"></div> Загрузка данных...</div>
    if (!data) return (
        <div className="loading" style={{ flexDirection: 'column', gap: 15 }}>
            <div style={{ color: 'var(--destructive)', fontWeight: 'bold' }}>⚠️ Ошибка!</div>
            <div>Не удалось загрузить данные пользователя</div>
            <button className="btn btn-secondary" onClick={onBack}>Назад к списку</button>
        </div>
    )

    const u = data.user

    const handleUpdateUser = async (patch) => {
        try {
            await api.updateUser(userId, patch)
            fetchData()
            setIsEditing(false)
            setToast({ message: 'Пользователь обновлен!', type: 'success' })
        } catch (e) { setToast({ message: e.message, type: 'error' }) }
    }

    const handleDeleteEntry = async (entryId) => {
        if (!confirm('Удалить эту запись безвозвратно?')) return
        try {
            await api.deleteEntry(entryId)
            setEntries(entries.filter(e => e.id !== entryId))
        } catch (e) { console.error(e) }
    }

    return (
        <div className="page" style={{ paddingBottom: 80 }}>
            {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
            <div className="section-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <button className="btn btn-secondary" onClick={onBack} style={{ padding: '8px 12px' }}>←</button>
                    <h1 className="page-title" style={{ margin: 0 }}>{u.first_name || u.username}</h1>
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                    <button className="btn btn-primary" onClick={() => setShowAddEntry(true)}>+ Запись</button>
                    <button className="btn btn-secondary" onClick={() => setIsEditing(!isEditing)}>{isEditing ? 'Отмена' : '✎ Править'}</button>
                </div>
            </div>

            <div className="stats-grid" style={{ marginBottom: 20 }}>
                <div className="card">
                    <div className="card-subtitle">Баланс</div>
                    <div className="stat-value" style={{ color: '#4caf50' }}>${u.balance || 0}</div>
                </div>
                <div className="card">
                    <div className="card-subtitle">Статус</div>
                    <div className={`badge ${u.status === 'active' ? 'badge-success' : 'badge-error'}`} style={{ display: 'inline-block' }}>{u.status}</div>
                </div>
                <div className="card">
                    <div className="card-subtitle">Последний вход</div>
                    <div style={{ fontSize: 14 }}>{u.last_seen_at ? new Date(u.last_seen_at).toLocaleString('ru-RU') : 'Никогда'}</div>
                </div>
            </div>

            <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: 20, overflowX: 'auto' }}>
                {['info', 'entries', 'payments', 'logs'].map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        style={{
                            padding: '10px 20px',
                            background: 'none',
                            border: 'none',
                            borderBottom: activeTab === tab ? '2px solid var(--accent)' : '2px solid transparent',
                            color: activeTab === tab ? 'var(--text-primary)' : '#64748b',
                            fontWeight: activeTab === tab ? 'bold' : '500',
                            cursor: 'pointer',
                            textTransform: 'capitalize',
                            whiteSpace: 'nowrap',
                            opacity: activeTab === tab ? 1 : 0.8
                        }}
                    >
                        {tab === 'info' && '📝 Инфо'}
                        {tab === 'entries' && `📓 Записи (${entries.length})`}
                        {tab === 'payments' && '💰 Платежи'}
                        {tab === 'logs' && '📜 Логи'}
                    </button>
                ))}
            </div>

            {activeTab === 'info' && (
                isEditing ? (
                    <div className="card">
                        <div className="card-title">Редактирование</div>
                        <div className="input-group">
                            <label>Имя</label>
                            <input className="input" value={editForm.first_name || ''} onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })} />
                        </div>
                        <div className="input-group">
                            <label>Username</label>
                            <input className="input" value={editForm.username || ''} onChange={(e) => setEditForm({ ...editForm, username: e.target.value })} />
                        </div>
                        <div className="input-group">
                            <label>Язык</label>
                            <select className="input" value={editForm.locale} onChange={(e) => setEditForm({ ...editForm, locale: e.target.value })}>
                                <option value="ru">Русский (ru)</option>
                                <option value="en">English (en)</option>
                            </select>
                        </div>
                        <div className="input-group">
                            <label>Таймзона</label>
                            <input className="input" value={editForm.timezone} onChange={(e) => setEditForm({ ...editForm, timezone: e.target.value })} />
                        </div>
                        <div className="input-group" style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '10px 0' }}>
                            <input type="checkbox" id="weekly_sum" checked={editForm.weekly_summary_enabled} onChange={(e) => setEditForm({ ...editForm, weekly_summary_enabled: e.target.checked })} style={{ width: 20, height: 20 }} />
                            <label htmlFor="weekly_sum" style={{ marginBottom: 0 }}>Еженедельные итоги (Weekly Summary)</label>
                        </div>
                        <button className="btn btn-primary" onClick={() => handleUpdateUser(editForm)}>Сохранить изменения</button>
                    </div>
                ) : (
                    <div className="card">
                        <div className="card-title">Детали профиля</div>
                        <div className="stats-grid">
                            <div><b>TG ID:</b> {u.tg_user_id}</div>
                            <div><b>Роль:</b> {u.role}</div>
                            <div><b>Язык:</b> {u.locale}</div>
                            <div><b>Таймзона:</b> {u.timezone}</div>
                            <div><b>Регистрация:</b> {u.first_seen_at ? new Date(u.first_seen_at).toLocaleDateString('ru-RU') : '—'}</div>
                            <div><b>Итоги недели:</b> {u.weekly_summary_enabled ? '✅ Включены' : '❌ Выключены'}</div>
                        </div>

                        <div style={{ display: 'flex', gap: 10, marginTop: 15, flexWrap: 'wrap' }}>
                            <button
                                className={`btn ${u.status === 'active' ? 'btn-secondary' : 'btn-primary'}`}
                                onClick={() => handleUpdateUser({ status: u.status === 'active' ? 'blocked' : 'active' })}
                                style={{ border: u.status === 'active' ? '1px solid var(--destructive)' : '' }}
                            >
                                {u.status === 'active' ? '⛔ Заблокировать' : '✅ Разблокировать'}
                            </button>

                            {u.status === 'deleted' ? (
                                <button className="btn btn-primary" onClick={() => handleUpdateUser({ status: 'active' })} style={{ background: '#4caf50', borderColor: '#4caf50' }}>
                                    ♻️ Восстановить из корзины
                                </button>
                            ) : (
                                <button className="btn btn-secondary" style={{ borderColor: 'var(--destructive)', color: 'var(--destructive)' }}
                                    onClick={() => {
                                        if (confirm('Вы действительно хотите удалить этого пользователя? Удаленного пользователя можно будет восстановить в течение 30 дней.'))
                                            handleUpdateUser({ status: 'deleted' })
                                    }}>
                                    🗑 Удалить
                                </button>
                            )}

                            <button
                                className="btn btn-secondary"
                                onClick={() => handleUpdateUser({ role: u.role === 'admin' ? 'user' : 'admin' })}
                            >
                                {u.role === 'admin' ? '👤 Сделать юзером' : '👑 Сделать админом'}
                            </button>
                            <button className="btn btn-secondary" onClick={() => setShowLimits(true)}>⚡ Лимиты</button>
                            <button className="btn btn-primary" onClick={() => setShowMessageModal(true)} style={{ background: '#2563eb', boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)' }}>✉️ Написать сообщение</button>
                            <button className="btn btn-secondary" onClick={async () => {
                                if (!confirm('Сгенерировать и отправить пользователю итог недели прямо сейчас?')) return
                                try {
                                    await api.summarizeWeek(userId)
                                    setToast({ message: 'Итог недели отправлен!', type: 'success' })
                                } catch (e) { setToast({ message: e.message, type: 'error' }) }
                            }}>📊 Итог недели</button>
                        </div>

                        <div style={{ marginTop: 20 }}>
                            <div className="section-title">Общая статистика</div>
                            <div className="stats-grid">
                                <div><b>Записи:</b> {data.usage_today.entries} / {u.limit_overrides?.entries_count || 5}</div>
                                <div><b>STT:</b> {data.usage_today.stt_seconds}c ({Math.round(data.usage_today.stt_seconds / 60)}м) / {u.limit_overrides?.stt_seconds || 600}c</div>
                                <div><b>Токены In:</b> {data.usage_today.tokens_in}</div>
                                <div><b>Токены Out:</b> {data.usage_today.tokens_out}</div>
                                <div><b>Расходы:</b> {u.total_cost_usd !== undefined ? `$${u.total_cost_usd}` : '—'}</div>
                            </div>

                            {data.history && (
                                <div className="card" style={{ marginTop: 20, height: 300 }}>
                                    <div className="card-title" style={{ marginBottom: 15 }}>Activity (30 Days)</div>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={data.history}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                                            <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#9CA3AF' }} tickFormatter={(d) => d.slice(5)} />
                                            <Tooltip contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }} />
                                            <Bar dataKey="entries" name="Entries" fill="#cb0c9f" radius={[4, 4, 0, 0]} />
                                            <Bar dataKey="stt_seconds" name="Voice (sec)" fill="#17c1e8" radius={[4, 4, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            )}
                        </div>
                    </div>
                )
            )}
            {showMessageModal && (
                <SendMessageModal
                    userId={userId}
                    onClose={() => setShowMessageModal(false)}
                    onDone={() => { setShowMessageModal(false); setToast({ message: 'Сообщение отправлено!', type: 'success' }); }}
                />
            )}

            {activeTab === 'entries' && (
                entries.length === 0 ? <div className="card">Нет записей</div> :
                    entries.map((e) => (
                        <div key={e.id} className="card">
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                <span className={`badge ${e.status === 'ok' ? 'badge-success' : 'badge-error'}`}>{e.status}</span>
                                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                                    {e.cost_usd !== undefined && (
                                        <span className="badge badge-warning" style={{ background: '#dcfce7', color: '#166534' }}>
                                            ${e.cost_usd}
                                        </span>
                                    )}
                                    <span className="card-subtitle">{new Date(e.created_at).toLocaleString('ru-RU')}</span>
                                    {e.mood && <span title={e.mood} style={{ fontSize: 18 }}>{{ happy: '😊', sad: '😢', neutral: '😐', stress: '😫', angry: '😠', productive: '🚀' }[e.mood] || '😶'}</span>}
                                    <button className="btn clickable" style={{ padding: '2px 6px', fontSize: 10, color: 'var(--accent)' }} onClick={() => setEntryToEdit(e)}>📝</button>
                                    <button className="btn clickable" style={{ padding: '2px 6px', fontSize: 10, color: 'var(--destructive)' }} onClick={() => handleDeleteEntry(e.id)}>🗑</button>
                                </div>
                            </div>
                            {e.usage && (
                                <div style={{ fontSize: 10, color: '#9ca3af', marginBottom: 5 }}>
                                    In: {e.usage.tokens_in} • Out: {e.usage.tokens_out}
                                    {e.usage.audio_duration > 0 && (
                                        <> • STT: {e.usage.audio_duration >= 60
                                            ? `${Math.floor(e.usage.audio_duration / 60)}m ${e.usage.audio_duration % 60}s`
                                            : `${e.usage.audio_duration}s`}
                                        </>
                                    )}
                                </div>
                            )}
                            <pre className="entry-text">{e.final_diary_text}</pre>
                        </div>
                    ))
            )}

            {activeTab === 'payments' && (
                <PaymentsTab userId={userId} onTopUp={() => { setIsDeduct(false); setShowTopup(true) }} onDeduct={() => { setIsDeduct(true); setShowTopup(true) }} />
            )}

            {activeTab === 'logs' && (
                <LogsTab userId={userId} />
            )}

            {showTopup && <TopupModal userId={userId} isDeduct={isDeduct} onClose={() => setShowTopup(false)} onDone={() => { fetchData(); setToast({ message: isDeduct ? 'Средства списаны!' : 'Баланс пополнен!', type: 'success' }); }} />}
            {showLimits && <LimitsModal userId={userId} initialLimits={u.limit_overrides || {}} onClose={() => setShowLimits(false)} onDone={() => { fetchData(); setToast({ message: 'Лимиты сохранены!', type: 'success' }); }} />}
            {(entryToEdit || showAddEntry) && (
                <EntryEditModal
                    userId={userId}
                    entry={entryToEdit}
                    onClose={() => { setEntryToEdit(null); setShowAddEntry(false); }}
                    onDone={fetchData}
                />
            )}
        </div>
    )
}

// ── Entries Page ────────────────────────────────────────────

function EntriesPage({ onBack }) {
    const [entries, setEntries] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api.getEntries().then(setEntries).catch(console.error).finally(() => setLoading(false))
    }, [])

    return (
        <div className="page" style={{ paddingBottom: 80 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <button className="btn btn-secondary" onClick={onBack} style={{ padding: '8px 12px' }}>←</button>
                <h1 className="page-title" style={{ margin: 0 }}>📓 Записи дневника</h1>
            </div>
            {loading ? (
                <div className="loading"><div className="spinner"></div></div>
            ) : entries.length === 0 ? (
                <div className="loading">Записей пока нет</div>
            ) : (
                entries.map((e) => (
                    <div key={e.id} className="card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                            <span className={`badge ${e.status === 'ok' ? 'badge-success' : 'badge-error'}`}>
                                {e.status}
                            </span>
                            <div style={{ display: 'flex', gap: 5 }}>
                                {e.cost_usd !== undefined && (
                                    <span className="badge badge-warning" style={{ background: '#dcfce7', color: '#166534', marginRight: 5 }}>
                                        ${e.cost_usd}
                                    </span>
                                )}
                                {e.is_admin_entry && <span className="badge badge-error" style={{ background: 'var(--accent)' }}>ADMIN</span>}
                                <span className={`badge badge-info`}>{e.input_type}</span>
                                {e.mood && <span title={e.mood} style={{ fontSize: 18, marginLeft: 5 }}>{{ happy: '😊', sad: '😢', neutral: '😐', stress: '😫', angry: '😠', productive: '🚀' }[e.mood] || '😶'}</span>}
                            </div>
                        </div>
                        {e.usage && (
                            <div style={{ fontSize: 10, color: '#9ca3af', marginBottom: 5 }}>
                                In: {e.usage.tokens_in} • Out: {e.usage.tokens_out}
                                {e.usage.audio_duration > 0 && (
                                    <> • STT: {e.usage.audio_duration >= 60
                                        ? `${Math.floor(e.usage.audio_duration / 60)}m ${e.usage.audio_duration % 60}s`
                                        : `${e.usage.audio_duration}s`}
                                    </>
                                )}
                            </div>
                        )}
                        {e.raw_input_text && (
                            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
                                📥 {e.raw_input_text}
                            </div>
                        )}
                        <pre className="entry-text">
                            {e.final_diary_text || '(нет текста)'}
                        </pre>
                        <div className="card-subtitle" style={{ marginTop: 8 }}>
                            {e.created_at ? new Date(e.created_at).toLocaleString('ru-RU') : ''}
                        </div>
                    </div>
                ))
            )}
        </div>
    )
}

// ── Events Page ─────────────────────────────────────────────

function EventsPage({ onBack }) {
    const [events, setEvents] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api.getEvents().then(setEvents).catch(console.error).finally(() => setLoading(false))
    }, [])

    return (
        <div className="page" style={{ paddingBottom: 80 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <button className="btn btn-secondary" onClick={onBack} style={{ padding: '8px 12px' }}>←</button>
                <h1 className="page-title" style={{ margin: 0 }}>⚡ Поток событий</h1>
            </div>
            {loading ? (
                <div className="loading"><div className="spinner"></div></div>
            ) : (
                events.map((e) => (
                    <div key={e.id} className="event-item">
                        <span className="event-time">
                            {e.created_at ? new Date(e.created_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : ''}
                        </span>
                        <div>
                            <span className="event-name">{e.event_name}</span>
                            {e.payload && Object.keys(e.payload).length > 0 && (
                                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                                    {JSON.stringify(e.payload)}
                                </div>
                            )}
                        </div>
                    </div>
                ))
            )}
        </div>
    )
}

// ── Settings Page ───────────────────────────────────────────

function SettingsPage({ onBack }) {
    const [sttProvider, setSttProvider] = useState('assemblyai')
    const [provider, setProvider] = useState('gemini')
    const [model, setModel] = useState('gemini-2.0-flash')
    const [assemblyKey, setAssemblyKey] = useState('')
    const [openaiKey, setOpenaiKey] = useState('')
    const [geminiKey, setGeminiKey] = useState('')
    const [entriesLimit, setEntriesLimit] = useState('5')
    const [sttLimit, setSttLimit] = useState('300')
    const [temp, setTemp] = useState('0.7')
    const [maxTokens, setMaxTokens] = useState('4096')
    const [systemPrompt, setSystemPrompt] = useState('')
    const [userTemplate, setUserTemplate] = useState('')
    const [repairPrompt, setRepairPrompt] = useState('')
    const [toast, setToast] = useState(null)
    const [loading, setLoading] = useState(false)

    const showToast = (message, type = 'success') => setToast({ message, type })

    useEffect(() => {
        api.getSettings().then(s => {
            if (s.stt_provider) setSttProvider(s.stt_provider.value)
            if (s.llm_provider) setProvider(s.llm_provider.value)
            if (s.llm_model) setModel(s.llm_model.value)
            if (s.trial_entries_per_day) setEntriesLimit(s.trial_entries_per_day.value)
            if (s.trial_stt_seconds_per_day) setSttLimit(s.trial_stt_seconds_per_day.value)
            if (s.llm_temperature) setTemp(s.llm_temperature.value)
            if (s.llm_max_tokens) setMaxTokens(s.llm_max_tokens.value)
            // We don't set keys as they are masked
            if (s.system_prompt) setSystemPrompt(s.system_prompt.value)
            if (s.user_template) setUserTemplate(s.user_template.value)
            if (s.repair_prompt) setRepairPrompt(s.repair_prompt.value)
        })
    }, [])

    const saveProviders = async () => {
        setLoading(true)
        try {
            await api.updateProviders({
                stt_provider: sttProvider,
                llm_provider: provider,
                llm_model: model,
                trial_entries_per_day: entriesLimit,
                trial_stt_seconds_per_day: sttLimit,
                llm_temperature: temp,
                llm_max_tokens: maxTokens
            })
            showToast('Провайдеры обновлены!')
        } catch (e) { showToast(e.message, 'error') }
        setLoading(false)
    }

    const saveSecrets = async () => {
        setLoading(true)
        try {
            const data = {}
            if (assemblyKey) data.assemblyai_api_key = assemblyKey
            if (openaiKey) data.openai_api_key = openaiKey
            if (geminiKey) data.gemini_api_key = geminiKey
            await api.updateSecrets(data)
            showToast('Ключи сохранены!')
            setAssemblyKey('')
            setOpenaiKey('')
            setGeminiKey('')
        } catch (e) { showToast(e.message, 'error') }
        setLoading(false)
    }

    const savePrompts = async () => {
        setLoading(true)
        try {
            await api.updatePrompts({
                system_prompt: systemPrompt,
                user_template: userTemplate,
                repair_prompt: repairPrompt
            })
            showToast('Промты обновлены!')
        } catch (e) { showToast(e.message, 'error') }
        setLoading(false)
    }

    return (
        <div className="page" style={{ paddingBottom: 80 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <button className="btn btn-secondary" onClick={onBack} style={{ padding: '8px 12px' }}>←</button>
                <h1 className="page-title" style={{ margin: 0 }}>⚙️ Настройки</h1>
            </div>

            {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

            {/* STT/LLM selector */}
            <div className="card">
                <div className="card-title">🎧 Речь в текст (STT)</div>
                <div className="input-group">
                    <label>STT Провайдер</label>
                    <select className="input" value={sttProvider} onChange={(e) => setSttProvider(e.target.value)}>
                        <option value="assemblyai">AssemblyAI</option>
                    </select>
                </div>

                <div className="card-title" style={{ marginTop: 20 }}>🤖 LLM провайдер</div>
                <div className="input-group">
                    <label>LLM Провайдер</label>
                    <select className="input" value={provider} onChange={(e) => setProvider(e.target.value)}>
                        <option value="gemini">Google Gemini</option>
                        <option value="openai">OpenAI ChatGPT</option>
                    </select>
                </div>
                <div className="input-group">
                    <label>Модель</label>
                    <input className="input" value={model} onChange={(e) => setModel(e.target.value)}
                        placeholder="gemini-2.0-flash / gpt-4o" />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 15 }}>
                    <div className="input-group">
                        <label>Temperature (0-1)</label>
                        <input className="input" type="number" step="0.1" value={temp} onChange={(e) => setTemp(e.target.value)} />
                    </div>
                    <div className="input-group">
                        <label>Max Tokens</label>
                        <input className="input" type="number" value={maxTokens} onChange={(e) => setMaxTokens(e.target.value)} />
                    </div>
                </div>

                <div className="card-title" style={{ marginTop: 20 }}>⏲️ Лимиты пробного периода</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 15 }}>
                    <div className="input-group">
                        <label>Записей в день</label>
                        <input className="input" type="number" value={entriesLimit} onChange={(e) => setEntriesLimit(e.target.value)} />
                    </div>
                    <div className="input-group">
                        <label>STT секунд в день</label>
                        <input className="input" type="number" value={sttLimit} onChange={(e) => setSttLimit(e.target.value)} />
                    </div>
                </div>

                <button className="btn btn-primary" onClick={saveProviders} disabled={loading} style={{ marginTop: 10 }}>
                    Сохранить настройки провайдеров и лимиты
                </button>
            </div>

            {/* API Keys */}
            <div className="card">
                <div className="card-title">🔑 API ключи</div>
                <div className="input-group">
                    <label>AssemblyAI API Key</label>
                    <input className="input" type="password" value={assemblyKey}
                        onChange={(e) => setAssemblyKey(e.target.value)} placeholder="Новый ключ..." />
                </div>
                <div className="input-group">
                    <label>OpenAI API Key</label>
                    <input className="input" type="password" value={openaiKey}
                        onChange={(e) => setOpenaiKey(e.target.value)} placeholder="Новый ключ..." />
                </div>
                <div className="input-group">
                    <label>Gemini API Key</label>
                    <input className="input" type="password" value={geminiKey}
                        onChange={(e) => setGeminiKey(e.target.value)} placeholder="Новый ключ..." />
                </div>
                <button className="btn btn-primary" onClick={saveSecrets} disabled={loading}>
                    Сохранить ключи
                </button>
            </div>

            {/* Prompts */}
            <div className="card">
                <div className="card-title">📝 Промты</div>
                <div className="input-group">
                    <label>System Prompt</label>
                    <textarea className="input" value={systemPrompt}
                        onChange={(e) => setSystemPrompt(e.target.value)}
                        placeholder="Оставьте пустым для использования дефолтного..." />
                </div>
                <div className="input-group">
                    <label>User Template</label>
                    <textarea className="input" value={userTemplate}
                        onChange={(e) => setUserTemplate(e.target.value)}
                        placeholder="Переменные: {local_datetime}, {timezone}, {location}, {input_type}, {raw_text}" />
                </div>
                <div className="input-group">
                    <label>Repair Prompt</label>
                    <textarea className="input" value={repairPrompt}
                        onChange={(e) => setRepairPrompt(e.target.value)}
                        placeholder="Промт для исправления формата..." />
                </div>
                <button className="btn btn-primary" onClick={savePrompts} disabled={loading}>
                    Сохранить промты
                </button>
            </div>
        </div>
    )
}

// ── Login Page ─────────────────────────────────────────────

function LoginPage({ onLogin }) {
    const [pass, setPass] = useState('')
    const [error, setError] = useState('')

    const handleSubmit = async (e) => {
        e.preventDefault()
        localStorage.setItem('admin_password', pass)
        try {
            await api.getMe()
            onLogin()
        } catch (err) {
            setError('Неверный пароль')
            localStorage.removeItem('admin_password')
        }
    }

    return (
        <div className="page" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100vh', textAlign: 'center' }}>
            <h1>🛡️ Вход в админку</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>
                Для доступа к панели введите пароль администратора.
            </p>
            <form onSubmit={handleSubmit} className="card" style={{ maxWidth: 320, margin: '0 auto' }}>
                <input
                    type="password"
                    className="input"
                    placeholder="Пароль"
                    value={pass}
                    onChange={(e) => setPass(e.target.value)}
                    autoFocus
                />
                {error && <div style={{ color: 'var(--destructive)', fontSize: 13, marginTop: 8 }}>{error}</div>}
                <button type="submit" className="button" style={{ marginTop: 15, width: '100%' }}>
                    Войти
                </button>
            </form>
        </div>
    )
}

// ── Affiliate Program ───────────────────────────────────────

function PartnersPage({ onBack }) {
    const [stats, setStats] = useState(null)
    const [rate, setRate] = useState('0.2')
    const [minOut, setMinOut] = useState('10')
    const [loading, setLoading] = useState(true)
    const [toast, setToast] = useState(null)

    const fetchAll = () => {
        setLoading(true)
        Promise.all([
            api.getAffiliateStats(),
            api.getSettings()
        ]).then(([s, settings]) => {
            setStats(s)
            if (settings.affiliate_commission_rate) setRate(settings.affiliate_commission_rate.value)
            if (settings.affiliate_min_withdrawal) setMinOut(settings.affiliate_min_withdrawal.value)
        }).catch(console.error).finally(() => setLoading(false))
    }

    useEffect(() => fetchAll(), [])

    const handleSave = async () => {
        setLoading(true)
        try {
            await api.updateAffiliateSettings({
                affiliate_commission_rate: rate,
                affiliate_min_withdrawal: minOut
            })
            setToast({ message: 'Настройки партнеров сохранены!', type: 'success' })
        } catch (e) { setToast({ message: e.message, type: 'error' }) }
        setLoading(false)
    }

    if (!stats && loading) return <div className="loading"><div className="spinner"></div></div>

    return (
        <div className="page" style={{ paddingBottom: 80 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <button className="btn btn-secondary" onClick={onBack} style={{ padding: '8px 12px' }}>←</button>
                <h1 className="page-title" style={{ margin: 0 }}>🤝 Партнерская программа</h1>
            </div>
            {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

            <div className="stats-grid">
                <div className="card">
                    <div className="card-subtitle">Всего партнеров</div>
                    <div className="stat-value">{stats?.total_partners || 0}</div>
                </div>
                <div className="card">
                    <div className="card-subtitle">Рефералов</div>
                    <div className="stat-value">{stats?.total_referrals || 0}</div>
                </div>
                <div className="card">
                    <div className="card-subtitle">Выплачено всего</div>
                    <div className="stat-value">${stats?.total_paid || 0}</div>
                </div>
            </div>

            <div className="card">
                <div className="card-title">Настройки программы</div>
                <div className="input-group">
                    <label>Комиссия (0.2 = 20%)</label>
                    <input className="input" type="number" step="0.01" value={rate} onChange={e => setRate(e.target.value)} />
                </div>
                <div className="input-group">
                    <label>Минимальная выплата ($)</label>
                    <input className="input" type="number" value={minOut} onChange={e => setMinOut(e.target.value)} />
                </div>
                <button className="btn btn-primary" onClick={handleSave} disabled={loading}>Сохранить условия</button>
            </div>
        </div>
    )
}

function PaymentsPage({ onBack }) {
    const [loading, setLoading] = useState(false)
    const [toast, setToast] = useState(null)
    const [form, setForm] = useState({
        yoomoney_shop_id: '',
        yoomoney_secret: '',
        robokassa_merchant_id: '',
        robokassa_password_1: '',
        robokassa_password_2: '',
        cryptobot_token: ''
    })

    useEffect(() => {
        api.getSettings().then(s => {
            setForm({
                yoomoney_shop_id: s.yoomoney_shop_id?.value || '',
                yoomoney_secret: '',
                robokassa_merchant_id: s.robokassa_merchant_id?.value || '',
                robokassa_password_1: '',
                robokassa_password_2: '',
                cryptobot_token: ''
            })
        }).catch(console.error)
    }, [])

    const handleSave = async () => {
        setLoading(true)
        try {
            await api.updatePaymentSettings(form)
            setToast({ message: 'Настройки платежей обновлены!', type: 'success' })
        } catch (e) { setToast({ message: e.message, type: 'error' }) }
        setLoading(false)
    }

    return (
        <div className="page" style={{ paddingBottom: 80 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <button className="btn btn-secondary" onClick={onBack} style={{ padding: '8px 12px' }}>←</button>
                <h1 className="page-title" style={{ margin: 0 }}>💰 Прием платежей</h1>
            </div>
            {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

            <div className="card">
                <div className="card-title">ЮMoney (ЮKassa)</div>
                <div className="input-group">
                    <label>Shop ID</label>
                    <input className="input" value={form.yoomoney_shop_id} onChange={e => setForm({ ...form, yoomoney_shop_id: e.target.value })} />
                </div>
                <div className="input-group">
                    <label>Секретный ключ (API Key)</label>
                    <input className="input" type="password" value={form.yoomoney_secret} onChange={e => setForm({ ...form, yoomoney_secret: e.target.value })} placeholder="Оставьте пустым, если не меняете..." />
                </div>
            </div>

            <div className="card">
                <div className="card-title">Robokassa</div>
                <div className="input-group">
                    <label>Идентификатор магазина</label>
                    <input className="input" value={form.robokassa_merchant_id} onChange={e => setForm({ ...form, robokassa_merchant_id: e.target.value })} />
                </div>
                <div className="input-group">
                    <label>Пароль #1</label>
                    <input className="input" type="password" value={form.robokassa_password_1} onChange={e => setForm({ ...form, robokassa_password_1: e.target.value })} />
                </div>
                <div className="input-group">
                    <label>Пароль #2</label>
                    <input className="input" type="password" value={form.robokassa_password_2} onChange={e => setForm({ ...form, robokassa_password_2: e.target.value })} />
                </div>
            </div>

            <div className="card">
                <div className="card-title">@CryptoBot (Telegram)</div>
                <div className="input-group">
                    <label>CryptoPay API Token</label>
                    <input className="input" type="password" value={form.cryptobot_token} onChange={e => setForm({ ...form, cryptobot_token: e.target.value })} placeholder="Оставьте пустым, если не меняете..." />
                </div>
            </div>

            <button className="btn btn-primary" onClick={handleSave} disabled={loading}>
                {loading ? 'Сохранение...' : 'Сохранить все ключи'}
            </button>
        </div>
    )
}

// ── Modals ──────────────────────────────────────────────────

function TopupModal({ userId, isDeduct, onClose, onDone }) {
    const [amount, setAmount] = useState(10)
    const [loading, setLoading] = useState(false)

    const handleSub = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            const val = parseFloat(amount)
            const final = isDeduct ? -Math.abs(val) : Math.abs(val)
            await api.topUpUser(userId, final)
            onDone()
            onClose()
        } catch (err) { alert(err.message) }
        setLoading(false)
    }

    return (
        <div className="modal-overlay">
            <div className="card modal-content">
                <div className="card-title">{isDeduct ? 'Списание средств' : 'Пополнение баланса'}</div>
                <form onSubmit={handleSub}>
                    <div className="input-group">
                        <label>Сумма ($)</label>
                        <input className="input" type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
                    </div>
                    {isDeduct && <div style={{ color: 'var(--destructive)', fontSize: 12, marginBottom: 10 }}>Внимание: сумма будет вычтена из баланса пользователя.</div>}
                    <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                        <button type="submit" className={`btn ${isDeduct ? 'btn-secondary' : 'btn-primary'}`} style={isDeduct ? { borderColor: 'var(--destructive)', color: 'var(--destructive)' } : {}} disabled={loading}>
                            {isDeduct ? 'Списать' : 'Пополнить'}
                        </button>
                        <button type="button" className="btn btn-secondary" onClick={onClose}>Отмена</button>
                    </div>
                </form>
            </div>
        </div>
    )
}

function LimitsModal({ userId, initialLimits, onClose, onDone }) {
    const [limits, setLimits] = useState(initialLimits || {})
    const [loading, setLoading] = useState(false)

    const handleSub = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            await api.updateUserLimits(userId, limits)
            onDone()
            onClose()
        } catch (err) { alert(err.message) }
        setLoading(false)
    }

    return (
        <div className="modal-overlay">
            <div className="card modal-content">
                <div className="card-title">Лимиты пользователя</div>
                <form onSubmit={handleSub}>
                    <div className="input-group">
                        <label>Лимит записей (всего)</label>
                        <input className="input" type="number" placeholder="По умолчанию: 5" value={limits.entries_count ?? ''} onChange={(e) => setLimits({ ...limits, entries_count: e.target.value === '' ? '' : parseInt(e.target.value) })} />
                    </div>
                    <div className="input-group">
                        <label>Лимит STT (секунд всего)</label>
                        <div style={{ fontSize: 12, color: '#888', marginBottom: 5 }}>600 сек = 10 мин. По умолчанию: 600</div>
                        <input className="input" type="number" placeholder="По умолчанию: 600" value={limits.stt_seconds ?? ''} onChange={(e) => setLimits({ ...limits, stt_seconds: e.target.value === '' ? '' : parseInt(e.target.value) })} />
                    </div>
                    <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                        <button type="submit" className="btn btn-primary" disabled={loading}>Сохранить</button>
                        <button type="button" className="btn btn-secondary" onClick={onClose}>Отмена</button>
                    </div>
                </form>
            </div>
        </div>
    )
}
function SendMessageModal({ userId, onClose, onDone }) {
    const [text, setText] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSub = async (e) => {
        e.preventDefault()
        if (!text.trim()) return
        setLoading(true)
        try {
            await api.sendUserMessage(userId, text)
            onDone()
        } catch (err) { alert(err.message) }
        setLoading(false)
    }

    return (
        <div className="modal-overlay">
            <div className="card modal-content" style={{ width: '90%', maxWidth: 500 }}>
                <div className="card-title">Отправить сообщение пользователю</div>
                <form onSubmit={handleSub}>
                    <div className="input-group">
                        <textarea
                            className="input"
                            style={{ height: 150 }}
                            value={text}
                            onChange={(e) => setText(e.target.value)}
                            placeholder="Текст сообщения..."
                            autoFocus
                        />
                    </div>
                    <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                        <button type="submit" className="btn btn-primary" disabled={loading}>Отправить</button>
                        <button type="button" className="btn btn-secondary" onClick={onClose}>Отмена</button>
                    </div>
                </form>
            </div>
        </div>
    )
}


function BroadcastPage({ onBack }) {
    const [result, setResult] = useState(null)

    return (
        <div className="page list-page">
            <div className="page-header">
                <button onClick={onBack} className="back-button">
                    <i className="icon-arrow-left"></i> Назад
                </button>
                <h1>Рассылка</h1>
            </div>

            {result !== null ? (
                <div className="card" style={{ textAlign: 'center', padding: 40, marginTop: 20 }}>
                    <div style={{ fontSize: 40, marginBottom: 20 }}>✅</div>
                    <h2>Рассылка завершена!</h2>
                    <p>Сообщение успешно отправлено {result} пользователям.</p>
                    <button className="btn btn-primary" onClick={onBack} style={{ marginTop: 20 }}>Вернуться в меню</button>
                </div>
            ) : (
                <BroadcastModal onClose={onBack} onDone={(count) => setResult(count)} />
            )}
        </div>
    )
}


function BroadcastModal({ onClose, onDone }) {
    // ... existing BroadcastModal code ...
    const [text, setText] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSub = async (e) => {
        e.preventDefault()
        if (!text.trim()) return
        if (!confirm('Отправить это сообщение ВСЕМ активным пользователям?')) return
        setLoading(true)
        try {
            const res = await api.broadcastMessage(text)
            onDone(res.sent_count)
        } catch (err) { alert(err.message) }
        setLoading(false)
    }

    return (
        <div className="card modal-content" style={{ width: '90%', maxWidth: 500, margin: '20px auto' }}>
            <div className="card-title">📣 Общерассылочное сообщение</div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 15 }}>
                Это сообщение получат все активные пользователи бота.
            </p>
            <form onSubmit={handleSub}>
                <div className="input-group">
                    <textarea
                        className="input"
                        style={{ height: 150 }}
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder="Текст рассылки..."
                        autoFocus
                    />
                </div>
                <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                    <button type="submit" className="btn btn-primary" disabled={loading || !text.trim()}>
                        🚀 Разослать
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={onClose}>Отмена</button>
                </div>
            </form>
        </div>
    )
}

function EntryEditModal({ userId, entry, onClose, onDone }) {
    const [text, setText] = useState(entry?.final_diary_text || '')
    const [loading, setLoading] = useState(false)

    const handleSub = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            if (entry) {
                await api.updateEntry(entry.id, { text })
            } else {
                await api.createEntry({ user_id: userId, text })
            }
            onDone()
            onClose()
        } catch (err) { alert(err.message) }
        setLoading(false)
    }

    return (
        <div className="modal-overlay">
            <div className="card modal-content" style={{ width: '90%', maxWidth: 600 }}>
                <div className="card-title">{entry ? 'Редактировать запись' : 'Новая запись'}</div>
                <form onSubmit={handleSub}>
                    <div className="input-group">
                        <textarea
                            className="input"
                            style={{ height: 300, fontSize: 13 }}
                            value={text}
                            onChange={(e) => setText(e.target.value)}
                            placeholder="Текст записи..."
                        />
                    </div>
                    <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                        <button type="submit" className="btn btn-primary" disabled={loading}>
                            {entry ? 'Обновить' : 'Создать'}
                        </button>
                        <button type="button" className="btn btn-secondary" onClick={onClose}>Отмена</button>
                    </div>
                </form>
            </div>
        </div>
    )
}

// ── App Shell ───────────────────────────────────────────────

export default function App() {
    const [page, setPageRaw] = useState(window.location.hash.replace('#', '') || 'users')
    const [selectedUser, setSelectedUser] = useState(localStorage.getItem('selected_user'))
    const [isAuth, setIsAuth] = useState(null)
    const [showBroadcast, setShowBroadcast] = useState(false)
    const [toast, setToast] = useState(null)

    // Navigate with browser history
    const navigate = (newPage, userId) => {
        setPageRaw(newPage)
        if (userId !== undefined) {
            setSelectedUser(userId)
            localStorage.setItem('selected_user', userId)
        }
        window.history.pushState({ page: newPage, userId: userId || selectedUser }, '', `#${newPage}`)
    }
    const setPage = navigate

    useEffect(() => {
        try {
            window.Telegram?.WebApp?.ready()
            window.Telegram?.WebApp?.expand()
        } catch { }

        api.getMe()
            .then(() => setIsAuth(true))
            .catch(() => setIsAuth(false))

        // Handle browser back/forward
        const handlePopState = (e) => {
            if (e.state && e.state.page) {
                setPageRaw(e.state.page)
                if (e.state.userId) {
                    setSelectedUser(e.state.userId)
                    localStorage.setItem('selected_user', e.state.userId)
                }
            } else {
                const hashPage = window.location.hash.replace('#', '') || 'users'
                setPageRaw(hashPage)
            }
        }
        window.addEventListener('popstate', handlePopState)

        // Set initial state based on current hash if no state exists
        if (!window.history.state) {
            window.history.replaceState({ page: page, userId: selectedUser }, '', window.location.hash || '#users')
        }

        return () => window.removeEventListener('popstate', handlePopState)
    }, [])

    // Handle Telegram Back Button
    useEffect(() => {
        const tg = window.Telegram?.WebApp
        if (!tg || !tg.BackButton) return

        const handleBack = () => {
            if (page === 'user-detail') {
                navigate('users')
            } else if (['dashboard', 'partners', 'payments', 'logs', 'entries', 'settings'].includes(page)) {
                navigate('menu')
            } else if (page === 'menu') {
                navigate('users')
            }
        }

        if (page === 'users') {
            tg.BackButton.hide()
        } else {
            tg.BackButton.show()
            tg.BackButton.onClick(handleBack)
        }

        return () => {
            tg.BackButton.offClick(handleBack)
        }
    }, [page])

    const handleSelectUser = (id) => {
        setSelectedUser(id)
        navigate('user-detail', id)
    }

    const renderPage = () => {
        switch (page) {
            case 'users': return <UsersPage onSelectUser={handleSelectUser} />
            case 'user-detail': return <UserDetailsPage userId={selectedUser} onBack={() => setPage('users')} />
            case 'entries': return <EntriesPage onBack={() => setPage('menu')} />

            // Menu pages
            case 'menu': return <MenuPage onNavigate={setPage} onBack={() => setPage('users')} />
            case 'dashboard': return <DashboardPage onBack={() => setPage('menu')} />
            case 'partners': return <PartnersPage onBack={() => setPage('menu')} />
            case 'payments': return <PaymentsPage onBack={() => setPage('menu')} />
            case 'logs': return <EventsPage onBack={() => setPage('menu')} />
            case 'settings': return <SettingsPage onBack={() => setPage('menu')} />
            case 'broadcast': return <BroadcastPage onBack={() => setPage('menu')} />

            default: return <UsersPage onSelectUser={handleSelectUser} />
        }
    }

    // Determine which tab is active based on current page
    const getActiveTab = () => {
        // If we are on users page or details, active is 'users'
        if (page === 'users' || page === 'user-detail') return 'users'
        // Everything else is under Menu now (including entries)
        return 'menu'
    }

    // ── Sidebar Component ───────────────────────────────────────

    function Sidebar({ activePage, onNavigate }) {
        const items = [
            { id: 'dashboard', label: 'Dashboard', icon: icons.dashboard },
            { id: 'users', label: 'Users', icon: icons.users },
            { id: 'entries', label: 'Journal', icon: icons.entries },
            { id: 'broadcast', label: 'Broadcast', icon: (<span>📣</span>) },
            { id: 'settings', label: 'Settings', icon: icons.settings },
        ]

        return (
            <aside className="sidebar">
                <div className="sidebar-header">
                    🚀 DiaryBot Admin
                </div>
                <nav className="sidebar-nav">
                    {items.map(item => (
                        <div
                            key={item.id}
                            className={`sidebar-link ${activePage === item.id ? 'active' : ''}`}
                            onClick={() => onNavigate(item.id)}
                        >
                            <div style={{ width: 20, display: 'flex', justifyContent: 'center' }}>{item.icon}</div>
                            <span>{item.label}</span>
                        </div>
                    ))}
                </nav>
                <div style={{ marginTop: 'auto', padding: '1rem 0' }}>
                    <div className="sidebar-link" onClick={() => {
                        if (confirm('Logout?')) { localStorage.removeItem('admin_password'); window.location.reload(); }
                    }}>
                        <span>🚪 Logout</span>
                    </div>
                </div>
            </aside>
        )
    }

    if (isAuth === null) return <div className="loading"><div className="spinner"></div></div>
    if (isAuth === false) return <LoginPage onLogin={() => setIsAuth(true)} />

    const activeTab = getActiveTab()

    return (
        <div className="app">
            <Sidebar activePage={page} onNavigate={setPage} />

            <div className="content">
                {/* Top Bar for Mobile/Desktop */}
                {/* <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2 style={{ margin: 0 }}>{page.charAt(0).toUpperCase() + page.slice(1)}</h2>
                    <div style={{ fontSize: 12, color: 'var(--secondary)' }}>Admin Panel</div>
                </div> */}

                {renderPage()}

                {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
            </div>

            <nav className="bottom-nav">
                {TABS.map((t) => (
                    <button
                        key={t.id}
                        className={`nav-item ${activeTab === t.id ? 'active' : ''}`}
                        onClick={() => setPage(t.id)}
                    >
                        {t.icon}
                        {t.label}
                    </button>
                ))}
            </nav>
        </div>
    )
}
