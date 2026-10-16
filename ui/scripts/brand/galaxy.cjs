// Siddha mark: the Nine-Arm Galaxy. Two dotted spiral arms, nine bright graha
// stars, a glowing core, on space black. One generator feeds every icon PNG
// so the sizes can't drift apart.
const TAU = Math.PI * 2;
function rng(seed) { let x = seed; return () => { x = (x * 9301 + 49297) % 233280; return x / 233280; }; }
function galaxySvg({ background = true, animated = false, size = null, idPrefix = 'sg', bold = false, arms: showArms = true, field: showField = true, zoom: zoomOverride = null, theme = 'night' } = {}) {
  const p = idPrefix;
  // Night: space black. Day: the app's cream ground, with deeper golds so the
  // arms hold contrast. Mono: white silhouette for Android themed icons.
  const c = {
    night: { dot: '#e9b949', graha: '#fff4d6', coreB: '#ffe7a6', star: '#fff', starK: 1, bg: ['#0d0b18', '#05050b', '#000000'], haze: ['#e9b949', '.18', '#5b3fa0', '.07'], coreDot: '#fff', sphere: ['#ffffff', '#ffe9a8', '#e0a93a'], halo: ['#ffe7a6', '.55'] },
    day: { dot: '#c18d1a', graha: '#8a5d00', coreB: '#f2c24f', star: '#6b5440', starK: 0.55, bg: ['#fffaf1', '#faf4e8', '#efe5d2'], haze: ['#e9b949', '.3', '#b27234', '.08'], coreDot: '#fffaf0', sphere: ['#fffaf0', '#f0c04f', '#a8740a'], halo: ['#f2c24f', '.6'] },
    mono: { dot: '#fff', graha: '#fff', coreB: '#fff', star: '#fff', starK: 0, bg: ['#000', '#000', '#000'], haze: ['#fff', '0', '#fff', '0'], coreDot: '#fff', sphere: ['#fff', '#fff', '#fff'], halo: ['#fff', '0'] },
  }[theme];
  // The home-screen icon is seen at 29-60 px, so the galaxy fills more of the
  // tile and the arm dots are a touch heavier; the motion version keeps the
  // fine detail. The arms are a fine dotted trail; the eight arm grahas are
  // drawn separately on top as small lit spheres with a soft halo, so they
  // read as stars rather than flat discs.
  const dot = bold ? 1.15 : 1, zoom = zoomOverride ?? (bold ? 1.14 : 1);
  const spiral = (arm, t) => {
    const a = arm * Math.PI + t * 1.42 * TAU, r = 4 + t * 38;
    return [50 + r * Math.cos(a), 50 + r * Math.sin(a) * 0.78];
  };
  const GRAHA_T = [6, 16, 26, 36].map((k) => k / 45);
  let arms = '', grahas = '';
  for (let arm = 0; arm < 2; arm++) {
    for (let k = 0; k < 64; k++) {
      const t = k / 63;
      if (GRAHA_T.some((g) => Math.abs(g - t) < 0.022)) continue;
      const [x, y] = spiral(arm, t);
      arms += `<circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="${((0.95 - t * 0.6) * dot).toFixed(2)}" fill="${c.dot}" opacity="${(1 - t * 0.7).toFixed(2)}"/>`;
    }
    GRAHA_T.forEach((t, i) => {
      const [x, y] = spiral(arm, t), n = arm * 4 + i;
      const cls = ` class="${p}-graha" style="animation-delay:${(n % 9) * 0.37}s"`;
      const body = (1.5 - t * 0.35) * (bold ? 1.1 : 1);
      grahas += `<g${cls}><circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="${(body * 2.6).toFixed(2)}" fill="url(#${p}-halo)"/><circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="${body.toFixed(2)}" fill="url(#${p}-sphere)"/></g>`;
    });
  }
  // Ninth graha: the core itself, so 4 + 4 bright arm stars + core = 9.
  const r = rng(13); let field = '';
  for (let i = 0; i < 26; i++) {
    const x = (r() * 100).toFixed(1), y = (r() * 100).toFixed(1);
    const cls = animated ? ` class="${p}-tw" style="animation-delay:${(i * 0.29 % 3).toFixed(2)}s"` : '';
    field += `<circle${cls} cx="${x}" cy="${y}" r="${(0.3 + (i % 3) * 0.18).toFixed(2)}" fill="${c.star}" opacity="${((0.25 + (i % 4) * 0.15) * c.starK).toFixed(2)}"/>`;
  }
  const style = animated ? `<style>
    .${p}-spin { transform-origin: 50px 50px; animation: ${p}-spin 48s linear infinite; }
    .${p}-graha { transform-box: fill-box; transform-origin: center; animation: ${p}-pulse 3.3s ease-in-out infinite; }
    .${p}-tw { animation: ${p}-tw 3s ease-in-out infinite; }
    .${p}-core { transform-origin: 50px 50px; animation: ${p}-breathe 4.8s ease-in-out infinite; }
    @keyframes ${p}-spin { to { transform: rotate(360deg); } }
    @keyframes ${p}-pulse { 0%,100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.3); opacity: .75; } }
    @keyframes ${p}-tw { 0%,100% { opacity: .15; } 50% { opacity: .85; } }
    @keyframes ${p}-breathe { 0%,100% { transform: scale(1); opacity: .9; } 50% { transform: scale(1.18); opacity: 1; } }
    @media (prefers-reduced-motion: reduce) { .${p}-spin, .${p}-graha, .${p}-tw, .${p}-core { animation: none; } }
  </style>` : '';
  const dims = size ? ` width="${size}" height="${size}"` : '';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"${dims} role="img" aria-label="Siddha">${style}<defs>
  <radialGradient id="${p}-bg" cx="50%" cy="46%" r="75%"><stop offset="0" stop-color="${c.bg[0]}"/><stop offset=".6" stop-color="${c.bg[1]}"/><stop offset="1" stop-color="${c.bg[2]}"/></radialGradient>
  <radialGradient id="${p}-haze" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="${c.haze[0]}" stop-opacity="${c.haze[1]}"/><stop offset=".55" stop-color="${c.haze[2]}" stop-opacity="${c.haze[3]}"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
  <radialGradient id="${p}-core"><stop offset="0" stop-color="#ffffff"/><stop offset=".3" stop-color="${c.coreB}"/><stop offset="1" stop-color="#e9b949" stop-opacity="0"/></radialGradient>
  <radialGradient id="${p}-sphere" cx="38%" cy="34%" r="70%"><stop offset="0" stop-color="${c.sphere[0]}"/><stop offset=".45" stop-color="${c.sphere[1]}"/><stop offset="1" stop-color="${c.sphere[2]}"/></radialGradient>
  <radialGradient id="${p}-halo"><stop offset="0" stop-color="${c.halo[0]}" stop-opacity="${c.halo[1]}"/><stop offset="1" stop-color="${c.halo[0]}" stop-opacity="0"/></radialGradient>
  <filter id="${p}-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="0.7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>${background ? `<rect width="100" height="100" fill="url(#${p}-bg)"/>` : ''}${showField ? field : ''}${showArms ? `<g transform="translate(50 50) scale(${zoom}) translate(-50 -50)"><ellipse cx="50" cy="50" rx="44" ry="36" fill="url(#${p}-haze)"/><g class="${p}-spin"><g transform="rotate(-24 50 50)"><g filter="url(#${p}-glow)">${arms}</g>${grahas}</g></g><g class="${p}-core"><circle cx="50" cy="50" r="11" fill="url(#${p}-core)"/><circle cx="50" cy="50" r="2.6" fill="${c.coreDot}"/></g></g>` : ''}</svg>`;
}
module.exports = { galaxySvg };
