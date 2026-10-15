// Renders every Siddha icon and splash PNG from the galaxy master drawing.
// Run from ui/: node scripts/brand/render-icons.cjs && python3 scripts/brand/finish_icons.py
// (set CHROMIUM_PATH if Playwright has no bundled browser).
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const { galaxySvg } = require('./galaxy.cjs');

const UI = path.resolve(__dirname, '../..'), R = UI + '/android/app/src/main/res', OUT = require('os').tmpdir() + '/siddha-icons';
fs.mkdirSync(OUT, { recursive: true });
// Each job: [file, w, h, html-body-svg-builder]
const icon = () => galaxySvg({ bold: true });
const fgOnly = () => galaxySvg({ bold: true, background: false, field: false, idPrefix: 'fg' });
const bgOnly = () => galaxySvg({ bold: true, arms: false, idPrefix: 'bgl' });
const jobs = [];
const page = (w, h, inner, bg = 'transparent') => `<html><body style="margin:0;width:${w}px;height:${h}px;background:${bg};display:grid;place-items:center;overflow:hidden">${inner}</body></html>`;
const sized = (svg, s) => svg.replace('<svg ', `<svg width="${s}" height="${s}" `);
// iOS / Capacitor master icon (opaque, no rounding: the OS masks it)
for (const f of [UI + '/assets/icon.png', UI + '/ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png']) jobs.push([f, 1024, 1024, page(1024, 1024, sized(icon(), 1024), '#000')]);
// PWA icons
for (const s of [48, 72, 96, 128, 192, 256, 512]) jobs.push([OUT + `/icon-${s}.png`, s, s, page(s, s, sized(icon(), s), '#000')]);
jobs.push([OUT + '/fav-256.png', 256, 256, page(256, 256, sized(icon(), 256), '#000')]);
// Android legacy (square + round) and adaptive layers
const dens = { ldpi: .75, mdpi: 1, hdpi: 1.5, xhdpi: 2, xxhdpi: 3, xxxhdpi: 4 };
for (const [d, k] of Object.entries(dens)) {
  const s = Math.round(48 * k), a = Math.round(108 * k);
  jobs.push([`${R}/mipmap-${d}/ic_launcher.png`, s, s, page(s, s, `<div style="width:${s}px;height:${s}px;border-radius:${s * .18}px;overflow:hidden">${sized(icon(), s)}</div>`)]);
  jobs.push([`${R}/mipmap-${d}/ic_launcher_round.png`, s, s, page(s, s, `<div style="width:${s}px;height:${s}px;border-radius:50%;overflow:hidden">${sized(icon(), s)}</div>`)]);
  // Background layer: the full 108dp canvas of space black + star field.
  jobs.push([`${R}/mipmap-${d}/ic_launcher_background.png`, a, a, page(a, a, sized(bgOnly(), a), '#000')]);
  // Foreground: the galaxy kept inside the 72dp visible circle (spec: 66dp safe zone).
  jobs.push([`${R}/mipmap-${d}/ic_launcher_foreground.png`, a, a, page(a, a, sized(fgOnly(), Math.round(a * 70 / 108)))]);
}
// Splash images: space black with the galaxy centred at ~28% of the short side.
// Stars spread over the whole canvas (the same seeded sky the in-app intro draws).
function sky(w, h) {
  let seed = 29; const next = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
  const k = Math.min(w, h) / 390; let c = '';
  for (let i = 0; i < 140; i++) { const x = next() * w, y = next() * h; c += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${((0.3 + (i % 3) * 0.18) * 2.2 * k).toFixed(2)}" fill="#fff" opacity="${(0.25 + (i % 4) * 0.15) * .8}"/>`; }
  return `<svg width="${w}" height="${h}" style="position:absolute;inset:0">${c}</svg>`;
}
const splash = (w, h) => page(w, h, sky(w, h) + `<div style="position:relative">${sized(galaxySvg({ background: false, field: false, idPrefix: 'sp' }), Math.round(Math.min(w, h) * .3))}</div>`, 'radial-gradient(circle at 50% 46%, #0d0b18, #05050b 60%, #000)');
for (const dir of fs.readdirSync(R).filter(d => d.startsWith('drawable'))) {
  const f = `${R}/${dir}/splash.png`; if (!fs.existsSync(f)) continue;
  const { w, h } = JSON.parse(require('child_process').execSync(`python3 -c "from PIL import Image;i=Image.open('${f}');print('{\\"w\\":%d,\\"h\\":%d}'%i.size)"`).toString());
  jobs.push([f, w, h, splash(w, h)]);
}
jobs.push([UI + '/assets/splash.png', 1024, 1024, splash(1024, 1024)]);
const IS = UI + '/ios/App/App/Assets.xcassets/Splash.imageset';
for (const f of fs.readdirSync(IS).filter(f => f.endsWith('.png'))) { const s = f.includes('@1x') ? 1366 : 2732; jobs.push([`${IS}/${f}`, s, s, splash(s, s)]); }
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const pg = await b.newPage();
  for (const [f, w, h, html] of jobs) {
    await pg.setViewportSize({ width: w, height: h }); await pg.setContent(html);
    await pg.screenshot({ path: f, omitBackground: true, clip: { x: 0, y: 0, width: w, height: h } });
  }
  await b.close(); console.log(jobs.length, 'rendered');
})();
