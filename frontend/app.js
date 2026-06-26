/* ── AstroSpace Frontend ── */

const API = '';   // same origin; backend serves /api/v1/...

// ── State ──────────────────────────────────────────────────────────────────
let kundlis       = [];
let activeKundli  = null;
let activeTab     = 'overview';
let editMode      = false;

// ── Zodiac helpers ─────────────────────────────────────────────────────────
const ZODIAC = {
  Aries:       { symbol: '♈', emoji: '🐏', color: '#e74c3c' },
  Taurus:      { symbol: '♉', emoji: '🐂', color: '#27ae60' },
  Gemini:      { symbol: '♊', emoji: '👯', color: '#f1c40f' },
  Cancer:      { symbol: '♋', emoji: '🦀', color: '#3498db' },
  Leo:         { symbol: '♌', emoji: '🦁', color: '#e67e22' },
  Virgo:       { symbol: '♍', emoji: '🌾', color: '#2ecc71' },
  Libra:       { symbol: '♎', emoji: '⚖️', color: '#9b59b6' },
  Scorpio:     { symbol: '♏', emoji: '🦂', color: '#c0392b' },
  Sagittarius: { symbol: '♐', emoji: '🏹', color: '#8e44ad' },
  Capricorn:   { symbol: '♑', emoji: '🐐', color: '#7f8c8d' },
  Aquarius:    { symbol: '♒', emoji: '🏺', color: '#2980b9' },
  Pisces:      { symbol: '♓', emoji: '🐟', color: '#1abc9c' },
};

const PLANET_ICONS = {
  Sun:'☀️', Moon:'🌙', Mercury:'☿', Venus:'♀️', Mars:'♂️',
  Jupiter:'♃', Saturn:'♄', Uranus:'♅', Neptune:'♆', Pluto:'♇',
  'North Node':'☊', 'True Node':'☊', Chiron:'⚷',
};

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadKundlis();
});

// ── API helpers ────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API error');
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Load Kundlis ───────────────────────────────────────────────────────────
async function loadKundlis() {
  try {
    kundlis = await apiFetch('/api/v1/kundlis');
    renderSidebar(kundlis);
  } catch (e) {
    showToast('Failed to load kundlis: ' + e.message, 'error');
  }
}

function renderSidebar(list) {
  const el = document.getElementById('kundli-list');
  if (!list.length) {
    el.innerHTML = '<div style="padding:16px;color:var(--muted);font-size:13px;text-align:center">No kundlis yet</div>';
    return;
  }
  el.innerHTML = list.map(k => {
    const sign = k.sun_sign || '?';
    const z    = ZODIAC[sign] || { emoji: '✦' };
    const active = activeKundli && activeKundli.id === k.id ? 'active' : '';
    return `
      <div class="kundli-item ${active}" onclick="selectKundli('${k.id}')">
        <div class="kundli-avatar">${z.emoji}</div>
        <div class="kundli-info">
          <div class="kundli-name">${esc(k.name)}</div>
          <div class="kundli-meta">${k.sun_sign || 'Unknown'} · ${k.relation}</div>
        </div>
      </div>`;
  }).join('');
}

function filterKundlis(q) {
  const filtered = kundlis.filter(k =>
    k.name.toLowerCase().includes(q.toLowerCase()) ||
    (k.sun_sign || '').toLowerCase().includes(q.toLowerCase())
  );
  renderSidebar(filtered);
}

// ── Select Kundli ──────────────────────────────────────────────────────────
async function selectKundli(id) {
  activeKundli = kundlis.find(k => k.id === id);
  if (!activeKundli) return;

  // update UI shell
  document.getElementById('empty-state').classList.add('hidden');
  document.getElementById('panel-overview').classList.remove('hidden');
  document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
  document.getElementById('tabs').style.display = '';
  document.getElementById('topbar-actions').style.display = '';

  const sign = activeKundli.sun_sign || '';
  const z    = ZODIAC[sign] || { emoji: '✦' };
  document.getElementById('topbar-title').textContent = `${z.emoji} ${activeKundli.name}`;
  document.getElementById('topbar-sub').textContent =
    `${activeKundli.sun_sign || 'Chart'} · ${activeKundli.relation} · Born ${activeKundli.birth_year}`;

  renderSidebar(kundlis);
  switchTab('overview');
}

// ── Tabs ───────────────────────────────────────────────────────────────────
function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
  const panel = document.getElementById('panel-' + tab);
  panel.classList.remove('hidden');

  if      (tab === 'overview')  renderOverview();
  else if (tab === 'chart')     renderChart();
  else if (tab === 'readings')  renderReadings();
  else if (tab === 'compat')    renderCompat();
  else if (tab === 'notes')     renderNotes();
}

