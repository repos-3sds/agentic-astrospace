// Renders every Siddha app icon PNG from the galaxy master drawing.
// Run from ui/: node scripts/brand/render-icons.cjs && python3 scripts/brand/finish_icons.py
// (set CHROMIUM_PATH if Playwright has no bundled browser).
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const { luminousPage } = require('./luminous.cjs');

const UI = path.resolve(__dirname, '../..'), R = UI + '/android/app/src/main/res', OUT = require('os').tmpdir() + '/siddha-icons';
fs.mkdirSync(OUT, { recursive: true });
// Each job: [file, w, h, html]. Two themes: night (space black, the default)
// and day (cream), plus a white silhouette for themed / tinted icons.
const BG = { night: '#000', day: '#faf4e8' };
const MONO = { theme: 'mono', background: false, weight: 2.2, star: 1.3 };
const full = (theme, s, o = {}) => luminousPage(s, { theme, fill: BG[theme], ...o });
const jobs = [];
// iOS (opaque, no rounding: the OS masks it). The primary icon carries day,
// dark and tinted appearances so iOS 18 follows the system; AppIcon-Day and
// AppIcon-Night are the alternates the in-app theme switches between.
const X = UI + '/ios/App/App/Assets.xcassets';
jobs.push([UI + '/assets/icon.png', 1024, 1024, full('night', 1024)]);
jobs.push([`${X}/AppIcon.appiconset/AppIcon-512@2x.png`, 1024, 1024, full('day', 1024)]);
jobs.push([`${X}/AppIcon.appiconset/AppIcon-Dark.png`, 1024, 1024, full('night', 1024)]);
jobs.push([`${X}/AppIcon.appiconset/AppIcon-Tinted.png`, 1024, 1024, luminousPage(1024, { ...MONO, fill: '#000' })]);
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
    jobs.push([`${R}/mipmap-${d}/${n}.png`, s, s, luminousPage(s, { theme, clip: 'rounded' })]);
    jobs.push([`${R}/mipmap-${d}/${n}_round.png`, s, s, luminousPage(s, { theme, clip: 'round' })]);
    // Background layer: the full 108dp canvas of ground.
    jobs.push([`${R}/mipmap-${d}/${n}_background.png`, a, a, luminousPage(a, { theme, arms: false, fill: BG[theme] })]);
    // Foreground: the galaxy kept inside the 72dp visible circle (spec: 66dp safe zone).
    jobs.push([`${R}/mipmap-${d}/${n}_foreground.png`, a, a, luminousPage(a, { theme, background: false, inner: Math.round(a * 70 / 108) })]);
  }
  // Themed-icon silhouette (Android 13+), shared by both launchers.
  jobs.push([`${R}/mipmap-${d}/ic_launcher_monochrome.png`, a, a, luminousPage(a, { ...MONO, inner: Math.round(a * 70 / 108) })]);
}
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const pg = await b.newPage();
  for (const [f, w, h, html] of jobs) {
    await pg.setViewportSize({ width: w, height: h }); await pg.setContent(html);
    await pg.waitForSelector('body[data-ready]', { state: 'attached' });
    await pg.screenshot({ path: f, omitBackground: true, clip: { x: 0, y: 0, width: w, height: h } });
  }
  await b.close(); console.log(jobs.length, 'rendered');
})();
