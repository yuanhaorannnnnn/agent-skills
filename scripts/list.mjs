#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import yaml from 'js-yaml';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '..');
const MANIFEST_PATH = path.join(ROOT_DIR, 'manifest.yaml');

function loadManifest() {
  if (!fs.existsSync(MANIFEST_PATH)) return null;
  const content = fs.readFileSync(MANIFEST_PATH, 'utf8');
  return yaml.load(content);
}

function getEnabledSkills(manifest) {
  if (!manifest || !manifest.skills) return [];
  return manifest.skills.filter(s => s.enabled !== false);
}

const manifest = loadManifest();
const skills = getEnabledSkills(manifest);

if (!skills.length) {
  console.log('No enabled skills found.');
  process.exit(0);
}

const byCategory = {};
for (const s of skills) {
  const cat = s.category || 'uncategorized';
  if (!byCategory[cat]) byCategory[cat] = [];
  byCategory[cat].push(s.name);
}

console.log('Published skills:');
for (const [cat, names] of Object.entries(byCategory).sort()) {
  console.log(`\n[${cat}]`);
  for (const name of names) {
    console.log(`  - ${name}`);
  }
}