// ── Overview panel ─────────────────────────────────────────────────────────
function renderOverview() {
  const k = activeKundli;
  if (!k) return;
  const cd = k.chart_data || {};
  const planets = cd.planets || {};
  const sun  = k.sun_sign  || '–';
  const moon = k.moon_sign || '–';
  const asc  = k.ascendant || '–';
  const zSun  = ZODIAC[sun]  || { symbol: '?', emoji: '✦' };
  const zMoon = ZODIAC[moon] || { symbol: '?', emoji: '✦' };
  const zAsc  = ZODIAC[asc]  || { symbol: '?', emoji: '✦' };

  let planetRows = '';
  for (const [pname, pdata] of Object.entries(planets)) {
    const icon = PLANET_ICONS[pname] || '⭐';
    const retro = pdata.retrograde ? '<span class="retro-tag">℞</span>' : '';
    planetRows += `
      <div class="planet-row">
        <span class="planet-icon">${icon}</span>
        <span class="planet-name">${pname}</span>
        <span class="planet-sign">${pdata.sign || '–'}</span>
        <span class="planet-deg">${pdata.degree || 0}° H${pdata.house || '?'}${retro}</span>
      </div>`;
  }
  if (!planetRows) planetRows = '<div style="color:var(--muted);font-size:13px">Chart data not available</div>';

  const birthDate = `${k.birth_year}-${String(k.birth_month).padStart(2,'0')}-${String(k.birth_day).padStart(2,'0')}`;
  const birthTime = `${String(k.birth_hour).padStart(2,'0')}:${String(k.birth_minute).padStart(2,'0')}`;

  document.getElementById('panel-overview').innerHTML = `
    <div class="card">
      <div class="card-title">✨ The Big Three</div>
      <div class="big-three">
        <div class="zodiac-badge">
          <div class="sign-symbol">${zSun.emoji}</div>
          <div class="sign-label">Sun Sign</div>
          <div class="sign-name">${sun}</div>
        </div>
        <div class="zodiac-badge">
          <div class="sign-symbol">${zMoon.emoji}</div>
          <div class="sign-label">Moon Sign</div>
          <div class="sign-name">${moon}</div>
        </div>
        <div class="zodiac-badge">
          <div class="sign-symbol">${zAsc.emoji}</div>
          <div class="sign-label">Ascendant</div>
          <div class="sign-name">${asc}</div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">🪐 All Planets</div>
      <div class="planet-grid">${planetRows}</div>
    </div>
    <div class="card">
      <div class="card-title">📅 Birth Details</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:14px">
        <div><span style="color:var(--muted)">Date: </span>${birthDate}</div>
        <div><span style="color:var(--muted)">Time: </span>${birthTime}</div>
        <div><span style="color:var(--muted)">City: </span>${esc(k.birth_city)}</div>
        <div><span style="color:var(--muted)">Country: </span>${esc(k.birth_nation)}</div>
        <div><span style="color:var(--muted)">Relation: </span>${esc(k.relation)}</div>
      </div>
    </div>
    <div class="card" style="text-align:center">
      <button class="btn-primary" style="max-width:280px" onclick="switchTab('readings')">
        🔮 Generate AI Reading
      </button>
    </div>`;
}

// ── Chart panel ────────────────────────────────────────────────────────────
function renderChart() {
  const k  = activeKundli;
  const cd = (k && k.chart_data) || {};
  const planets = cd.planets || {};

  document.getElementById('panel-chart').innerHTML = `
    <div class="card">
      <div class="card-title">🪐 Natal Chart Wheel</div>
      <canvas id="chart-canvas" width="480" height="480"></canvas>
    </div>
    <div class="card">
      <div class="card-title">🏠 House Positions</div>
      <div class="planet-grid" id="house-list"></div>
    </div>`;

  drawChartWheel(planets);

  const houseEl = document.getElementById('house-list');
  const houses = cd.houses || {};
  if (Object.keys(houses).length) {
    houseEl.innerHTML = Object.entries(houses).map(([h, data]) =>
      `<div class="planet-row">
        <span class="planet-icon">🏠</span>
        <span class="planet-name">H${h}</span>
        <span class="planet-sign">${data.sign || '–'}</span>
        <span class="planet-deg">${data.degree || 0}°</span>
       </div>`
    ).join('');
  } else {
    houseEl.innerHTML = '<div style="color:var(--muted);font-size:13px">House data not available</div>';
  }
}

