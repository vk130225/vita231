/**
 * VITA InsuraTech — Shared JS
 * Include in every HTML page: <script src="vita.js"></script>
 * Then call: VITA.init({ page: 'dashboard' })
 */

const VITA = (() => {
  const API = 'http://localhost:8000';
  let currentZone = localStorage.getItem('vita_zone') || 'ORANGE';
  let sseSource = null;

  // ── Nav structure ────────────────────────────────────────────────────────
  const NAV = [
    { id: 'dashboard',  label: 'Dashboard',      icon: 'fa-grid-2',            href: 'workers_dashboard.html' },
    { id: 'pipeline',   label: 'Live Pipeline',  icon: 'fa-code-branch',       href: 'workers_pipeline.html' },
    { id: 'zone',       label: 'Zone Status',    icon: 'fa-map-location-dot',  href: 'workers_zonestatus.html' },
    { id: 'payouts',    label: 'Payout History', icon: 'fa-wallet',            href: 'workers_payouts.html' },
    { id: 'sensors',    label: 'Live Sensors',   icon: 'fa-satellite-dish',    href: 'workers_sensors.html' },
    { id: 'trust',      label: 'Trust Score',    icon: 'fa-chart-line',        href: 'workers_trust.html' },
    { id: 'profile',    label: 'Profile & KYC',  icon: 'fa-user-circle',       href: 'workers_profile.html' },
  ];

  // ── Sidebar HTML ─────────────────────────────────────────────────────────
  function buildSidebar(activePage) {
    const links = NAV.map(n => `
      <a href="${n.href}" class="nav-link ${activePage === n.id ? 'active' : ''}">
        <i class="fa-solid ${n.icon}"></i> ${n.label}
      </a>
    `).join('');

    return `
      <div class="sidebar-logo">
        <div class="sidebar-logo-icon"><i class="fa-solid fa-shield-heart"></i></div>
        <span class="sidebar-logo-text">VITA <span>WORKER</span></span>
      </div>
      <nav class="sidebar-nav">
        <span class="sidebar-section-label">Main</span>
        ${links.slice(0, NAV.indexOf(NAV.find(n=>n.id==='profile'))*1)}
        <div class="sidebar-divider"></div>
        <span class="sidebar-section-label">Account</span>
        <a href="workers_profile.html" class="nav-link ${activePage==='profile'?'active':''}">
          <i class="fa-solid fa-user-circle"></i> Profile & KYC
        </a>
      </nav>
      <div class="sidebar-footer">
        <div class="sidebar-user">
          <div class="sidebar-avatar" id="sb-avatar">AK</div>
          <div>
            <div class="sidebar-user-name" id="sb-name">Loading...</div>
            <div class="sidebar-user-phone" id="sb-phone">+91 ··· ···</div>
          </div>
          <div id="api-status-dot"></div>
        </div>
        <button onclick="VITA.checkAPI()" class="btn-ghost" style="width:100%;font-size:0.65rem;padding:0.35rem;">
          <i class="fa-solid fa-rotate"></i> Refresh Connection
        </button>
      </div>
    `;
  }

  // ── Topbar HTML ──────────────────────────────────────────────────────────
  function buildTopbar() {
    return `
      <div class="topbar-left">
        <div class="topbar-live-dot" id="tb-live-dot"></div>
        <div>
          <div class="topbar-location">
            <span id="tb-area">Koramangala</span> ·
            <span class="zone-label" id="tb-zone">ORANGE Zone</span>
          </div>
          <div class="topbar-meta">
            Rain <span id="tb-rain" class="mono">—</span> mm/hr ·
            AQI <span id="tb-aqi" class="mono">—</span> ·
            <span id="tb-time">—</span>
          </div>
        </div>
      </div>
      <div class="topbar-right">
        <select id="zone-select" onchange="VITA.setZone(this.value)">
          <option value="GREEN">🟢 GREEN</option>
          <option value="YELLOW">🟡 YELLOW</option>
          <option value="ORANGE">🟠 ORANGE</option>
          <option value="RED">🔴 RED</option>
        </select>
        <div style="text-align:right;border-right:1px solid #e8eaed;padding-right:0.75rem;">
          <div style="font-size:0.55rem;font-weight:900;color:#94a3b8;text-transform:uppercase">Trust</div>
          <div style="font-size:0.75rem;font-weight:900;color:#16a34a;" id="tb-trust">Fast-Track</div>
        </div>
      </div>
    `;
  }

  // ── API helper ───────────────────────────────────────────────────────────
  async function api(path) {
    try {
      const r = await fetch(API + path);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } catch(e) {
      setDot('offline');
      return null;
    }
  }

  // ── API status ───────────────────────────────────────────────────────────
  async function checkAPI() {
    try {
      const r = await fetch(API + '/api/status', { signal: AbortSignal.timeout(3000) });
      if (r.ok) {
        const d = await r.json();
        setDot('online');
        updateTopbar(d);
        toast('Backend connected ✓', 'success');
        return true;
      }
    } catch {}
    setDot('offline');
    toast('Backend offline. Run: uvicorn server:app --port 8000', 'error');
    return false;
  }

  function setDot(state) {
    const dot = document.getElementById('api-status-dot');
    if (dot) dot.className = state;
  }

  // ── Zone ─────────────────────────────────────────────────────────────────
  function setZone(z) {
    currentZone = z;
    localStorage.setItem('vita_zone', z);
    const sel = document.getElementById('zone-select');
    if (sel) sel.value = z;
    document.dispatchEvent(new CustomEvent('vita:zonechange', { detail: z }));
    toast(`Zone → <b>${z}</b>`, 'info');
  }

  function getZone() { return currentZone; }

  // ── Topbar updater ───────────────────────────────────────────────────────
  function updateTopbar(data) {
    if (!data) return;
    const area = document.getElementById('tb-area');
    const zone = document.getElementById('tb-zone');
    const rain = document.getElementById('tb-rain');
    const aqi  = document.getElementById('tb-aqi');
    const time = document.getElementById('tb-time');
    if (area) area.textContent = data.area || '—';
    if (zone) zone.textContent = (data.zone || currentZone) + ' Zone';
    if (rain) rain.textContent = typeof data.rain_mm_hr === 'number' ? data.rain_mm_hr.toFixed(1) : '—';
    if (aqi)  aqi.textContent  = typeof data.aqi === 'number' ? data.aqi.toFixed(0) : '—';
    if (time) time.textContent = new Date().toLocaleTimeString('en-IN', {hour:'2-digit', minute:'2-digit'});
  }

  // ── Worker profile (sidebar) ─────────────────────────────────────────────
  async function loadWorkerProfile() {
    const w = await api('/api/worker/AK001');
    if (!w) return;
    const name   = document.getElementById('sb-name');
    const phone  = document.getElementById('sb-phone');
    const avatar = document.getElementById('sb-avatar');
    const trust  = document.getElementById('tb-trust');
    if (name)   name.textContent   = w.name;
    if (phone)  phone.textContent  = w.phone;
    if (avatar) avatar.textContent = w.initials || w.name.split(' ').map(x=>x[0]).join('');
    if (trust)  trust.textContent  = w.trust_level || 'Fast-Track';
  }

  // ── Toast ────────────────────────────────────────────────────────────────
  function toast(msg, type = 'info') {
    let wrap = document.getElementById('toast-wrap');
    if (!wrap) { wrap = document.createElement('div'); wrap.id = 'toast-wrap'; document.body.appendChild(wrap); }
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.innerHTML = msg;
    wrap.appendChild(el);
    setTimeout(() => el.remove(), 4100);
  }

  // ── SSE sensors stream ───────────────────────────────────────────────────
  function startSSE(zone, onData, onStatus) {
    if (sseSource) { sseSource.close(); sseSource = null; }
    if (onStatus) onStatus(false);
    try {
      sseSource = new EventSource(`${API}/api/stream/sensors?zone=${zone}`);
      sseSource.onopen  = () => { if (onStatus) onStatus(true); };
      sseSource.onmessage = (e) => { if (onData) onData(JSON.parse(e.data)); };
      sseSource.onerror = () => { if (onStatus) onStatus(false); };
    } catch { if (onStatus) onStatus(false); }
  }

  function stopSSE() {
    if (sseSource) { sseSource.close(); sseSource = null; }
  }

  // ── Pipeline SSE ─────────────────────────────────────────────────────────
  function streamPipeline(zone, onStep, onResult, onError) {
    const src = new EventSource(`${API}/api/stream/pipeline?zone=${zone}&worker_id=AK001`);
    src.onmessage = (e) => {
      const d = JSON.parse(e.data);
      if (d.type === 'step')   { if (onStep)   onStep(d); }
      if (d.type === 'result') { if (onResult) onResult(d); src.close(); }
    };
    src.onerror = () => { src.close(); if (onError) onError(); };
    return src;
  }

  // ── Score ring helper ────────────────────────────────────────────────────
  function updateScoreRing(ringId, textId, score, maxDash) {
    const ring = document.getElementById(ringId);
    const text = document.getElementById(textId);
    if (!ring || !text) return;
    ring.style.strokeDashoffset = maxDash * (1 - score);
    ring.style.stroke = score >= 0.7 ? '#22c55e' : score >= 0.5 ? '#eab308' : score >= 0.3 ? '#f97316' : '#ef4444';
    text.textContent = score.toFixed(2);
  }

  // ── Chip helper ──────────────────────────────────────────────────────────
  function chip(val) {
    return `<span class="chip chip-${val}">${val}</span>`;
  }

  // ── Init ─────────────────────────────────────────────────────────────────
  async function init({ page }) {
    // Inject sidebar
    const sb = document.getElementById('sidebar');
    if (sb) sb.innerHTML = buildSidebar(page);

    // Inject topbar
    const tb = document.getElementById('topbar');
    if (tb) tb.innerHTML = buildTopbar();

    // Restore zone
    const sel = document.getElementById('zone-select');
    if (sel) sel.value = currentZone;

    // Check API + load worker
    const ok = await checkAPI();
    if (ok) {
      await loadWorkerProfile();
      // Auto-refresh topbar every 30s
      setInterval(async () => {
        const d = await api('/api/status');
        if (d) updateTopbar(d);
      }, 30000);
    }
  }

  // ── Public API ───────────────────────────────────────────────────────────
  return { init, api, checkAPI, setZone, getZone, toast, chip,
           startSSE, stopSSE, streamPipeline, updateScoreRing, updateTopbar,
           API };
})();
