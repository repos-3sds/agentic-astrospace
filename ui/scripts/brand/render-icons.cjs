// Renders every Siddha app icon PNG from the galaxy master drawing.
// Run from ui/: node scripts/brand/render-icons.cjs && python3 scripts/brand/finish_icons.py
// (set CHROMIUM_PATH if Playwright has no bundled browser).
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const { galaxySvg } = require('./galaxy.cjs');

const UI = path.resolve(__dirname, '../..'), R = UI + '/android/app/src/main/res', OUT = require('os').tmpdir() + '/siddha-icons';
fs.mkdirSync(OUT, { recursive: true });
// Each job: [file, w, h, html]. Two themes: night (space black, the default)
// and day (cream), plus a white silhouette for Android 13+ themed icons.
const icon = (theme = 'night') => galaxySvg({ bold: true, theme, idPrefix: 'i' + theme });
const fgOnly = (theme = 'night') => galaxySvg({ bold: true, theme, background: false, field: false, idPrefix: 'fg' + theme });
const bgOnly = (theme = 'night') => galaxySvg({ bold: true, theme, arms: false, idPrefix: 'bg' + theme });
const BG = { night: '#000', day: '#faf4e8' };
const jobs = [];
const page = (w, h, inner, bg = 'transparent') => `<html><body style="margin:0;width:${w}px;height:${h}px;background:${bg};display:grid;place-items:center;overflow:hidden">${inner}</body></html>`;
const sized = (svg, s) => svg.replace('<svg ', `<svg width="${s}" height="${s}" `);
const full = (theme, s) => page(s, s, sized(icon(theme), s), BG[theme]);
// iOS (opaque, no rounding: the OS masks it). The primary icon carries day,
// dark and tinted appearances so iOS 18 follows the system; AppIcon-Day and
// AppIcon-Night are the alternates the in-app theme switches between.
const X = UI + '/ios/App/App/Assets.xcassets';
jobs.push([UI + '/assets/icon.png', 1024, 1024, full('night', 1024)]);
jobs.push([`${X}/AppIcon.appiconset/AppIcon-512@2x.png`, 1024, 1024, full('day', 1024)]);
jobs.push([`${X}/AppIcon.appiconset/AppIcon-Dark.png`, 1024, 1024, full('night', 1024)]);
jobs.push([`${X}/AppIcon.appiconset/AppIcon-Tinted.png`, 1024, 1024, page(1024, 1024, sized(galaxySvg({ bold: true, theme: 'mono', field: false, idPrefix: 'tint' }), 1024), '#000')]);
jobs.push([`${X}/AppIcon-Day.appiconset/AppIcon-Day.png`, 1024, 1024, full('day', 1024)]);
jobs.push([`${X}/AppIcon-Night.appiconset/AppIcon-Night.png`, 1024, 1024, full('night', 1024)]);
// PWA icons
for (const s of [48, 72, 96, 128, 192, 256, 512]) jobs.push([OUT + `/icon-${s}.png`, s, s, full('night', s)]);
jobs.push([OUT + '/fav-256.png', 256, 256, full('night', 256)]);
// Android legacy (square + round) and adaptive layers, per theme.
const dens = { ldpi: .75, mdpi: 1, hdpi: 1.5, xhdpi: 2, xxhdpi: 3, xxxhdpi: 4 };
for (const [d, k] of Object.entries(dens)) {
  const s = Math.round(48 * k), a = Math.round(108 * k);
  for (const theme of ['night', 'day']) {
    const n = theme === 'night' ? 'ic_launcher' : 'ic_launcher_day';
    jobs.push([`${R}/mipmap-${d}/${n}.png`, s, s, page(s, s, `<div style="width:${s}px;height:${s}px;border-radius:${s * .18}px;overflow:hidden">${sized(icon(theme), s)}</div>`)]);
    jobs.push([`${R}/mipmap-${d}/${n}_round.png`, s, s, page(s, s, `<div style="width:${s}px;height:${s}px;border-radius:50%;overflow:hidden">${sized(icon(theme), s)}</div>`)]);
    // Background layer: the full 108dp canvas of ground + star field.
    jobs.push([`${R}/mipmap-${d}/${n}_background.png`, a, a, page(a, a, sized(bgOnly(theme), a), BG[theme])]);
    // Foreground: the galaxy kept inside the 72dp visible circle (spec: 66dp safe zone).
    jobs.push([`${R}/mipmap-${d}/${n}_foreground.png`, a, a, page(a, a, sized(fgOnly(theme), Math.round(a * 70 / 108)))]);
  }
  // Themed-icon silhouette (Android 13+), shared by both launchers.
  jobs.push([`${R}/mipmap-${d}/ic_launcher_monochrome.png`, a, a, page(a, a, sized(galaxySvg({ bold: true, theme: 'mono', background: false, field: false, idPrefix: 'mono' }), Math.round(a * 70 / 108)))]);
}
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const pg = await b.newPage();
  for (const [f, w, h, html] of jobs) {
    await pg.setViewportSize({ width: w, height: h }); await pg.setContent(html);
    await pg.screenshot({ path: f, omitBackground: true, clip: { x: 0, y: 0, width: w, height: h } });
  }
  await b.close(); console.log(jobs.length, 'rendered');
})();
