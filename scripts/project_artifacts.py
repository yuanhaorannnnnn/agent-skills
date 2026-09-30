"""Resolve task artifacts for the documented, repository-owned CARLA layout."""
from pathlib import Path


def task_dir(repo, task_id, workflow='tasking', runtime=False):
    root = Path(repo)
    if not task_id or task_id in {'.', '..'} or '/' in task_id or '\\' in task_id:
        raise ValueError('task ID must be one path component')
    owned_docs = (root / '.agent-artifacts-repo-owned').is_file() and (root / 'Docs/guides/documentation.md').is_file()
    if owned_docs:
        slug = 'repair-' + task_id if workflow == 'repair' else task_id
        return root / ('.local' if runtime else 'Docs') / 'tasks' / slug
    if runtime:
        return root / '.planning' / task_id
    return root / '.proposal' / ('repair' if workflow == 'repair' else '') / task_id
