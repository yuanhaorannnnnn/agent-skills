"""Cluster conversation events into tasks."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from .normalizer import Event, Session
    from .common_wr import load_json, parse_iso_timestamp
except ImportError:
    from normalizer import Event, Session
    from common_wr import load_json, parse_iso_timestamp

# Time gap threshold for splitting tasks (2 hours)
# Users may take long breaks and return to the same task.
TASK_GAP_MINUTES = 120


@dataclass
class Task:
    """A work task composed of one or more sessions."""

    task_id: str
    sessions: list[Session] = field(default_factory=list)
    title: str = ""
    project: str = ""
    agent: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "unknown"  # completed, in_progress, blocked, abandoned

    # STAR fields (populated by star_builder)
    situation: str = ""
    task_description: str = ""
    actions: list[str] = field(default_factory=list)
    result: str = ""

    # Metadata
    files_modified: list[str] = field(default_factory=list)
    total_events: int = 0
    total_prompts: int = 0
    total_responses: int = 0

    def all_events(self) -> list[Event]:
        """Get all events across all sessions, sorted by time."""
        events = []
        for s in self.sessions:
            events.extend(s.events)
        events.sort(key=lambda e: e.timestamp)
        return events

    def conversation_text(self, max_length: int = 8000) -> str:
        """Generate a condensed text representation of the conversation."""
        lines = []
        for e in self.all_events():
            if e.event_type == "user_prompt":
                lines.append(f"USER: {e.content[:500]}")
            elif e.event_type == "assistant_response":
                lines.append(f"ASSISTANT: {e.content[:500]}")
            elif e.event_type == "file_change":
                lines.append(f"FILE: {e.file_path}")
            elif e.event_type == "tool_call":
                lines.append(f"TOOL: {e.tool_name}")
        text = "\n".join(lines)
        if len(text) > max_length:
            text = text[:max_length] + "\n... [truncated]"
        return text


def cluster_sessions(sessions: list[Session]) -> list[Task]:
    """Group sessions into tasks based on boundaries and relationships."""
    if not sessions:
        return []

    # Step 1: Split each session into task segments based on boundaries
    all_segments: list[tuple[Session, list[Event]]] = []
    for session in sessions:
        segments = _split_session_into_segments(session)
        for seg_events in segments:
            all_segments.append((session, seg_events))

    # Step 2: Group segments by Canon task pages (priority)
    canon_groups = _group_by_canon_tasks(all_segments)

    # Step 3: Group segments by historical runtime recap links
    linked_groups = _group_by_save_conversation(canon_groups)

    # Step 4: Further group by time proximity and project
    tasks = _merge_into_tasks(linked_groups)

    return tasks


def _split_session_into_segments(session: Session) -> list[list[Event]]:
    """Split a single session's events into task segments.

    A new segment starts when:
    - Time gap > 30 minutes
    - /clear command
    """
    if not session.events:
        return []

    segments: list[list[Event]] = []
    current: list[Event] = []

    sorted_events = sorted(session.events, key=lambda e: e.timestamp)

    for i, event in enumerate(sorted_events):
        # Start new segment on /clear
        if event.event_type == "user_prompt" and event.content.strip() == "/clear":
            if current:
                segments.append(current)
            current = []
            continue

        # Start new segment on large time gap (only if there's actual conversation)
        if current:
            gap = event.timestamp - current[-1].timestamp
            if gap > timedelta(minutes=TASK_GAP_MINUTES):
                segments.append(current)
                current = []

        # Start new segment on working directory or branch change
        # (signals a switch to a different project/task)
        if current and i > 0:
            prev = sorted_events[i - 1]
            if event.cwd and prev.cwd and event.cwd != prev.cwd:
                segments.append(current)
                current = []
            elif event.git_branch and prev.git_branch and event.git_branch != prev.git_branch:
                segments.append(current)
                current = []

        current.append(event)

    if current:
        segments.append(current)

    return segments


def _group_by_canon_tasks(
    segments: list[tuple[Session, list[Event]]],
) -> list[list[tuple[Session, list[Event]]]]:
    """Group segments linked via Canon task pages.

    Uses weighted scoring — not one-to-one mapping — to avoid merging
    unrelated tasks that happen to share the same project or source.

    Scoring weights:
      - demand/bug ID exact match: 10
      - branch name match in task content: 8
      - task title keywords in branch/event content: 5
      - project match: 2 (weak signal, insufficient alone)
      - source match: 1 (very weak, 'user' matches everything)
    """
    canon_tasks = Path("/media/yhr/2T/Canon/tasks")
    if not canon_tasks.exists():
        return [[seg] for seg in segments]

    # Build scored candidates for each segment
    MIN_SCORE = 4  # project alone (2) is insufficient

    segment_best: dict[int, tuple[str, int]] = {}  # seg_idx → (task_name, score)

    for i, (session, seg_events) in enumerate(segments):
        best_name = None
        best_score = 0

        for tf in canon_tasks.glob("*.md"):
            content = tf.read_text(encoding="utf-8", errors="replace")
            task_name = tf.stem
            score = 0

            # Exact ID match (demand/bug ID)
            demand_match = re.match(r"(?:feature|bugfix|fix)/([\w-]+)", session.git_branch or "")
            if demand_match:
                if demand_match.group(1) == task_name:
                    score += 10
                elif demand_match.group(1) in content:
                    score += 5

            # Branch name appears in task content
            if session.git_branch and session.git_branch in content:
                score += 8

            # Task title keywords in events
            events_text = " ".join(
                e.content[:200] for e in seg_events if e.content
            )[:1000]
            # Extract keywords from task name (kebab → words)
            task_keywords = set(task_name.replace("-", " ").split())
            for kw in task_keywords:
                if len(kw) > 2 and kw.lower() in events_text.lower():
                    score += 5
                    break  # one keyword match is enough

            # Project match (weak — same project ≠ same task)
            frontmatter_project = ""
            for line in content.split("\n"):
                if line.startswith("project:"):
                    frontmatter_project = line.split(":", 1)[1].strip()
                    break
            if session.project and frontmatter_project == session.project:
                score += 2

            # Source match (very weak — 'user' matches everything)
            frontmatter_source = ""
            for line in content.split("\n"):
                if line.startswith("source:"):
                    frontmatter_source = line.split(":", 1)[1].strip()
                    break
            if frontmatter_source and frontmatter_source != "user" and frontmatter_source in (session.project or ""):
                score += 1

            if score > best_score:
                best_score = score
                best_name = task_name

        if best_score >= MIN_SCORE and best_name:
            segment_best[i] = (best_name, best_score)

    # Group by matched task name
    groups: dict[str, list[tuple[Session, list[Event]]]] = {}
    ungrouped: list[tuple[Session, list[Event]]] = []
    for i, seg in enumerate(segments):
        match = segment_best.get(i)
        if match:
            task_name = match[0]
            if task_name not in groups:
                groups[task_name] = []
            groups[task_name].append(seg)
        else:
            ungrouped.append(seg)

    result = list(groups.values())
    result.extend([[seg] for seg in ungrouped])
    return result


def _group_by_save_conversation(
    groups: list[list[tuple[Session, list[Event]]]],
) -> list[list[tuple[Session, list[Event]]]]:
    """Group segments that are linked via historical runtime recap.

    Check .agent-state/conversations/<name>.md for conversation links.
    Accepts pre-grouped segments from _group_by_canon_tasks and further
    merges groups linked by the same conversation name.
    """
    # Flatten pre-groups into individual segments for conversation matching
    agent_state_dir = Path(".agent-state")
    if not agent_state_dir.exists():
        return groups

    conv_dir = agent_state_dir / "conversations"
    conversation_names: dict[str, str] = {}  # session_id -> conversation_name

    if conv_dir.exists():
        for md_file in conv_dir.glob("*.md"):
            name = md_file.stem
            content = md_file.read_text(encoding="utf-8", errors="replace")
            for group in groups:
                for session, _ in group:
                    if session.session_id in content:
                        conversation_names[session.session_id] = name

    # Group pre-groups by conversation name
    conv_groups: dict[str, list[tuple[Session, list[Event]]]] = {}
    ungrouped: list[list[tuple[Session, list[Event]]]] = []

    for group in groups:
        # Find the conversation name for this group via any session
        conv_name = None
        for session, _ in group:
            conv_name = conversation_names.get(session.session_id)
            if conv_name:
                break

        if conv_name:
            if conv_name not in conv_groups:
                conv_groups[conv_name] = []
            conv_groups[conv_name].extend(group)
        else:
            ungrouped.append(group)

    result = list(conv_groups.values())
    result.extend(ungrouped)
    return result


def _merge_into_tasks(
    groups: list[list[tuple[Session, list[Event]]]],
) -> list[Task]:
    """Merge segment groups into final Task objects."""
    tasks: list[Task] = []

    for group in groups:
        # Collect all sessions and events
        all_sessions: list[Session] = []
        all_events: list[Event] = []

        for session, seg_events in group:
            if session not in all_sessions:
                all_sessions.append(session)
            all_events.extend(seg_events)

        if not all_events:
            continue

        all_events.sort(key=lambda e: e.timestamp)

        # Determine primary session (the one with the most events)
        primary_session = max(all_sessions, key=lambda s: len(s.events))

        # Build task
        task_id = primary_session.session_id

        # Extract title
        title = _extract_task_title(all_sessions, all_events)

        # Determine project
        projects = {s.project for s in all_sessions if s.project}
        project = next(iter(projects)) if projects else ""

        # Determine agent
        agents = {s.agent for s in all_sessions if s.agent}
        agent = ",".join(sorted(agents)) if agents else ""

        # Collect files modified
        files = list(dict.fromkeys(
            e.file_path for e in all_events if e.event_type == "file_change" and e.file_path
        ))

        # Count stats
        prompts = len([e for e in all_events if e.event_type == "user_prompt"])
        responses = len([e for e in all_events if e.event_type == "assistant_response"])

        task = Task(
            task_id=task_id,
            sessions=all_sessions,
            title=title,
            project=project,
            agent=agent,
            start_time=all_events[0].timestamp,
            end_time=all_events[-1].timestamp,
            files_modified=files,
            total_events=len(all_events),
            total_prompts=prompts,
            total_responses=responses,
        )

        # Detect status
        task.status = _detect_status(task, all_events)

        # Filter out noise tasks
        if _is_noise_task(task):
            continue

        tasks.append(task)

    # Merge similar tasks (same conversation split by /clear or session restore)
    tasks = _merge_similar_tasks(tasks)

    # Sort by start time
    tasks.sort(key=lambda t: t.start_time or datetime.min)
    return tasks


def _is_noise_task(task: Task) -> bool:
    """Check if a task is noise and should be filtered out.

    Criteria:
    - Less than 3 total events
    - 0 user prompts and 0 assistant responses
    - Title looks like a session ID (UUID fragment)
    """
    # Too few events
    if task.total_events < 3:
        return True

    # No actual conversation content
    if task.total_prompts == 0 and task.total_responses == 0:
        return True

    # Title looks like a UUID/session ID
    title = task.title
    if len(title) == 12 and all(c in "0123456789abcdef-" for c in title):
        return True

    # Title is just a meta command
    meta_commands = ["/clear", "/login", "/exit", "/logout", "/sessions"]
    if title.strip().lower() in meta_commands:
        return True

    return False


def _normalize_title(title: str) -> str:
    """Normalize a title for similarity comparison.

    Lowercase, remove spaces/punctuation, keep only CJK/alphanumeric chars.
    """
    import re

    if not title:
        return ""
    # Lowercase
    normalized = title.lower()
    # Remove common punctuation and whitespace
    normalized = re.sub(r'[\s\n\r\t.,;:!?·，。；：！？、"\'\(\)\[\]\{\}<>\-_/\\|@#$%^&*+=~`]', '', normalized)
    return normalized


def _title_similarity(a: str, b: str) -> float:
    """Compute similarity between two titles (0-1)."""
    na = _normalize_title(a)
    nb = _normalize_title(b)
    if not na or not nb:
        return 0.0

    # Exact match after normalization
    if na == nb:
        return 1.0

    # One contains the other
    if na in nb or nb in na:
        # Require minimum length to avoid false positives
        if len(na) >= 10 and len(nb) >= 10:
            return 0.9

    # Check shared prefix (for titles that start the same way)
    min_len = min(len(na), len(nb))
    if min_len >= 10:
        prefix_len = 0
        for i in range(min_len):
            if na[i] == nb[i]:
                prefix_len += 1
            else:
                break
        if prefix_len >= min_len * 0.8:
            return 0.85

    return 0.0


def _extract_response_fingerprints(task: Task, max_responses: int = 5, fingerprint_len: int = 300) -> set[str]:
    """Extract fingerprints from assistant responses for content comparison.

    We use assistant responses (not user prompts) because user prompts may vary
    widely even within the same conversation (e.g. "continue", "ok", "test it"),
    but the agent's replies carry the actual work content.
    """
    fingerprints: set[str] = set()
    responses = [e for e in task.all_events() if e.event_type == "assistant_response"]

    for e in responses[:max_responses]:
        text = e.content.strip().lower()
        # Remove extra whitespace
        text = " ".join(text.split())
        # Take first N chars as fingerprint
        fp = text[:fingerprint_len]
        if len(fp) > 50:  # Ignore very short responses
            fingerprints.add(fp)

    return fingerprints


def _content_similarity(a: Task, b: Task) -> float:
    """Compute content similarity based on assistant response overlap.

    Returns 0-1 where 1 means all assistant responses are identical.
    """
    fp_a = _extract_response_fingerprints(a)
    fp_b = _extract_response_fingerprints(b)

    if not fp_a or not fp_b:
        return 0.0

    # Count how many fingerprints from A have a match in B
    # A match means one contains the other or they share a long prefix
    matched = 0
    for fa in fp_a:
        for fb in fp_b:
            # Exact match
            if fa == fb:
                matched += 1
                break
            # One contains the other (>= 80% overlap)
            if fa in fb or fb in fa:
                min_len = min(len(fa), len(fb))
                if min_len > 100:
                    matched += 1
                    break
            # Shared prefix >= 60%
            min_len = min(len(fa), len(fb))
            if min_len > 100:
                prefix_len = sum(1 for i in range(min_len) if fa[i] == fb[i])
                if prefix_len >= min_len * 0.6:
                    matched += 1
                    break

    # Jaccard-like score: matched / max(len(A), len(B))
    return matched / max(len(fp_a), len(fp_b))


def _should_merge_tasks(a: Task, b: Task) -> bool:
    """Determine if two tasks should be merged.

    Aggressive strategy: similar work is the same task. Small prompt differences
    should not prevent merging.

    Criteria (all must pass):
    1. Same project
    2. Within 24 hours
    3. Either title similarity >= 0.6 OR content similarity >= 0.4
    """
    # Same project
    if a.project != b.project:
        return False

    # Within 24 hours
    if a.start_time and b.start_time:
        time_diff = abs((a.start_time - b.start_time).total_seconds())
        if time_diff > 86400:
            return False

    # Title similarity (lowered threshold for aggressive merging)
    title_sim = _title_similarity(a.title, b.title)
    if title_sim >= 0.6:
        return True

    # Content similarity (assistant response overlap)
    # Lowered threshold to handle "short starter session + long implementation session" cases
    content_sim = _content_similarity(a, b)
    if content_sim >= 0.25:
        return True

    return False


def _merge_similar_tasks(tasks: list[Task]) -> list[Task]:
    """Merge tasks that are likely the same conversation split across sessions.

    Uses aggressive merging: tasks with similar assistant response content or
    similar titles are merged even if user prompts differ.
    """
    if not tasks:
        return tasks

    merged: list[Task] = []
    merged_indices: set[int] = set()

    for i, task_a in enumerate(tasks):
        if i in merged_indices:
            continue

        similar_tasks: list[Task] = [task_a]

        for j, task_b in enumerate(tasks[i + 1:], start=i + 1):
            if j in merged_indices:
                continue

            if _should_merge_tasks(task_a, task_b):
                similar_tasks.append(task_b)
                merged_indices.add(j)

        if len(similar_tasks) == 1:
            merged.append(task_a)
            continue

        # Merge all similar tasks into one
        all_sessions: list[Session] = []
        all_events: list[Event] = []

        for t in similar_tasks:
            for s in t.sessions:
                if s not in all_sessions:
                    all_sessions.append(s)
            all_events.extend(t.all_events())

        all_events.sort(key=lambda e: e.timestamp)

        # Merge files
        all_files = list(dict.fromkeys(
            f for t in similar_tasks for f in t.files_modified
        ))

        # Determine merged status: blocked > in_progress > completed
        statuses = [t.status for t in similar_tasks]
        if "blocked" in statuses:
            merged_status = "blocked"
        elif "in_progress" in statuses:
            merged_status = "in_progress"
        else:
            merged_status = "completed"

        # Use the longest/most descriptive title
        best_title = max(similar_tasks, key=lambda t: len(t.title)).title

        # Build merged task
        merged_task = Task(
            task_id=task_a.task_id,
            sessions=all_sessions,
            title=best_title,
            project=task_a.project,
            agent=task_a.agent,
            start_time=min(t.start_time for t in similar_tasks if t.start_time),
            end_time=max(t.end_time for t in similar_tasks if t.end_time),
            status=merged_status,
            files_modified=all_files,
            total_events=len(all_events),
            total_prompts=len([e for e in all_events if e.event_type == "user_prompt"]),
            total_responses=len([e for e in all_events if e.event_type == "assistant_response"]),
        )
        merged.append(merged_task)

    return merged


def _extract_star_text(task: Task) -> str:
    """Extract STAR content as a single text for similarity comparison."""
    parts = []
    if task.situation:
        parts.append(task.situation)
    if task.task_description:
        parts.append(task.task_description)
    parts.extend(task.actions)
    if task.result:
        parts.append(task.result)
    return " ".join(parts)


def _normalize_for_similarity(text: str) -> str:
    """Normalize text for similarity comparison."""
    import re
    text = text.lower()
    # Remove punctuation and extra whitespace
    text = re.sub(r'[\s\n\r\t.,;:!?·，。；：！？、"\'\(\)\[\]\{\}<>\-_/\\|@#$%^&*+=~`]', '', text)
    return text


def _normalize_project_name(project: str | None) -> str | None:
    """Normalize CWD-based project names to comparable short names.

    Claude Code uses CWD slugs like '-media-yhr-2T-ultralytics'.
    Pi uses paths like '/home/yhr-.pi'. Extract the last meaningful component.
    """
    if not project:
        return None
    # Strip leading / and split by -, take plausible repo names
    cleaned = project.lstrip("/").lstrip("-")
    parts = cleaned.split("-")
    # Return last component if it's a recognizable project name (≥3 chars)
    for part in reversed(parts):
        if len(part) >= 3:
            return part.lower()
    return cleaned.lower()


def _star_similarity(a: Task, b: Task) -> float:
    """Compute similarity between two tasks' STAR content, prioritizing Situation.

    Returns 0-1. Higher means the tasks describe the same work.
    The Situation field carries the most weight because it describes the context
    and background — two tasks about the same work will share similar situations.
    """
    score = 0.0

    # Same-project baseline: tasks in the same project get a moderate boost.
    # Normalize CWD-based project names first (e.g. '-media-yhr-2T-ultralytics' → 'ultralytics').
    proj_a = _normalize_project_name(a.project)
    proj_b = _normalize_project_name(b.project)
    if proj_a and proj_b and proj_a == proj_b:
        score += 0.08

    # Fast-path: shared key noun phrases in title (2+ char bigrams).
    # Catches "BDD100K 语义分割 training" vs "BDD100K 语义分割 recovery".
    if a.title and b.title:
        ta = _normalize_for_similarity(a.title)
        tb = _normalize_for_similarity(b.title)
        if ta and tb:
            # Title substring match (normalized, ≥8 chars)
            if min(len(ta), len(tb)) >= 8 and (ta in tb or tb in ta):
                score += 0.35
            else:
                # Shared bigram bonus — rewards tasks sharing key terms
                # like "BDD100K", "语义分割", "训练"
                bigrams_a = set(ta[i:i+2] for i in range(len(ta)-1))
                bigrams_b = set(tb[i:i+2] for i in range(len(tb)-1))
                if bigrams_a and bigrams_b:
                    shared = len(bigrams_a & bigrams_b)
                    total = len(bigrams_a | bigrams_b)
                    bigram_jaccard = shared / total if total > 0 else 0
                    if bigram_jaccard > 0.15:
                        score += bigram_jaccard * 0.20

    # Primary: Situation similarity (highest weight)
    if a.situation and b.situation:
        sa = _normalize_for_similarity(a.situation)
        sb = _normalize_for_similarity(b.situation)
        if sa and sb:
            # Exact or substring match
            if sa == sb or sa in sb or sb in sa:
                score += 0.5
            else:
                # 4-gram Jaccard in situation
                wa = set(sa[i:i+4] for i in range(0, len(sa)-3))
                wb = set(sb[i:i+4] for i in range(0, len(sb)-3))
                if wa and wb:
                    sit_jaccard = len(wa & wb) / len(wa | wb)
                    score += sit_jaccard * 0.5

    # Secondary: Task description similarity
    if a.task_description and b.task_description:
        ta = _normalize_for_similarity(a.task_description)
        tb = _normalize_for_similarity(b.task_description)
        if ta and tb:
            if ta == tb or ta in tb or tb in ta:
                score += 0.3
            else:
                wa = set(ta[i:i+3] for i in range(0, len(ta)-2))
                wb = set(tb[i:i+3] for i in range(0, len(tb)-2))
                if wa and wb:
                    score += (len(wa & wb) / len(wa | wb)) * 0.3

    # Tertiary: Result similarity (late-stage tasks share results)
    if a.result and b.result:
        ra = _normalize_for_similarity(a.result)
        rb = _normalize_for_similarity(b.result)
        if ra and rb:
            if ra == rb or ra in rb or rb in ra:
                score += 0.2
            else:
                wa = set(ra[i:i+4] for i in range(0, len(ra)-3))
                wb = set(rb[i:i+4] for i in range(0, len(rb)-3))
                if wa and wb:
                    score += (len(wa & wb) / len(wa | wb)) * 0.2

    return min(1.0, score)


_LLM_MERGE_PROMPT = """You are judging whether two work tasks are the same task, possibly split across different conversation sessions.

