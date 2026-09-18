## What changed

<!-- One paragraph. Name the skill(s) or repo-level path touched. -->

## Why

## Verification

- [ ] `node scripts/install.mjs doctor`
- [ ] `python3 -m unittest discover -s tests -p 'test_*.py'`
- [ ] `git diff --check`
- [ ] Affected skill keeps its trigger boundary narrow (no over-broad `description`)

## Manifest and docs sync

- [ ] `manifest.yaml` updated for added/removed/disabled skills
- [ ] README skill table updated if the enabled set changed
