/**
 * app.js — Shared frontend utilities
 *
 * Includes:
 *   - Token / user storage helpers
 *   - apiFetch with automatic Bearer injection + 401 handling
 *   - showToast notification system
 *   - requireAuth guard
 *   - initNavbar — populates user pill and logout button
 *   - Badge / formatting helpers
 */

// ── Constants ────────────────────────────────────────────────────────────────
const API_BASE = '';  // Same origin as the FastAPI server

// ── Storage helpers ───────────────────────────────────────────────────────────
function getToken()       { return localStorage.getItem('cp_token'); }
function setToken(t)      { localStorage.setItem('cp_token', t); }
function clearToken()     { localStorage.removeItem('cp_token'); }
function getUser()        { const u = localStorage.getItem('cp_user'); return u ? JSON.parse(u) : null; }
function setUser(u)       { localStorage.setItem('cp_user', JSON.stringify(u)); }
function clearUser()      { localStorage.removeItem('cp_user'); }
function clearSession()   { clearToken(); clearUser(); }

// ── Fetch wrapper ─────────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  let res;
  try {
    res = await fetch(API_BASE + path, { ...options, headers });
  } catch (networkErr) {
    throw new Error('Network error — is the server running?');
  }

  // Session expired or invalid token
  if (res.status === 401) {
    clearSession();
    window.location.href = '/index.html';
    return null;
  }

  // No content (e.g., DELETE 204)
  if (res.status === 204) return null;

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail || err.message || detail;
    } catch { /* ignore parse error */ }
    throw new Error(detail);
  }

  try {
    return await res.json();
  } catch {
    return null;
  }
}

// ── Toast system ──────────────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span style="font-size:1rem;font-weight:800;flex-shrink:0">${icons[type] || icons.info}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.2s, transform 0.2s';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(30px)';
    setTimeout(() => toast.remove(), 220);
  }, duration);
}

// ── Auth guard ────────────────────────────────────────────────────────────────
/**
 * Call at the top of any protected page.
 * @param {boolean} adminOnly  — redirect to dashboard if not admin
 * @returns {object|null}      — user object or null (also redirects)
 */
function requireAuth(adminOnly = false) {
  const token = getToken();
  const user  = getUser();

  if (!token || !user) {
    window.location.href = '/index.html';
    return null;
  }
  if (adminOnly && user.role !== 'admin') {
    showToast('Admin access required', 'error');
    window.location.href = '/dashboard.html';
    return null;
  }
  return user;
}

// ── Navbar initialisation ─────────────────────────────────────────────────────
function initNavbar(activePage = '') {
  const user = getUser();
  if (!user) return;

  // Populate user pill
  const pill = document.getElementById('user-pill');
  if (pill) {
    const initials = user.username.slice(0, 2).toUpperCase();
    pill.innerHTML = `
      <div class="avatar">${initials}</div>
      <span>${user.username}</span>
      <span class="role-tag ${user.role}">${user.role}</span>
    `;
  }

  // Show admin nav link only for admins
  const adminLink = document.getElementById('admin-nav-link');
  if (adminLink) {
    adminLink.style.display = user.role === 'admin' ? 'block' : 'none';
  }

  // Highlight active nav item
  if (activePage) {
    document.querySelectorAll('.navbar-nav a').forEach(a => {
      if (a.dataset.page === activePage) a.classList.add('active');
    });
  }

  // Logout button
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      clearSession();
      window.location.href = '/index.html';
    });
  }
}

// ── Formatting helpers ────────────────────────────────────────────────────────
function diffBadge(d) {
  const cls = d >= 1600 ? 'diff-hard' : d >= 1000 ? 'diff-medium' : 'diff-easy';
  return `<span class="badge ${cls}">${d}</span>`;
}

function verdictBadge(v) {
  return `<span class="badge verdict-${v}">${v}</span>`;
}

function fmtTime(sec) {
  if (sec == null) return '—';
  return sec < 1 ? `${Math.round(sec * 1000)} ms` : `${sec.toFixed(2)} s`;
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function fmtDateShort(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ── Modal helpers ─────────────────────────────────────────────────────────────
function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

// Close modal when clicking the overlay backdrop
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});

// ── Tab system ────────────────────────────────────────────────────────────────
function initTabs(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(target)?.classList.add('active');
    });
  });
}
