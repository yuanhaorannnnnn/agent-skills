#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';
import yaml from 'js-yaml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const SKILLS_DIR = path.join(ROOT_DIR, 'skills');
const SCRIPTS_DIR = path.join(ROOT_DIR, 'scripts');
const MANIFEST_PATH = path.join(ROOT_DIR, 'manifest.yaml');
const HOME_DIR = process.env.HOME;
const RUNTIME_DIRS = [
  path.join(HOME_DIR, '.agents', 'skills'),
  path.join(HOME_DIR, '.claude', 'skills'),
];

function loadManifest() {
  if (!fs.existsSync(MANIFEST_PATH)) return null;
  const content = fs.readFileSync(MANIFEST_PATH, 'utf8');
  return yaml.load(content);
}

function getEnabledSkills(manifest) {
  if (!manifest || !manifest.skills) return [];
  return manifest.skills.filter(s => s.enabled !== false);
}

function ensureRuntimeDir(runtimeDir) {
  if (!fs.existsSync(runtimeDir)) {
    fs.mkdirSync(runtimeDir, { recursive: true });
  }
}

function isSkillEnabled(enabledMap, name) {
  return !(enabledMap.has(name) && enabledMap.get(name) === false);
}

function buildEnabledMap(manifest) {
  const enabledMap = new Map();
  if (manifest && manifest.skills) {
    for (const s of manifest.skills) {
      enabledMap.set(s.name, s.enabled !== false);
    }
  }
  return enabledMap;
}

function maintainScriptsLink(runtimeDir) {
  const scriptsLink = path.join(runtimeDir, '.scripts');
  if (fs.existsSync(scriptsLink) || fs.lstatSync(path.dirname(scriptsLink)).isDirectory()) {
    try {
      fs.unlinkSync(scriptsLink);
    } catch {}
  }
  fs.symlinkSync(SCRIPTS_DIR, scriptsLink, 'dir');
}

function cleanupRepoLinks(runtimeDir, enabledMap) {
  const entries = fs.existsSync(runtimeDir) ? fs.readdirSync(runtimeDir) : [];
  for (const entry of entries) {
    const linkPath = path.join(runtimeDir, entry);
    let stat;
    try {
      stat = fs.lstatSync(linkPath);
    } catch {
      continue;
    }
    if (!stat.isSymbolicLink()) continue;
    const target = fs.readlinkSync(linkPath);
    if (target.startsWith(SKILLS_DIR + path.sep)) {
      const skillDir = path.join(SKILLS_DIR, entry);
      if (!fs.existsSync(linkPath) || !fs.existsSync(skillDir) || !isSkillEnabled(enabledMap, entry)) {
        fs.unlinkSync(linkPath);
        console.log(`Removed stale link: ${entry}`);
      }
    }
  }
}

function installIntoRuntime(runtimeDir, enabledMap) {
  ensureRuntimeDir(runtimeDir);
  maintainScriptsLink(runtimeDir);
  cleanupRepoLinks(runtimeDir, enabledMap);

  const installed = [];
  const updated = [];
  const skipped = [];
  const missingSkillMd = [];

  const skillDirs = fs.existsSync(SKILLS_DIR)
    ? fs.readdirSync(SKILLS_DIR)
        .map(name => ({ name, dir: path.join(SKILLS_DIR, name) }))
        .filter(({ dir }) => fs.statSync(dir).isDirectory())
    : [];

  for (const { name, dir } of skillDirs) {
    if (!fs.existsSync(path.join(dir, 'SKILL.md'))) {
      missingSkillMd.push(name);
      continue;
    }
    if (!isSkillEnabled(enabledMap, name)) {
      skipped.push(`${name} (disabled in manifest)`);
      continue;
    }
    const targetLink = path.join(runtimeDir, name);
    const existed = (() => {
      try {
        return fs.lstatSync(targetLink).isSymbolicLink();
      } catch {
        return false;
      }
    })();
    if (existed) {
      fs.unlinkSync(targetLink);
    }
    fs.symlinkSync(dir, targetLink, 'dir');
    if (existed) {
      updated.push(name);
    } else {
      installed.push(name);
    }
  }

  return { installed, updated, skipped, missingSkillMd };
}

function cmdInstall() {
  const manifest = loadManifest();
  const enabledMap = buildEnabledMap(manifest);

  const perRuntime = RUNTIME_DIRS.map((runtimeDir) => ({
    runtimeDir,
    ...installIntoRuntime(runtimeDir, enabledMap),
  }));

  console.log('');
  console.log('=== agent-skills install report ===');
  for (const { runtimeDir, installed, updated, skipped, missingSkillMd } of perRuntime) {
    console.log(`Runtime:   ${runtimeDir}`);
    if (installed.length) console.log(`Installed: ${installed.join(' ')}`);
    if (updated.length) console.log(`Updated:   ${updated.join(' ')}`);
    if (skipped.length) console.log(`Skipped:   ${skipped.join(' ')}`);
    if (missingSkillMd.length) console.log(`Missing SKILL.md: ${missingSkillMd.join(' ')}`);
    console.log('');
  }
  console.log('===================================');
}

