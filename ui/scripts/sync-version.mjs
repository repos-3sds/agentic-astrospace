#!/usr/bin/env node
/**
 * One version, written into the two native projects that must agree.
 *
 * Before this, four numbers disagreed: package.json said 0.0.0, iOS said 1.0/1,
 * Android said 1.0/1, and FastAPI said 2.0.0. Three of those describe the same
 * app and had drifted; a mismatched CURRENT_PROJECT_VERSION is also how a
 * TestFlight upload gets rejected at the last step.
 *
 * FastAPI's version is deliberately NOT touched. That is the *API* version and
 * is a different thing from what the app calls itself — `/api/v1` routes served
 * by a 2.0.0 application is coherent, and collapsing them would lose real
 * information.
 *
 *   marketing version  <- package.json "version"      (what users see: 1.0.0)
 *   build number       <- git commit count             (monotonic, automatic)
 *
 * The build number is derived rather than stored because Play rejects a
 * versionCode that does not increase, and a number a human has to remember to
 * bump is a number that eventually does not get bumped. Commit count only ever
 * grows on a branch that only ever gains commits.
 *
 * Run: node scripts/sync-version.mjs [--check]
 *   --check exits non-zero if anything is out of sync, without writing. That is
 *   the form CI should use.
 */
import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const checkOnly = process.argv.includes('--check');

const pkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
const marketing = pkg.version;

if (!/^\d+\.\d+\.\d+$/.test(marketing)) {
  console.error(`package.json version must be x.y.z, got "${marketing}"`);
  process.exit(1);
}

const build = execSync('git rev-list --count HEAD', { cwd: root }).toString().trim();

const edits = [];

/** Replace every occurrence, recording whether anything actually changed. */
function apply(path, replacements) {
  const file = join(root, path);
  const before = readFileSync(file, 'utf8');
  let after = before;
  for (const [pattern, next] of replacements) after = after.replace(pattern, next);
  if (after !== before) edits.push({ path, file, after });
}

apply('ios/App/App.xcodeproj/project.pbxproj', [
  [/MARKETING_VERSION = [^;]+;/g, `MARKETING_VERSION = ${marketing};`],
  [/CURRENT_PROJECT_VERSION = [^;]+;/g, `CURRENT_PROJECT_VERSION = ${build};`],
]);

apply('android/app/build.gradle', [
  [/versionCode \d+/g, `versionCode ${build}`],
  [/versionName "[^"]*"/g, `versionName "${marketing}"`],
]);

if (edits.length === 0) {
  console.log(`versions already in sync — ${marketing} (build ${build})`);
  process.exit(0);
}

if (checkOnly) {
  console.error(`version drift in: ${edits.map((e) => e.path).join(', ')}`);
  console.error(`expected ${marketing} (build ${build}) — run: npm run version:sync`);
  process.exit(1);
}

for (const { path, file, after } of edits) {
  writeFileSync(file, after);
  console.log(`  updated ${path}`);
}
console.log(`synced to ${marketing} (build ${build})`);
