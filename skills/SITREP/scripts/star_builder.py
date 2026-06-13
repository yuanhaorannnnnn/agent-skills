"""Build STAR structures from tasks using LLM."""

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from .task_clustering import Task, load_save_conversation_summary
    from .common_wr import load_json
except ImportError:
    from task_clustering import Task, load_save_conversation_summary
    from common_wr import load_json


# Cache directory for LLM responses
_CACHE_DIR = Path.home() / ".agents" / "work-reports" / ".cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Model to use for STAR extraction
_MODEL = os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro[1m]")

_STAR_PROMPT = """You are analyzing a coding agent conversation to extract a work record following the STAR principle.

The final report is read by a person who wants a clear weekly/monthly work summary,
not a transcript audit. Write natural, concrete Chinese that sounds like a human
summarizing real engineering work. Avoid debug-log wording, raw prompt wording,
and vague phrases such as "进行了一些处理" or "完成相关工作".

STAR stands for:
- Situation: The context and background of why this task existed
- Task: The specific objective or goal
- Action: The key steps taken (file edits, technical decisions, tool usage, debugging)
- Result: The outcome and what was achieved

Here is the conversation (USER = user's request, ASSISTANT = agent's response, FILE = file changed, TOOL = tool invoked):

{conversation}

Additional context:
- Project: {project}
- Agent: {agent}
- Files modified: {files}
- Time range: {time_range}
{save_conversation_context}

Extract the work record in JSON format:
{{
  "situation": "...",
  "task": "...",
  "actions": ["...", "...", "..."],
  "result": "...",
  "status": "completed|in_progress|blocked"
}}

Guidelines:
1. Situation: 1-2 concise Chinese sentences explaining why this work mattered. Do not mention "USER", "ASSISTANT", prompts, or raw session mechanics.
2. Task: The core objective in one plain Chinese sentence. Phrase it as a work goal, not as a chat request.
3. Actions: 3-5 concrete Chinese action items. Prefer engineering verbs such as "梳理", "实现", "修正", "验证", "接入", "清理". Mention important files only when they help the reader understand the work.
4. Result: One clear Chinese sentence stating the outcome, current state, or remaining gap. If unfinished, say what remains instead of pretending it is complete.
5. Status: "completed" if the task was finished, "in_progress" if ongoing, "blocked" if stuck
6. Be factual and specific, but readable. Remove filler, assistant self-reference, and tool chatter.
7. If the conversation is too short or just a meta command, set all fields to empty strings and status to "skipped".

Output ONLY the JSON object, no markdown formatting, no explanation."""


def _load_canon_task_for_sessions(sessions) -> Optional[dict]:
    """Load STAR-relevant fields from the best-matching Canon task page.

    Collects all candidates, scores them, picks the highest above threshold.
    Does NOT return the first match with score > 0.
    """
    canon_tasks = Path("/media/yhr/2T/Canon/tasks")
    if not canon_tasks.exists():
        return None

    projects = {s.project for s in sessions if s.project}
    branches = {s.git_branch for s in sessions if s.git_branch}

    candidates: list[tuple[int, str]] = []  # (score, content)
    for tf in canon_tasks.glob("*.md"):
        content = tf.read_text(encoding="utf-8", errors="replace")
        score = 0
        # Exact branch/ID match in filename
        for branch in branches:
            if branch:
                # Try demand/bug ID extraction first (feature/JHBN-123 → JHBN-123)
                id_match = re.match(r"(?:feature|bugfix|fix)/([\w-]+)", branch)
                if id_match:
                    if id_match.group(1) == tf.stem:
                        score += 10
                    elif id_match.group(1) in content:
                        score += 5
                # Then sanitized branch name fallback
                safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", branch).strip("-")
                if safe in tf.stem:
                    score += 8
        # Project match in content
        for proj in projects:
            if proj and proj in content:
                score += 2
        # Branch match in content
        for branch in branches:
            if branch and branch in content:
                score += 3
        if score > 0:
            candidates.append((score, content))

    if not candidates:
        return None

    # Sort by score descending, pick best above threshold
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_content = candidates[0]
    if best_score >= 4:  # project alone (2) insufficient
        return _parse_canon_task_for_star(best_content)
    return None


def _parse_canon_task_for_star(content: str) -> dict:
    """Extract STAR-relevant fields from a Canon task page."""
    result = {
        "summary": "",
        "objective": "",
        "key_decisions": "",
        "pending_followups": "",
        "known_issues": "",
    }
    sections = {
        "## Current State": "summary",
        "## Goal": "objective",
        "## Key Decisions": "key_decisions",
        "## Next Step": "pending_followups",
    }
    current_key = None
    buffer: list[str] = []

    for line in content.split("\n"):
        stripped = line.strip()
        matched = False
        for header, key in sections.items():
            if stripped.startswith(header):
                if current_key and buffer:
                    result[current_key] = "\n".join(buffer).strip()
                    buffer = []
                current_key = key
                matched = True
                break
        if matched:
            continue
        if current_key:
            buffer.append(line)

    if current_key and buffer:
        result[current_key] = "\n".join(buffer).strip()

    return result