function cmdUpdate() {
  console.log('Pulling latest changes...');
  execSync('git pull --ff-only', { cwd: ROOT_DIR, stdio: 'inherit' });
  console.log('Running install...');
  cmdInstall();
}

function cmdList() {
  const manifest = loadManifest();
  const skills = getEnabledSkills(manifest);
  if (!skills.length) {
    console.log('No enabled skills found.');
    return;
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
}

function cmdDoctor() {
  const manifest = loadManifest();
  const manifestNames = new Set((manifest?.skills || []).map(s => s.name));
  const enabledNames = new Set(getEnabledSkills(manifest).map(s => s.name));

  let issues = 0;

  // Check manifest consistency
  const skillEntries = manifest?.skills || [];
  const skillByName = new Map(skillEntries.map((skill) => [skill.name, skill]));
  const allowedInvocation = new Set(['user', 'model']);
  const allowedRole = new Set(['orchestrator', 'discipline', 'renderer', 'adapter']);

  for (const skill of skillEntries) {
    if (!allowedInvocation.has(skill.invocation)) {
      console.log(`[INVALID INVOCATION] ${skill.name}: ${skill.invocation}`);
      issues++;
    }
    if (!allowedRole.has(skill.role)) {
      console.log(`[INVALID ROLE] ${skill.name}: ${skill.role}`);
      issues++;
    }
    if (!Array.isArray(skill.calls)) {
      console.log(`[INVALID CALLS] ${skill.name}: calls must be an array`);
      issues++;
      continue;
    }
    for (const callee of skill.calls) {
      const target = skillByName.get(callee);
      if (!target) {
        console.log(`[UNKNOWN CALLEE] ${skill.name} -> ${callee}`);
        issues++;
      } else if (skill.invocation === 'user' && target.invocation !== 'model') {
        console.log(`[ORCHESTRATOR NESTING] ${skill.name} -> ${callee} is not model-invoked`);
        issues++;
      }
    }
  }

  for (const name of manifestNames) {
    const skillDir = path.join(SKILLS_DIR, name);
    if (!fs.existsSync(skillDir)) {
      console.log(`[MISSING DIR] manifest lists ${name}, but skills/${name}/ does not exist`);
      issues++;
    } else if (!fs.existsSync(path.join(skillDir, 'SKILL.md'))) {
      console.log(`[MISSING SKILL.md] skills/${name}/SKILL.md not found`);
      issues++;
    }
  }

  for (const runtimeDir of RUNTIME_DIRS) {
    ensureRuntimeDir(runtimeDir);

    const runtimeEntries = fs.existsSync(runtimeDir) ? fs.readdirSync(runtimeDir) : [];
    for (const entry of runtimeEntries) {
      const linkPath = path.join(runtimeDir, entry);
      let stat;
      try {
        stat = fs.lstatSync(linkPath);
      } catch {
        continue;
      }
      if (!stat.isSymbolicLink()) continue;
      const target = fs.readlinkSync(linkPath);
      if (!target.startsWith(SKILLS_DIR + path.sep)) continue;

      if (!fs.existsSync(linkPath)) {
        console.log(`[BAD LINK] ${runtimeDir}/${entry} -> ${target}`);
        issues++;
        continue;
      }
      if (!enabledNames.has(entry)) {
        console.log(`[DISABLED LINK] runtime link ${runtimeDir}/${entry} exists but the skill is disabled in manifest.yaml`);
        issues++;
      }
      if (!fs.existsSync(path.join(linkPath, 'SKILL.md'))) {
        console.log(`[MISSING SKILL.md] ${runtimeDir}/${entry}`);
        issues++;
      }
      if (!manifestNames.has(entry)) {
        console.log(`[NOT IN MANIFEST] runtime link ${runtimeDir}/${entry} is not listed in manifest.yaml`);
        issues++;
      }
    }

    const scriptsLinkPath = path.join(runtimeDir, '.scripts');
    if (!fs.existsSync(scriptsLinkPath)) {
      console.log(`[MISSING LINK] ${runtimeDir}/.scripts is not linked to the repo scripts directory`);
      issues++;
    }
  }

  // Check shared scripts presence (heuristic: list known shared scripts)
  const knownSharedScripts = [
    'common.py', 'note_rule.py', 'planning_paths.py', 'planning_status.py',
    'restore_conversation.py', 'review_diff.py',
    'save_conversation.py'
  ];
  for (const script of knownSharedScripts) {
    const scriptPath = path.join(SCRIPTS_DIR, script);
    if (!fs.existsSync(scriptPath)) {
      console.log(`[MISSING SCRIPT] scripts/${script}`);
      issues++;
    }
  }

  if (issues === 0) {
    console.log('Doctor: all checks passed.');
  } else {
    console.log(`Doctor: found ${issues} issue(s).`);
    process.exit(1);
  }
}

function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'install';

  switch (command) {
    case 'install':
      cmdInstall();
      break;
    case 'update':
      cmdUpdate();
      break;
    case 'list':
      cmdList();
      break;
    case 'doctor':
      cmdDoctor();
      break;
    default:
      console.error(`Unknown command: ${command}`);
      console.error('Usage: agent-skills [install|update|list|doctor]');
      process.exit(1);
  }
}

main();
