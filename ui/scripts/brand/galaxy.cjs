// Siddha mark: the Nine-Arm Galaxy. Two dotted spiral arms, nine bright graha
// stars, a glowing core, on space black. One generator feeds every icon PNG
// so the sizes can't drift apart.
const TAU = Math.PI * 2;
function rng(seed) { let x = seed; return () => { x = (x * 9301 + 49297) % 233280; return x / 233280; }; }
function galaxySvg({ background = true, animated = false, size = null, idPrefix = 'sg', bold = false, arms: showArms = true, field: showField = true, zoom: zoomOverride = null } = {}) {
  const p = idPrefix;
  const c = { dot: '#e9b949', graha: '#fff4d6', coreB: '#ffe7a6', star: '#fff', starK: 1 };
  // The home-screen icon is seen at 29-60 px, so its dots are drawn heavier and
  // the galaxy fills more of the tile; the motion version keeps the fine detail.
  const dot = bold ? 1.4 : 1, zoom = zoomOverride ?? (bold ? 1.14 : 1);
  let arms = '';
  for (let a2 = 0; a2 < 2; a2++) for (let k = 0; k < 46; k++) {
    const t = k / 45, a = a2 * Math.PI + t * 1.42 * TAU, r = 4 + t * 38;
    const x = 50 + r * Math.cos(a), y = 50 + r * Math.sin(a) * 0.78, big = k % 10 === 6;
    const cls = big ? ` class="${p}-graha" style="animation-delay:${((k + a2 * 23) % 9) * 0.37}s"` : '';
    arms += `<circle${cls} cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="${((big ? 2.1 : 1.15 - t * 0.7) * dot).toFixed(2)}" fill="${big ? c.graha : c.dot}" opacity="${big ? 1 : (1 - t * 0.65).toFixed(2)}"/>`;
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
  <radialGradient id="${p}-bg" cx="50%" cy="46%" r="75%"><stop offset="0" stop-color="#0d0b18"/><stop offset=".6" stop-color="#05050b"/><stop offset="1" stop-color="#000000"/></radialGradient>
  <radialGradient id="${p}-haze" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#e9b949" stop-opacity=".18"/><stop offset=".55" stop-color="#5b3fa0" stop-opacity=".07"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
  <radialGradient id="${p}-core"><stop offset="0" stop-color="#ffffff"/><stop offset=".3" stop-color="${c.coreB}"/><stop offset="1" stop-color="#e9b949" stop-opacity="0"/></radialGradient>
  <filter id="${p}-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>${background ? `<rect width="100" height="100" fill="url(#${p}-bg)"/>` : ''}${showField ? field : ''}${showArms ? `<g transform="translate(50 50) scale(${zoom}) translate(-50 -50)"><ellipse cx="50" cy="50" rx="44" ry="36" fill="url(#${p}-haze)"/><g class="${p}-spin"><g filter="url(#${p}-glow)" transform="rotate(-24 50 50)">${arms}</g></g><g class="${p}-core"><circle cx="50" cy="50" r="11" fill="url(#${p}-core)"/><circle cx="50" cy="50" r="2.6" fill="#fff"/></g></g>` : ''}</svg>`;
}
module.exports = { galaxySvg };