def build_star_for_task(task: Task, use_cache: bool = True) -> Task:
    """Enrich a Task with STAR fields using LLM.

    If use_cache is True, cached results are used when available.
    """
    # Priority 1: Canon task page (durable task state)
    canon_task = _load_canon_task_for_sessions(task.sessions)
    if canon_task and canon_task.get("summary"):
        _apply_save_conversation(task, canon_task)
        if not task.actions or not task.result:
            _llm_enrich(task, use_cache=use_cache)
        return task

    # Priority 2: Historical runtime recap
    save_conv = None
    for session in task.sessions:
        save_conv = load_save_conversation_summary(session.session_id)
        if save_conv:
            break

    if save_conv and save_conv.get("summary"):
        _apply_save_conversation(task, save_conv)
        if not task.actions or not task.result:
            _llm_enrich(task, use_cache=use_cache)
        return task

    # Priority 3: LLM extraction from raw conversation
    _llm_enrich(task, use_cache=use_cache)
    return task


def _apply_save_conversation(task: Task, save_conv: dict) -> None:
    """Apply historical runtime recap to task fields."""
    task.situation = save_conv.get("summary", "")[:500]
    task.task_description = save_conv.get("objective", "")[:300]
    # LLM-extracted objective is a better title than the first user prompt
    if task.task_description:
        task.title = task.task_description[:120]

    # Key decisions become actions
    decisions = save_conv.get("key_decisions", "")
    if decisions:
        task.actions = [d.strip() for d in decisions.split("\n") if d.strip()][:5]

    # Pending followups indicate in-progress status
    pending = save_conv.get("pending_followups", "")
    if pending:
        task.status = "in_progress"

    # Known issues indicate blocked status
    issues = save_conv.get("known_issues", "")
    if issues:
        task.status = "blocked"


def _llm_enrich(task: Task, use_cache: bool = True) -> None:
    """Use LLM to extract STAR fields from conversation."""
    conversation = task.conversation_text(max_length=6000)

    # Skip very short conversations
    if len(conversation) < 100:
        task.status = "skipped"
        return

    # Check cache
    cache_key = _compute_cache_key(task.task_id, conversation)
    cache_path = _CACHE_DIR / f"{cache_key}.json"

    if use_cache and cache_path.exists():
        cached = load_json(cache_path)
        if cached:
            _apply_star_json(task, cached)
            return

    # Call LLM
    result = _call_llm(conversation, task)
    if result:
        _apply_star_json(task, result)
        # Save to cache
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)


def _call_llm(conversation: str, task: Task) -> Optional[dict]:
    """Call Claude API to extract STAR structure."""
    if anthropic is None:
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        return None

    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
    )

    files_str = ", ".join(task.files_modified[:10]) if task.files_modified else "None"
    time_range = ""
    if task.start_time and task.end_time:
        time_range = f"{task.start_time.strftime('%Y-%m-%d %H:%M')} to {task.end_time.strftime('%Y-%m-%d %H:%M')}"

    save_ctx = ""
    if task.situation:
        save_ctx = f"\n- Historical runtime recap: {task.situation[:200]}"

    prompt = _STAR_PROMPT.format(
        conversation=conversation,
        project=task.project or "Unknown",
        agent=task.agent or "Unknown",
        files=files_str,
        time_range=time_range,
        save_conversation_context=save_ctx,
    )

    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1500,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )

        content = ""
        for block in response.content:
            if hasattr(block, "text") and block.text:
                content = block.text
                break
        return _parse_json_response(content)

    except Exception as e:
        print(f"LLM call failed for task {task.task_id}: {e}")
        return None


def _parse_json_response(content: str) -> Optional[dict]:
    """Parse JSON from LLM response, handling markdown wrappers."""
    content = content.strip()

    # Remove markdown code blocks
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass
        return None


def _apply_star_json(task: Task, data: dict) -> None:
    """Apply parsed STAR JSON to task fields."""
    if not data:
        return

    task.situation = data.get("situation", "")[:500]
    task.task_description = data.get("task", "")[:300]
    # LLM-extracted task description is a better title than the first user prompt
    if task.task_description:
        task.title = task.task_description[:120]

    actions = data.get("actions", [])
    if isinstance(actions, list):
        task.actions = [str(a).strip() for a in actions if str(a).strip()][:8]
    elif isinstance(actions, str):
        task.actions = [actions.strip()]

    task.result = data.get("result", "")[:500]

    status = data.get("status", "").lower()
    if status in ("completed", "in_progress", "blocked", "skipped"):
        task.status = status
    elif status:
        # Map partial matches
        if "complete" in status or "done" in status:
            task.status = "completed"
        elif "progress" in status or "ongoing" in status:
            task.status = "in_progress"
        elif "block" in status or "fail" in status:
            task.status = "blocked"


def _compute_cache_key(task_id: str, conversation: str) -> str:
    """Compute a cache key for a task + conversation."""
    content = f"{task_id}:{conversation[:2000]}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def build_stars_for_tasks(tasks: list[Task], use_cache: bool = True, quiet: bool = False) -> list[Task]:
    """Build STAR structures for all tasks."""
    for i, task in enumerate(tasks):
        if not quiet:
            print(f"  [{i+1}/{len(tasks)}] Building STAR for: {task.title[:50]}...")
        build_star_for_task(task, use_cache=use_cache)
    return tasks