function drawChartWheel(planets) {
  const canvas = document.getElementById('chart-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const cx = 240, cy = 240, R = 200, r = 100;

  ctx.clearRect(0, 0, 480, 480);

  // Outer ring background
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  ctx.fillStyle = '#0d0d1f';
  ctx.fill();
  ctx.strokeStyle = '#1e1e3f';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Inner circle
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.strokeStyle = '#1e1e3f';
  ctx.lineWidth = 1;
  ctx.stroke();

  // 12 zodiac segments
  const signs = Object.keys(ZODIAC);
  const segAngle = (Math.PI * 2) / 12;
  const signColors = signs.map(s => ZODIAC[s]?.color || '#7B2FBE');

  signs.forEach((sign, i) => {
    const startAngle = i * segAngle - Math.PI / 2;
    const endAngle   = startAngle + segAngle;
    const midAngle   = startAngle + segAngle / 2;
    const labelR     = (R + r) / 2 + 10;

    // Segment
    ctx.beginPath();
    ctx.moveTo(cx + r * Math.cos(startAngle), cy + r * Math.sin(startAngle));
    ctx.arc(cx, cy, R - 10, startAngle, endAngle);
    ctx.arc(cx, cy, r + 10, endAngle, startAngle, true);
    ctx.closePath();
    ctx.fillStyle = signColors[i] + '22';
    ctx.fill();
    ctx.strokeStyle = '#1e1e3f';
    ctx.lineWidth = 0.5;
    ctx.stroke();

    // Divider lines
    ctx.beginPath();
    ctx.moveTo(cx + r * Math.cos(startAngle), cy + r * Math.sin(startAngle));
    ctx.lineTo(cx + R * Math.cos(startAngle), cy + R * Math.sin(startAngle));
    ctx.strokeStyle = '#1e1e3f';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Sign symbol
    ctx.font = '14px serif';
    ctx.fillStyle = signColors[i];
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(ZODIAC[sign].symbol, cx + labelR * Math.cos(midAngle), cy + labelR * Math.sin(midAngle));
  });

  // Planet dots
  Object.entries(planets).forEach(([name, p], idx) => {
    const signIdx = signs.indexOf(p.sign);
    if (signIdx === -1) return;
    const baseAngle = signIdx * segAngle - Math.PI / 2;
    const degOffset = ((p.degree || 0) / 30) * segAngle;
    const angle     = baseAngle + degOffset;
    const pr        = r + 30 + (idx % 3) * 18;
    const px        = cx + pr * Math.cos(angle);
    const py        = cy + pr * Math.sin(angle);

    ctx.beginPath();
    ctx.arc(px, py, 8, 0, Math.PI * 2);
    ctx.fillStyle = '#7B2FBE';
    ctx.fill();
    ctx.strokeStyle = '#F4D03F';
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.font = '10px serif';
    ctx.fillStyle = '#F4D03F';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(PLANET_ICONS[name] || '⭐', px, py);
  });

  // Center text
  ctx.font = 'bold 16px Inter, sans-serif';
  ctx.fillStyle = '#F4D03F';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('✦', cx, cy);
}

// ── Readings panel ─────────────────────────────────────────────────────────
let currentPeriod = 'daily';

function renderReadings() {
  document.getElementById('panel-readings').innerHTML = `
    <div class="card">
      <div class="card-title">🔮 AI Readings</div>
      <div class="period-tabs">
        ${['daily','weekly','monthly','quarterly','yearly'].map(p =>
          `<button class="period-btn ${p === currentPeriod ? 'active' : ''}"
            onclick="selectPeriod('${p}')">${p.charAt(0).toUpperCase()+p.slice(1)}</button>`
        ).join('')}
      </div>
      <div id="reading-area"><div class="loading-row"><div class="spinner spinner-lg"></div><span>Loading…</span></div></div>
      <div style="text-align:right;margin-top:10px">
        <button class="btn-icon" onclick="generateReading(true)">🔄 Refresh Reading</button>
      </div>
    </div>`;

  loadReading(false);
}

function selectPeriod(p) {
  currentPeriod = p;
  document.querySelectorAll('.period-btn').forEach(b => b.classList.toggle('active', b.textContent.toLowerCase() === p));
  loadReading(false);
}

async function loadReading(forceRefresh) {
  const area = document.getElementById('reading-area');
  if (!area) return;
  area.innerHTML = '<div class="loading-row"><div class="spinner spinner-lg"></div><span>Consulting the stars…</span></div>';

  try {
    const data = await apiFetch(`/api/v1/readings/${activeKundli.id}/generate`, {
      method: 'POST',
      body: JSON.stringify({ period: currentPeriod, force_refresh: forceRefresh }),
    });
    const cached = data.cached ? '<span style="color:var(--teal)">📦 Cached</span>' : '<span style="color:var(--purple2)">✨ Fresh</span>';
    area.innerHTML = `
      <div class="reading-content">${markdownToHtml(data.content)}</div>
      <div class="reading-meta">
        <span>Generated: ${data.generated_at ? new Date(data.generated_at).toLocaleString() : '–'}</span>
        ${cached}
      </div>`;
  } catch (e) {
    area.innerHTML = `<div style="color:var(--red);padding:16px">Failed to generate reading: ${esc(e.message)}</div>`;
  }
}

function generateReading(force) {
  loadReading(force);
}

// ── Compatibility panel ────────────────────────────────────────────────────
function renderCompat() {
  const others = kundlis.filter(k => k.id !== activeKundli.id);
  const options = others.map(k =>
    `<option value="${k.id}">${esc(k.name)} (${k.sun_sign || 'Unknown'})</option>`
  ).join('');

  document.getElementById('panel-compat').innerHTML = `
    <div class="card">
      <div class="card-title">💞 Compatibility Analysis</div>
      <div class="compat-grid">
        <div>
          <label class="form-label">Person A</label>
          <div class="compat-select" style="background:var(--bg3);padding:12px;border-radius:8px;border:1px solid var(--border)">
            ${esc(activeKundli.name)} (${activeKundli.sun_sign || 'Unknown'})
          </div>
        </div>
        <div>
          <label class="form-label">Person B</label>
          <select class="compat-select" id="compat-partner" onchange="runCompat()">
            <option value="">Select a person…</option>
            ${options}
          </select>
        </div>
      </div>
      <div id="compat-result"></div>
    </div>`;
}

async function runCompat() {
  const partnerId = document.getElementById('compat-partner').value;
  if (!partnerId) return;
  const partner = kundlis.find(k => k.id === partnerId);
  if (!partner) return;

  const res = document.getElementById('compat-result');
  res.innerHTML = '<div class="loading-row"><div class="spinner spinner-lg"></div><span>Calculating compatibility…</span></div>';

  try {
    const a = activeKundli;
    const b = partner;
    const data = await apiFetch('/api/v1/compatibility', {
      method: 'POST',
      body: JSON.stringify({
        person1: { name: a.name, year: a.birth_year, month: a.birth_month, day: a.birth_day, hour: a.birth_hour, minute: a.birth_minute, city: a.birth_city, nation: a.birth_nation },
        person2: { name: b.name, year: b.birth_year, month: b.birth_month, day: b.birth_day, hour: b.birth_hour, minute: b.birth_minute, city: b.birth_city, nation: b.birth_nation },
      }),
    });
    const text = data.compatibility || data.analysis || data.content || JSON.stringify(data);
    res.innerHTML = `<div class="reading-content">${markdownToHtml(text)}</div>`;
  } catch (e) {
    res.innerHTML = `<div style="color:var(--red);padding:16px">Compatibility error: ${esc(e.message)}</div>`;
  }
}

// ── Notes panel ────────────────────────────────────────────────────────────
function renderNotes() {
  document.getElementById('panel-notes').innerHTML = `
    <div class="card">
      <div class="card-title">📝 Personal Notes</div>
      <textarea class="notes-area" id="notes-text" placeholder="Add personal notes about ${esc(activeKundli.name)}...">${esc(activeKundli.notes || '')}</textarea>
      <div style="text-align:right;margin-top:10px">
        <button class="btn-primary" style="max-width:120px" onclick="saveNotes()">💾 Save</button>
      </div>
    </div>`;
}

async function saveNotes() {
  const notes = document.getElementById('notes-text').value;
  try {
    await apiFetch(`/api/v1/kundlis/${activeKundli.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ notes }),
    });
    activeKundli.notes = notes;
    showToast('Notes saved ✓', 'success');
  } catch (e) {
    showToast('Save failed: ' + e.message, 'error');
  }
}

// ── Add/Edit Modal ─────────────────────────────────────────────────────────
function openAddModal() {
  editMode = false;
  clearForm();
  document.getElementById('modal-title').textContent = '✨ Add Kundli';
  document.getElementById('modal-save-btn').textContent = 'Save Kundli';
  document.getElementById('kundli-modal').classList.remove('hidden');
}

function openEditModal() {
  if (!activeKundli) return;
  editMode = true;
  const k = activeKundli;
  document.getElementById('f-name').value   = k.name;
  document.getElementById('f-relation').value = k.relation || 'friend';
  document.getElementById('f-year').value   = k.birth_year;
  document.getElementById('f-month').value  = k.birth_month;
  document.getElementById('f-day').value    = k.birth_day;
  document.getElementById('f-hour').value   = k.birth_hour;
  document.getElementById('f-minute').value = k.birth_minute;
  document.getElementById('f-city').value   = k.birth_city;
  document.getElementById('f-nation').value = k.birth_nation;
  document.getElementById('f-notes').value  = k.notes || '';
  document.getElementById('modal-title').textContent = '✏️ Edit Kundli';
  document.getElementById('modal-save-btn').textContent = 'Update';
  document.getElementById('kundli-modal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('kundli-modal').classList.add('hidden');
}

function clearForm() {
  ['f-name','f-year','f-month','f-day','f-city','f-notes'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('f-hour').value   = '12';
  document.getElementById('f-minute').value = '0';
  document.getElementById('f-nation').value = 'US';
  document.getElementById('f-relation').value = 'friend';
}

async function saveKundli() {
  const name   = document.getElementById('f-name').value.trim();
  const year   = parseInt(document.getElementById('f-year').value);
  const month  = parseInt(document.getElementById('f-month').value);
  const day    = parseInt(document.getElementById('f-day').value);
  const hour   = parseInt(document.getElementById('f-hour').value) || 12;
  const minute = parseInt(document.getElementById('f-minute').value) || 0;
  const city   = document.getElementById('f-city').value.trim();
  const nation = document.getElementById('f-nation').value.trim().toUpperCase() || 'US';
  const relation = document.getElementById('f-relation').value;
  const notes  = document.getElementById('f-notes').value.trim();

  if (!name || !year || !month || !day || !city) {
    showToast('Please fill required fields (name, date, city)', 'error');
    return;
  }

  const btn = document.getElementById('modal-save-btn');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    let k;
    if (editMode && activeKundli) {
      k = await apiFetch(`/api/v1/kundlis/${activeKundli.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name, relation, birth_hour: hour, birth_minute: minute, birth_city: city, birth_nation: nation, notes }),
      });
      const idx = kundlis.findIndex(x => x.id === k.id);
      if (idx >= 0) kundlis[idx] = k;
      activeKundli = k;
    } else {
      k = await apiFetch('/api/v1/kundlis', {
        method: 'POST',
        body: JSON.stringify({ name, relation, birth_year: year, birth_month: month, birth_day: day, birth_hour: hour, birth_minute: minute, birth_city: city, birth_nation: nation, notes }),
      });
      kundlis.push(k);
      activeKundli = k;
    }

    closeModal();
    renderSidebar(kundlis);
    await selectKundli(k.id);
    showToast(editMode ? 'Kundli updated ✓' : 'Kundli created ✓', 'success');
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = editMode ? 'Update' : 'Save Kundli';
  }
}

