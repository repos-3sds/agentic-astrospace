
// ── Starfield ────────────────────────────────────────────────────────────────
const canvas = document.getElementById('starfield');
const ctx = canvas.getContext('2d');
let stars = [];

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

function initStars() {
  stars = Array.from({ length: 220 }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    r: Math.random() * 1.4 + 0.2,
    a: Math.random(),
    speed: Math.random() * 0.4 + 0.05,
    twinkle: Math.random() * Math.PI * 2,
  }));
}

function drawStars() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const t = Date.now() / 1000;
  stars.forEach(s => {
    s.twinkle += s.speed * 0.02;
    const alpha = 0.3 + 0.5 * Math.abs(Math.sin(s.twinkle));
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255,255,255,${alpha})`;
    ctx.fill();
  });
  requestAnimationFrame(drawStars);
}

window.addEventListener('resize', () => { resize(); initStars(); });
resize(); initStars(); drawStars();

// ── Navbar scroll effect ─────────────────────────────────────────────────────
window.addEventListener('scroll', () => {
  document.getElementById('navbar').style.background =
    window.scrollY > 50 ? 'rgba(5,5,15,0.95)' : 'rgba(5,5,15,0.7)';
});

// ── Zodiac Data ──────────────────────────────────────────────────────────────
const ZODIAC = [
  { name: 'Aries',       symbol: '♈', dates: 'Mar 21–Apr 19', element: 'Fire',  modality: 'Cardinal', ruler: 'Mars',    traits: 'Pioneering, courageous, impulsive, energetic', compatible: ['Leo', 'Sagittarius', 'Gemini'] },
  { name: 'Taurus',      symbol: '♉', dates: 'Apr 20–May 20', element: 'Earth', modality: 'Fixed',    ruler: 'Venus',   traits: 'Stable, sensual, persistent, loyal', compatible: ['Virgo', 'Capricorn', 'Cancer'] },
  { name: 'Gemini',      symbol: '♊', dates: 'May 21–Jun 20', element: 'Air',   modality: 'Mutable',  ruler: 'Mercury', traits: 'Curious, adaptable, witty, communicative', compatible: ['Libra', 'Aquarius', 'Aries'] },
  { name: 'Cancer',      symbol: '♋', dates: 'Jun 21–Jul 22', element: 'Water', modality: 'Cardinal', ruler: 'Moon',    traits: 'Nurturing, intuitive, protective, emotional', compatible: ['Scorpio', 'Pisces', 'Taurus'] },
  { name: 'Leo',         symbol: '♌', dates: 'Jul 23–Aug 22', element: 'Fire',  modality: 'Fixed',    ruler: 'Sun',     traits: 'Creative, generous, proud, dramatic', compatible: ['Aries', 'Sagittarius', 'Gemini'] },
  { name: 'Virgo',       symbol: '♍', dates: 'Aug 23–Sep 22', element: 'Earth', modality: 'Mutable',  ruler: 'Mercury', traits: 'Analytical, practical, service-oriented, precise', compatible: ['Taurus', 'Capricorn', 'Cancer'] },
  { name: 'Libra',       symbol: '♎', dates: 'Sep 23–Oct 22', element: 'Air',   modality: 'Cardinal', ruler: 'Venus',   traits: 'Harmonious, diplomatic, aesthetic, fair', compatible: ['Gemini', 'Aquarius', 'Leo'] },
  { name: 'Scorpio',     symbol: '♏', dates: 'Oct 23–Nov 21', element: 'Water', modality: 'Fixed',    ruler: 'Pluto',   traits: 'Intense, passionate, transformative, powerful', compatible: ['Cancer', 'Pisces', 'Capricorn'] },
  { name: 'Sagittarius', symbol: '♐', dates: 'Nov 22–Dec 21', element: 'Fire',  modality: 'Mutable',  ruler: 'Jupiter', traits: 'Adventurous, optimistic, philosophical, free', compatible: ['Aries', 'Leo', 'Aquarius'] },
  { name: 'Capricorn',   symbol: '♑', dates: 'Dec 22–Jan 19', element: 'Earth', modality: 'Cardinal', ruler: 'Saturn',  traits: 'Ambitious, disciplined, responsible, structured', compatible: ['Taurus', 'Virgo', 'Scorpio'] },
  { name: 'Aquarius',    symbol: '♒', dates: 'Jan 20–Feb 18', element: 'Air',   modality: 'Fixed',    ruler: 'Uranus',  traits: 'Innovative, humanitarian, eccentric, visionary', compatible: ['Gemini', 'Libra', 'Sagittarius'] },
  { name: 'Pisces',      symbol: '♓', dates: 'Feb 19–Mar 20', element: 'Water', modality: 'Mutable',  ruler: 'Neptune', traits: 'Compassionate, dreamy, spiritual, boundless', compatible: ['Cancer', 'Scorpio', 'Taurus'] },
];

const ELEM_COLOR = { Fire: '#FF6B35', Earth: '#4CAF50', Air: '#87CEEB', Water: '#4FC3F7' };

function buildZodiacGrid() {
  const grid = document.getElementById('zodiacGrid');
  ZODIAC.forEach((z, i) => {
    const card = document.createElement('div');
    card.className = 'zodiac-card';
    card.innerHTML = `<span class="z-symbol">${z.symbol}</span><span class="z-name">${z.name}</span><span class="z-dates">${z.dates}</span>`;
    card.onclick = () => showDetail(z, card);
    grid.appendChild(card);
  });
}

let activeCard = null;

function showDetail(z, card) {
  if (activeCard) activeCard.classList.remove('active');
  activeCard = card;
  card.classList.add('active');
  const elemClass = `tag-${z.element.toLowerCase()}`;
  document.getElementById('detailInner').innerHTML = `
    <div class="detail-symbol">${z.symbol}</div>
    <div class="detail-info">
      <h3>${z.name}</h3>
      <p style="color:var(--gold);margin-bottom:0.5rem">${z.dates}</p>
      <p><strong>Traits:</strong> ${z.traits}</p>
      <p><strong>Ruler:</strong> ${z.ruler} &nbsp;|&nbsp; <strong>Modality:</strong> ${z.modality}</p>
      <div style="margin-top:0.7rem">
        <span class="tag ${elemClass}">${z.element}</span>
        ${z.compatible.map(s => `<span class="tag" style="color:var(--muted);border-color:var(--border)">♥ ${s}</span>`).join('')}
      </div>
    </div>`;
  document.getElementById('zodiacDetail').style.display = 'block';
}

function closeDetail() {
  document.getElementById('zodiacDetail').style.display = 'none';
  if (activeCard) { activeCard.classList.remove('active'); activeCard = null; }
}

buildZodiacGrid();

// ── Tabs ─────────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.demo-panel').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById(`tab-${name}`).classList.add('active');
}

// ── Horoscope fetch ───────────────────────────────────────────────────────────
async function fetchHoroscope() {
  const sign = document.getElementById('horoSign').value;
  const base = (document.getElementById('apiUrl').value || '').replace(/\/$/, '');
  const out = document.getElementById('horoOutput');

  if (!base) {
    out.innerHTML = `<div class="reading-card"><h4>✦ ${sign} — Sample Horoscope</h4><p style="color:var(--muted)">Enter your backend URL above to get a live AI-generated horoscope, or start your AstroSpace server with <code style="color:var(--gold)">python main.py</code> and point to <code style="color:var(--gold)">http://localhost:8000</code>.</p><p><strong>Quick start:</strong> pip install -r requirements.txt &amp;&amp; python main.py</p></div>`;
    return;
  }

  out.innerHTML = `<div class="reading-card"><p style="color:var(--muted)">⏳ Generating horoscope...</p></div>`;
  try {
    const res = await fetch(`${base}/api/v1/horoscope`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sun_sign: sign, weekly: false }),
    });
    const data = await res.json();
    out.innerHTML = `<div class="reading-card"><h4>✦ ${sign} — Daily Horoscope</h4><p style="white-space:pre-wrap;color:var(--muted)">${data.horoscope || data.detail}</p></div>`;
  } catch (e) {
    out.innerHTML = `<div class="reading-card"><p style="color:#FF6B6B">Could not reach backend: ${e.message}</p></div>`;
  }
}

