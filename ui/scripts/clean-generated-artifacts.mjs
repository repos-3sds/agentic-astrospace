#!/usr/bin/env node
/**
 * Keep generated web/native build folders deterministic.
 *
 * macOS occasionally leaves Finder-style duplicate files in generated folders
 * (`chunk-ABC 2.js`, `config 3.xml`, `build 2.gradle`). Angular and Capacitor
 * can ignore them, but Android's resource and asset packagers cannot. This
 * script quarantines only generated artifacts and leaves source files alone.
 */
import { existsSync, mkdirSync, readdirSync, renameSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = join(root, '..');
const stamp = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14);
const backupRoot = join('/tmp', `siddha-generated-artifacts-${stamp}`);
const args = new Set(process.argv.slice(2));

const duplicatePattern = / \d+(\.[^/.]+)$/;
let moved = 0;

function backupPath(path) {
  const rel = relative(repoRoot, path).replaceAll('/', '__').replaceAll(' ', '_');
  return join(backupRoot, `${String(++moved).padStart(3, '0')}__${rel}`);
}

function ensureBackup() {
  mkdirSync(backupRoot, { recursive: true });
}

function move(path) {
  if (!existsSync(path)) return;
  ensureBackup();
  const next = backupPath(path);
  mkdirSync(dirname(next), { recursive: true });
  renameSync(path, next);
}

function walk(path, visit) {
  if (!existsSync(path)) return;
  const stat = statSync(path);
  if (!stat.isDirectory()) {
    visit(path);
    return;
  }
  for (const entry of readdirSync(path, { withFileTypes: true })) {
    const child = join(path, entry.name);
    if (entry.isDirectory()) walk(child, visit);
    else visit(child);
  }
}

function quarantineDuplicates(paths) {
  for (const path of paths) {
    walk(path, (file) => {
      if (duplicatePattern.test(file)) move(file);
    });
  }
}

if (args.has('--before-web-build')) {
  move(join(repoRoot, 'frontend', 'dist', 'browser'));
}

if (args.has('--after-web-build')) {
  quarantineDuplicates([join(repoRoot, 'frontend', 'dist', 'browser')]);
}

if (args.has('--before-cap-sync')) {
  move(join(root, 'android', 'app', 'src', 'main', 'assets', 'public'));
  quarantineDuplicates([
    join(root, 'android', 'app', 'src', 'main', 'res'),
    join(root, 'android'),
    join(root, 'ios', 'App', 'App'),
    join(root, 'ios'),
  ]);
}

if (args.has('--after-cap-sync')) {
  quarantineDuplicates([
    join(root, 'android', 'app', 'src', 'main', 'assets', 'public'),
    join(root, 'android', 'app', 'src', 'main', 'res'),
    join(root, 'android'),
    join(root, 'ios', 'App', 'App'),
    join(root, 'ios'),
  ]);
}

if (args.size === 0) {
  quarantineDuplicates([
    join(repoRoot, 'frontend', 'dist', 'browser'),
    join(root, 'android', 'app', 'src', 'main', 'assets', 'public'),
    join(root, 'android', 'app', 'src', 'main', 'res'),
    join(root, 'android'),
    join(root, 'ios', 'App', 'App'),
    join(root, 'ios'),
  ]);
}

if (moved) {
  console.log(`quarantined ${moved} generated duplicate${moved === 1 ? '' : 's'} in ${backupRoot}`);
} else {
  console.log('generated artifacts already clean');
}