// ── Delete ─────────────────────────────────────────────────────────────────
async function confirmDelete() {
  if (!activeKundli) return;
  if (!confirm(`Delete ${activeKundli.name}'s kundli? This will remove all readings too.`)) return;
  try {
    await apiFetch(`/api/v1/kundlis/${activeKundli.id}`, { method: 'DELETE' });
    kundlis = kundlis.filter(k => k.id !== activeKundli.id);
    activeKundli = null;
    document.getElementById('empty-state').classList.remove('hidden');
    document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
    document.getElementById('tabs').style.display = 'none';
    document.getElementById('topbar-actions').style.display = 'none';
    document.getElementById('topbar-title').textContent = 'Welcome to AstroSpace';
    document.getElementById('topbar-sub').textContent = 'Select or add a kundli to begin';
    renderSidebar(kundlis);
    showToast('Kundli deleted', 'success');
  } catch (e) {
    showToast('Delete failed: ' + e.message, 'error');
  }
}

// ── Markdown ────────────────────────────────────────────────────────────────
function markdownToHtml(md) {
  if (!md) return '';
  return md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hul])/gm, '')
    .replace(/<\/ul>\s*<ul>/g, '')
    .replace(/([^>])\n([^<])/g, '$1<br>$2');
}

// ── Toast ───────────────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), 3500);
}

// ── Escape HTML ─────────────────────────────────────────────────────────────
function esc(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Close modal on overlay click
document.getElementById('kundli-modal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeModal();
});