// ── Chart SVG ────────────────────────────────────────────────────────────────
function drawChartWheel(planets) {
  const svg = document.getElementById('chartSvg');
  const cx = 200, cy = 200, R = 160, r = 80;
  const signs = ['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓'];
  const signColors = ['#FF6B35','#4CAF50','#87CEEB','#4FC3F7','#FFD700','#98FB98','#DDA0DD','#9B59B6','#FF7F50','#8FBC8F','#00CED1','#6A5ACD'];
  let html = '';

  // Outer ring segments (signs)
  signs.forEach((s, i) => {
    const a1 = (i * 30 - 90) * Math.PI / 180;
    const a2 = ((i + 1) * 30 - 90) * Math.PI / 180;
    const x1 = cx + R * Math.cos(a1), y1 = cy + R * Math.sin(a1);
    const x2 = cx + R * Math.cos(a2), y2 = cy + R * Math.sin(a2);
    const mx = cx + (R - 18) * Math.cos((a1 + a2) / 2);
    const my = cy + (R - 18) * Math.sin((a1 + a2) / 2);
    html += `<path d="M${cx},${cy} L${x1},${y1} A${R},${R} 0 0,1 ${x2},${y2} Z" fill="${signColors[i]}20" stroke="${signColors[i]}60" stroke-width="0.5"/>`;
    html += `<text x="${mx}" y="${my}" text-anchor="middle" dominant-baseline="middle" fill="${signColors[i]}" font-size="10">${s}</text>`;
  });

  // Inner circle
  html += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="rgba(10,8,32,0.8)" stroke="rgba(123,47,190,0.4)" stroke-width="1"/>`;

  // House lines
  for (let i = 0; i < 12; i++) {
    const a = (i * 30 - 90) * Math.PI / 180;
    html += `<line x1="${cx + r * Math.cos(a)}" y1="${cy + r * Math.sin(a)}" x2="${cx + R * Math.cos(a)}" y2="${cy + R * Math.sin(a)}" stroke="rgba(255,255,255,0.08)" stroke-width="0.5"/>`;
  }

  // Planet dots
  const pColors = { Sun: '#F4D03F', Moon: '#C0C0C0', Mercury: '#A0C4FF', Venus: '#FF69B4', Mars: '#FF4444', Jupiter: '#FFA500', Saturn: '#C5A028', Uranus: '#00CED1', Neptune: '#6A5ACD', Pluto: '#9B59B6' };
  (planets || [
    { name: 'Sun', abs_pos: 80 }, { name: 'Moon', abs_pos: 210 },
    { name: 'Venus', abs_pos: 50 }, { name: 'Mars', abs_pos: 130 },
    { name: 'Jupiter', abs_pos: 290 },
  ]).forEach((p, idx) => {
    const a = ((p.abs_pos || idx * 60) - 90) * Math.PI / 180;
    const pr = r - 20 - (idx % 3) * 8;
    const px = cx + pr * Math.cos(a), py = cy + pr * Math.sin(a);
    const col = pColors[p.name] || '#888';
    html += `<circle cx="${px}" cy="${py}" r="5" fill="${col}" stroke="rgba(0,0,0,0.5)" stroke-width="1"/>`;
    html += `<text x="${px}" y="${py - 8}" text-anchor="middle" fill="${col}" font-size="7">${p.name}</text>`;
  });

  svg.innerHTML = html;
}

async function fetchChart() {
  const base = (document.getElementById('apiUrl').value || '').replace(/\/$/, '');
  const out = document.getElementById('chartOutput');

  if (!base) {
    drawChartWheel(null);
    out.querySelector('.sample-label').textContent = 'Sample chart (connect backend for live data) ↓';
    return;
  }

  const d = document.getElementById('chartDate').value.split('-');
  const t = document.getElementById('chartTime').value.split(':');
  out.innerHTML = '<div class="reading-card"><p style="color:var(--muted)">⏳ Calculating chart...</p></div>';

  try {
    const res = await fetch(`${base}/api/v1/chart`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('chartName').value,
        year: +d[0], month: +d[1], day: +d[2],
        hour: +t[0], minute: +t[1],
        city: document.getElementById('chartCity').value,
        nation: 'US',
      }),
    });
    const data = await res.json();
    const chart = data.data;
    out.innerHTML = `
      <div class="sample-label">Live birth chart ↓</div>
      <div class="chart-viz">
        <svg id="chartSvg" viewBox="0 0 400 400" width="280" height="280"></svg>
        <div class="chart-legend" id="chartLegend">
          <div class="legend-item"><span class="planet-dot sun"></span><strong>Sun</strong> in ${chart.sun_sign}</div>
          <div class="legend-item"><span class="planet-dot moon"></span><strong>Moon</strong> in ${chart.moon_sign}</div>
          <div class="legend-item"><span class="planet-dot asc"></span><strong>Ascendant:</strong> ${chart.ascendant}</div>
          ${(chart.planets || []).slice(2, 5).map(p =>
            `<div class="legend-item"><span class="planet-dot" style="background:#888"></span>${p.name} in ${p.sign}</div>`
          ).join('')}
        </div>
      </div>`;
    drawChartWheel(chart.planets);
  } catch (e) {
    out.innerHTML = `<div class="reading-card"><p style="color:#FF6B6B">Error: ${e.message}</p></div>`;
  }
}

// ── Compatibility ─────────────────────────────────────────────────────────────
const COMPAT_SCORES = {
  'Fire-Fire': 85, 'Fire-Air': 80, 'Fire-Earth': 55, 'Fire-Water': 50,
  'Earth-Earth': 82, 'Earth-Water': 78, 'Earth-Air': 60,
  'Air-Air': 80, 'Air-Water': 58,
  'Water-Water': 88,
};

const ELEM = { Aries:'Fire', Taurus:'Earth', Gemini:'Air', Cancer:'Water', Leo:'Fire', Virgo:'Earth', Libra:'Air', Scorpio:'Water', Sagittarius:'Fire', Capricorn:'Earth', Aquarius:'Air', Pisces:'Water' };

function checkCompat() {
  const s1 = document.getElementById('sign1').value;
  const s2 = document.getElementById('sign2').value;
  const e1 = ELEM[s1], e2 = ELEM[s2];
  const key = [e1, e2].sort().join('-');
  const score = COMPAT_SCORES[key] || 65;
  const pct = Math.round(score / 100 * 263.9);
  const sym1 = ZODIAC.find(z => z.name === s1)?.symbol || '';
  const sym2 = ZODIAC.find(z => z.name === s2)?.symbol || '';

  const out = document.getElementById('compatOutput');
  const desc = score >= 80 ? 'A harmonious and flowing connection with natural understanding.' :
               score >= 65 ? 'A dynamic pairing with both chemistry and growth opportunities.' :
               'A challenging but potentially transformative connection.';

  out.innerHTML = `
    <div class="compat-card">
      <div class="compat-score">
        <div class="score-circle">
          <svg viewBox="0 0 100 100" width="120" height="120">
            <circle cx="50" cy="50" r="42" fill="none" stroke="#1a0a3a" stroke-width="10"/>
            <circle cx="50" cy="50" r="42" fill="none" stroke="#9B59B6" stroke-width="10"
              stroke-dasharray="263.9" stroke-dashoffset="${263.9 - pct}"
              stroke-linecap="round" transform="rotate(-90 50 50)"/>
          </svg>
          <div class="score-num">${score}</div>
        </div>
        <div>
          <h4>${s1} ${sym1} + ${s2} ${sym2}</h4>
          <p class="compat-summary">${desc}</p>
        </div>
      </div>
      <div class="compat-details">
        <div class="compat-row positive">🔥 <strong>Elements:</strong> ${e1} meets ${e2}</div>
        <div class="compat-row positive">♥ Connect your AstroSpace backend for a full AI synastry reading</div>
      </div>
    </div>`;
}

// ── Code copy ──────────────────────────────────────────────────────────────────
function copyCode(btn) {
  const code = btn.closest('.code-block').querySelector('code').innerText;
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
}

// ── Init ───────────────────────────────────────────────────────────────────────
drawChartWheel(null);