Task A:
- Situation: {situation_a}
- Task: {task_a}
- Actions: {actions_a}
- Result: {result_a}

Task B:
- Situation: {situation_b}
- Task: {task_b}
- Actions: {actions_b}
- Result: {result_b}

Are these the SAME task (same conversation split across sessions, or different stages of the same work)?
Answer ONLY "yes" or "no".

Rules:
- "yes" if they describe the same work, even if one is earlier/later stage
- "yes" if they have the same goal and context (e.g. both about designing the same system)
- "yes" if they share the same project/topic and appear to be continuations of each other
- "no" if they are completely unrelated work (e.g. one about bug fix, one about feature design)
- "no" if they are about different projects or different topics

When in doubt, answer "yes" — merging is safer than splitting for weekly reports. Two sessions about the same project and similar work are better merged than kept separate."""


def _llm_should_merge(task_a: Task, task_b: Task) -> bool:
    """Use LLM to judge if two tasks are the same.

    Returns True if LLM says they are the same task.
    """
    try:
        import anthropic
        import os
    except ImportError:
        return False

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False

    client = anthropic.Anthropic(api_key=api_key)

    prompt = _LLM_MERGE_PROMPT.format(
        situation_a=task_a.situation[:300] if task_a.situation else "(none)",
        task_a=task_a.task_description[:200] if task_a.task_description else "(none)",
        actions_a="; ".join(task_a.actions[:5]) if task_a.actions else "(none)",
        result_a=task_a.result[:200] if task_a.result else "(none)",
        situation_b=task_b.situation[:300] if task_b.situation else "(none)",
        task_b=task_b.task_description[:200] if task_b.task_description else "(none)",
        actions_b="; ".join(task_b.actions[:5]) if task_b.actions else "(none)",
        result_b=task_b.result[:200] if task_b.result else "(none)",
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=10,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text.strip().lower() if response.content else ""
        return content.startswith("yes")
    except Exception:
        return False


def merge_by_star_similarity(
    tasks: list[Task], rule_threshold: float = 0.1, quiet: bool = False
) -> list[Task]:
    """Merge tasks using two-stage similarity: rule-based pre-filter + LLM confirmation.

    Stage 1: Rule-based similarity >= rule_threshold → candidate pair
    Stage 2: LLM confirms whether candidates are truly the same task

    This should be called AFTER build_star_for_task() has populated STAR fields.
    """
    if not tasks:
        return tasks

    # Stage 1: Find candidate pairs with rule-based similarity
    # Relaxed filters: LLM judgment has highest priority.
    # We only filter out obviously unrelated pairs (different agent + no similarity).
    candidates: list[tuple[int, int, float]] = []
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            # Soft time filter: 7 days (work records rarely span longer)
            if tasks[i].start_time and tasks[j].start_time:
                time_diff = abs((tasks[i].start_time - tasks[j].start_time).total_seconds())
                if time_diff > 604800:  # 7 days
                    continue

            sim = _star_similarity(tasks[i], tasks[j])
            if sim >= rule_threshold:
                candidates.append((i, j, sim))

    if not quiet:
        print(f"  Rule-based candidates: {len(candidates)} pairs")

    HIGH_SIM_THRESHOLD = 0.9  # auto-merge without LLM (near-identical tasks only)

    # Stage 2: LLM confirmation for candidates
    # LLM judgment overrides all other rules. If LLM says same task, merge regardless
    # of project, agent, status, or /clear boundaries.
    # Only HIGH_SIM_THRESHOLD bypasses LLM — same-project alone is NOT enough to
    # auto-merge (would swallow distinct work sharing a repo, per adversarial review).
    llm_merge_pairs: set[tuple[int, int]] = set()
    auto_merged = 0
    for idx, (i, j, sim) in enumerate(candidates):
        if sim >= HIGH_SIM_THRESHOLD:
            llm_merge_pairs.add((i, j))
            auto_merged += 1
            if not quiet:
                print(f"    Auto [{idx+1}/{len(candidates)}]: {tasks[i].title[:40]}... (sim={sim:.2f}, high-sim) → MERGE")
            continue
        if not quiet:
            print(f"    LLM check [{idx+1}/{len(candidates)}]: {tasks[i].title[:40]}... vs {tasks[j].title[:40]}... (sim={sim:.2f})")
        if _llm_should_merge(tasks[i], tasks[j]):
            llm_merge_pairs.add((i, j))
            if not quiet:
                print(f"      → YES, merge")
        else:
            if not quiet:
                print(f"      → NO, keep separate")

    if auto_merged:
        if not quiet:
            print(f"  Auto-merged {auto_merged} high-similarity pairs")

    if not llm_merge_pairs:
        return tasks

    if not quiet:
        print(f"  LLM confirmed merges: {len(llm_merge_pairs)} pairs")

    # Stage 3: Union-Find to build merge groups
    parent = list(range(len(tasks)))

    def find(x: int) -> int:
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i, j in llm_merge_pairs:
        union(i, j)

    groups: dict[int, list[int]] = {}
    for idx in range(len(tasks)):
        root = find(idx)
        if root not in groups:
            groups[root] = []
        groups[root].append(idx)

    # Stage 4: Build merged tasks
    merged: list[Task] = []
    for group_indices in groups.values():
        if len(group_indices) == 1:
            merged.append(tasks[group_indices[0]])
            continue

        similar_tasks = [tasks[i] for i in group_indices]

        all_sessions: list[Session] = []
        all_events: list[Event] = []
        all_files: list[str] = []

        for t in similar_tasks:
            for s in t.sessions:
                if s not in all_sessions:
                    all_sessions.append(s)
            all_events.extend(t.all_events())
            all_files.extend(t.files_modified)

        all_events.sort(key=lambda e: e.timestamp)
        all_files = list(dict.fromkeys(f for f in all_files if f))

        best = max(similar_tasks, key=lambda t: len(t.situation) + len(t.task_description) + len(t.result))
        all_actions = list(dict.fromkeys(a for t in similar_tasks for a in t.actions))

        statuses = [t.status for t in similar_tasks]
        if "blocked" in statuses:
            merged_status = "blocked"
        elif "in_progress" in statuses:
            merged_status = "in_progress"
        else:
            merged_status = "completed"

        merged_task = Task(
            task_id=tasks[group_indices[0]].task_id,
            sessions=all_sessions,
            title=best.title,
            project=tasks[group_indices[0]].project,
            agent=tasks[group_indices[0]].agent,
            start_time=min(t.start_time for t in similar_tasks if t.start_time),
            end_time=max(t.end_time for t in similar_tasks if t.end_time),
            status=merged_status,
            situation=best.situation,
            task_description=best.task_description,
            actions=all_actions[:8],
            result=best.result,
            files_modified=all_files,
            total_events=len(all_events),
            total_prompts=len([e for e in all_events if e.event_type == "user_prompt"]),
            total_responses=len([e for e in all_events if e.event_type == "assistant_response"]),
        )
        merged.append(merged_task)

    return merged


def _extract_task_title(sessions: list[Session], events: list[Event]) -> str:
    """Extract the best title for a task from available sources."""
    # Priority 1: Session title
    for s in sessions:
        if s.title:
            return s.title

    # Priority 2: First user prompt (first sentence)
    for e in events:
        if e.event_type == "user_prompt":
            content = e.content.strip()
            if content:
                # Take first sentence or first 80 chars
                if "。" in content:
                    return content.split("。")[0] + "。"
                if "." in content and len(content) > 100:
                    return content.split(".")[0] + "."
                return content[:80] + ("..." if len(content) > 80 else "")

    # Priority 3: Session ID fallback
    return sessions[0].session_id[:12] if sessions else "unknown"


def _detect_status(task: Task, events: list[Event]) -> str:
    """Detect completion status from events."""
    if not events:
        return "unknown"

    # Check last events for completion signals
    last_events = events[-10:]

    completion_keywords = ["完成", "done", "completed", "fixed", "resolved", "merged", "已修复", "已通过"]
    blocked_keywords = ["失败", "failed", "error", "cannot", "unable", "blocked", "报错", "无法"]

    for event in reversed(last_events):
        content = (event.content or "").lower()
        for kw in completion_keywords:
            if kw in content:
                return "completed"
        for kw in blocked_keywords:
            if kw in content:
                return "blocked"

    # Check if session is still active (last event within 1 hour)
    now = datetime.now()
    last_time = events[-1].timestamp
    if last_time and (now - last_time) < timedelta(hours=1):
        return "in_progress"

    # Default: assume completed for older sessions
    return "completed"


def load_save_conversation_summary(session_id: str) -> Optional[dict]:
    """Load historical runtime recap for a session if available.

    Returns dict with keys: summary, objective, key_decisions, pending_followups
    """
    conv_dir = Path(".agent-state") / "conversations"
    if not conv_dir.exists():
        return None

    for md_file in conv_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8", errors="replace")
        if session_id in content:
            return _parse_conversation_md(content)

    return None


def _parse_conversation_md(content: str) -> dict:
    """Parse a conversation markdown file into structured data."""
    result = {
        "summary": "",
        "objective": "",
        "key_decisions": "",
        "pending_followups": "",
        "known_issues": "",
    }

    current_key = None
    lines_buffer: list[str] = []

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped.startswith("## Conversation Summary"):
            if current_key and lines_buffer:
                result[current_key] = "\n".join(lines_buffer).strip()
            current_key = "summary"
            lines_buffer = []
        elif stripped.startswith("## Current Objective"):
            if current_key and lines_buffer:
                result[current_key] = "\n".join(lines_buffer).strip()
            current_key = "objective"
            lines_buffer = []
        elif stripped.startswith("## Key Decisions"):
            if current_key and lines_buffer:
                result[current_key] = "\n".join(lines_buffer).strip()
            current_key = "key_decisions"
            lines_buffer = []
        elif stripped.startswith("## Pending Follow-Ups"):
            if current_key and lines_buffer:
                result[current_key] = "\n".join(lines_buffer).strip()
            current_key = "pending_followups"
            lines_buffer = []
        elif stripped.startswith("## Known Issues"):
            if current_key and lines_buffer:
                result[current_key] = "\n".join(lines_buffer).strip()
            current_key = "known_issues"
            lines_buffer = []
        elif stripped.startswith("## "):
            # Unknown section - skip
            if current_key and lines_buffer:
                result[current_key] = "\n".join(lines_buffer).strip()
            current_key = None
            lines_buffer = []
        elif current_key and stripped:
            lines_buffer.append(stripped)

    if current_key and lines_buffer:
        result[current_key] = "\n".join(lines_buffer).strip()

    return result
