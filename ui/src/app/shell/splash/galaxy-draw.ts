// @ts-nocheck: a verbatim port of the icon drawing (plain JS); typed at the export.
// The Siddha galaxy, drawn live for the splash screen.
//
// This is drawGalaxy from ui/scripts/brand/luminous.cjs (the code that draws
// the app icon), so the splash and the icon are the same picture. Two
// additions: `tilt`/`squash` let the splash draw it face-on and tilt it with
// CSS, so it can spin without the tilt spinning too; and a `day` theme draws
// it as ink on cream (multiply) instead of light on black (lighter).
// Keep the two copies in step when the icon changes.

export interface GalaxyOptions {
  theme?: 'night' | 'day' | 'mono';
  background?: boolean;
  arms?: boolean;
  zoom?: number;
  weight?: number;
  shine?: number;
  star?: number;
  tilt?: number;
  squash?: number;
}

/* eslint-disable */
export function drawGalaxy(cv: HTMLCanvasElement, opt: GalaxyOptions): void {

  const TAU = Math.PI * 2;
  let seed = 7;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const gauss = () => (rnd() + rnd() + rnd() - 1.5) / 1.5;
  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const mix = (stops, off) => { // off in [-2, 2] across the arm
    const f = Math.max(0, Math.min(3.999, off + 2)), i = Math.floor(f), k = f - i;
    const a = hex(stops[i]), b = hex(stops[i + 1]);
    return 'rgb(' + a.map((v, j) => Math.round(v + (b[j] - v) * k)).join(',') + ')';
  };
  const T = {
    night: { disp: ['#9a4cff', '#ffae2e', '#fff4dc', '#ffd36a', '#ff6a4a'], rings: ['#ffd36a', '#9a4cff', '#ff6a4a', '#7fd0ff'], hot: '#fffaf0', core: ['#ffffff', '#ffe7a6', '#e07a3a'], halo: '#ffd98a', bg: ['#0d0b18', '#05050b', '#000000'], bloom: [0.45, 0.8], glint: 'aa' },
    day: { disp: ['#9a7bc4', '#d49a5a', '#a0684a', '#e0b66a', '#cf8a6e'], rings: ['#d2a878', '#9a7bc4', '#cf8a6e', '#86a9c0'], hot: '#8a5236', core: ['#fff3c4', '#f0b84a', '#c0661f'], halo: '#d99a3c', bg: null, bloom: [0.25, 0.45], glint: '88' },
    mono: { disp: ['#ffffff', '#ffffff', '#ffffff', '#ffffff', '#ffffff'], rings: ['#ffffff'], hot: '#ffffff', core: ['#ffffff', '#ffffff', '#ffffff'], halo: '#ffffff', bg: null, bloom: [0.3, 0.6], glint: 'aa' },
  }[opt.theme || 'night'];
  const S = cv.width, ctx = cv.getContext('2d');
  const OP = opt.theme === 'day' ? 'multiply' : 'lighter';
  const u = S / 100 * (opt.zoom || 1.14), cx = S / 2, cy = S / 2, rot = (opt.tilt ?? -24) * Math.PI / 180;
  const W = S / 1024 * (opt.weight || 1);
  // Shine: how much light the drawing gives off (bloom, core, spines, stars).
  // 1 is the original gold icon; render-icons.cjs sets the shipped level.
  const SH = opt.shine || 1;
  const map = (x, y) => { const dx = x - 50, dy = y - 50; return [cx + (dx * Math.cos(rot) - dy * Math.sin(rot)) * u, cy + (dx * Math.sin(rot) + dy * Math.cos(rot)) * u]; };
  const spiral = (arm, t, dr = 0, da = 0) => { const a = arm * Math.PI + t * 1.42 * TAU + da, r = 4 + t * 38 + dr; return map(50 + r * Math.cos(a), 50 + r * Math.sin(a) * (opt.squash ?? 0.78)); };
  if (opt.background !== false && T.bg) {
    const g = ctx.createRadialGradient(cx, cy * 0.92, 0, cx, cy, S * 0.75);
    g.addColorStop(0, T.bg[0]); g.addColorStop(0.6, T.bg[1]); g.addColorStop(1, T.bg[2]);
    ctx.fillStyle = g; ctx.fillRect(0, 0, S, S);
  }
  if (opt.arms === false) return;
  // Light layer, drawn apart and then bloomed onto the ground.
  const L = document.createElement('canvas') as HTMLCanvasElement; L.width = L.height = S;
  const l = L.getContext('2d');
  l.globalCompositeOperation = OP;
  // Faint orbit rings behind the arms.
  for (let i = 0; i < 9; i++) {
    const rr = 14 + i * 4.2 + gauss() * 0.8;
    l.beginPath();
    for (let k = 0; k <= 180; k++) { const a = k / 180 * TAU, [x, y] = map(50 + rr * Math.cos(a), 50 + rr * Math.sin(a) * (opt.squash ?? 0.78)); k ? l.lineTo(x, y) : l.moveTo(x, y); }
    l.strokeStyle = T.rings[i % T.rings.length]; l.globalAlpha = 0.05 + rnd() * 0.05; l.lineWidth = Math.max(0.6, 0.75 * W); l.stroke();
  }
  // Ribbon strands: many faint ones plus eight saturated edge leads per arm.
  const N = 90, SEG = 160, CH = 8;
  for (let arm = 0; arm < 2; arm++) {
    for (let s = 0; s < N + 8; s++) {
      const lead = s >= N, sgn = s % 2 ? 1 : -1;
      const off = lead ? sgn * (1.3 + rnd() * 0.7) : Math.max(-2, Math.min(2, gauss() * 1.4));
      const phase = gauss() * 0.03, col = mix(T.disp, off);
      const tEnd = 0.75 + rnd() * 0.3, tStart = rnd() * 0.08;
      const w = (lead ? 1.4 + rnd() * 1.2 : 0.3 + rnd() * 0.9) * W;
      let pts = [];
      for (let k = 0; k <= SEG; k++) {
        const t = tStart + (tEnd - tStart) * k / SEG;
        const spread = 0.25 + Math.pow(Math.sin(Math.min(1, t) * Math.PI), 0.7) * 2.6; // widest mid-arm
        pts.push(spiral(arm, t, off * spread, phase));
        if (pts.length > CH || k === SEG) {
          const fade = Math.min(1, k / 12) * Math.pow(1 - k / SEG, 0.5);
          l.globalAlpha = Math.min(1, (lead ? 0.85 : 0.06 + 0.5 * Math.pow(Math.abs(off) / 2, 1.5)) * fade * (1 - t * 0.2) * (lead ? SH : Math.sqrt(SH)));
          l.strokeStyle = col; l.lineWidth = w * (1.4 - t * 0.6); l.lineCap = 'butt'; l.lineJoin = 'round';
          l.beginPath(); pts.forEach((p, i) => (i ? l.lineTo(p[0], p[1]) : l.moveTo(p[0], p[1]))); l.stroke();
          pts = [pts[pts.length - 1]];
        }
      }
    }
    // Bright spine.
    let prev = null;
    for (let k = 0; k <= SEG; k++) {
      const t = k / SEG * 0.98, p = spiral(arm, t);
      if (prev) { l.globalAlpha = Math.min(1, 0.75 * SH * (1 - t * 0.85)); l.strokeStyle = T.hot; l.lineWidth = (1.6 - t * 1.2) * W * Math.sqrt(SH); l.lineCap = 'round'; l.beginPath(); l.moveTo(prev[0], prev[1]); l.lineTo(p[0], p[1]); l.stroke(); }
      prev = p;
    }
  }
  // Core, with a thin flare along the galaxy's tilt.
  l.globalAlpha = 1;
  const CR = 9 * u * Math.sqrt(SH);
  let g = l.createRadialGradient(cx, cy, 0, cx, cy, CR);
  g.addColorStop(0, T.core[0]); g.addColorStop(0.12, T.core[1]); g.addColorStop(0.4, T.core[2] + '44'); g.addColorStop(1, T.core[2] + '00');
  l.fillStyle = g; l.beginPath(); l.arc(cx, cy, CR, 0, TAU); l.fill();
  l.save(); l.translate(cx, cy); l.rotate(rot); l.scale(1, 0.035);
  g = l.createRadialGradient(0, 0, 0, 0, 0, 40 * u); g.addColorStop(0, T.hot + 'cc'); g.addColorStop(0.4, T.halo + '44'); g.addColorStop(1, T.halo + '00');
  l.fillStyle = g; l.beginPath(); l.arc(0, 0, 40 * u, 0, TAU); l.fill(); l.restore();
  // Eight graha stars as small flare points, on their own layer so the
  // arm bloom doesn't swell them into blobs.
  const St = document.createElement('canvas') as HTMLCanvasElement; St.width = St.height = S;
  const st = St.getContext('2d'); st.globalCompositeOperation = l.globalCompositeOperation;
  const GT = [6, 16, 26, 36].map((k) => k / 45);
  for (let arm = 0; arm < 2; arm++) GT.forEach((t) => {
    const [x, y] = spiral(arm, t), b = (0.62 - t * 0.18) * u * (opt.star || 1) * Math.pow(SH, 0.35);
    const h = st.createRadialGradient(x, y, 0, x, y, b * 2.6);
    h.addColorStop(0, '#ffffff'); h.addColorStop(0.12, T.hot);
    h.addColorStop(0.3, T.halo + '66'); h.addColorStop(1, T.halo + '00');
    st.fillStyle = h; st.beginPath(); st.arc(x, y, b * 2.6, 0, TAU); st.fill();
    st.save(); st.translate(x, y); st.rotate(rot);
    for (const sc of [[1, 0.06], [0.06, 1]]) {
      st.save(); st.scale(sc[0], sc[1]);
      const q = st.createRadialGradient(0, 0, 0, 0, 0, b * 3.6); q.addColorStop(0, T.hot + T.glint); q.addColorStop(1, T.hot + '00');
      st.fillStyle = q; st.beginPath(); st.arc(0, 0, b * 3.6, 0, TAU); st.fill(); st.restore();
    }
    st.restore();
  });
  // Bloom: a wide and a tight blurred copy under the sharp layer.
  ctx.globalCompositeOperation = OP;
  ctx.filter = `blur(${S / 40}px)`; ctx.globalAlpha = Math.min(1, T.bloom[0] * SH); ctx.drawImage(L, 0, 0);
  ctx.filter = `blur(${S / 160}px)`; ctx.globalAlpha = Math.min(1, T.bloom[1] * SH); ctx.drawImage(L, 0, 0);
  if (SH > 1 && T.bg) {
    // A soft gold glow around the core, so the whole mark reads as lit.
    const halo = ctx.createRadialGradient(cx, cy, 0, cx, cy, S * 0.42);
    const a = Math.round(Math.min(0.45, 0.22 * (SH - 1)) * 255).toString(16).padStart(2, '0');
    halo.addColorStop(0, T.halo + a); halo.addColorStop(1, T.halo + '00');
    ctx.filter = 'none'; ctx.globalAlpha = 1; ctx.fillStyle = halo; ctx.fillRect(0, 0, S, S);
  }
  ctx.filter = 'none'; ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = OP;
  ctx.drawImage(L, 0, 0);
  ctx.globalCompositeOperation = OP;
  ctx.filter = `blur(${S / 220}px)`; ctx.globalAlpha = 0.5; ctx.drawImage(St, 0, 0);
  ctx.filter = 'none'; ctx.globalAlpha = 1; ctx.drawImage(St, 0, 0);
  ctx.globalCompositeOperation = 'source-over';
}
