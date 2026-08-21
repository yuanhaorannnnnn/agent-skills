# Accepted Specification Schema

accepted_spec.json is the machine-readable execution boundary. It is an
artifact linked from the Canon task page; runtime .proposal files are not
durable truth by themselves.

Required fields:

    {
      "schema_version": 1,
      "task_id": "example-task",
      "spec_version": 1,
      "state": "accepted",
      "artifact_mode": "delivery",
      "scope": ["skills/example/**"],
      "constraints": ["preserve existing CLI defaults"],
      "acceptance": ["execution handoff contains no raw transcript"],
      "non_goals": ["no new skill framework"],
      "approved_dependencies": [],
      "artifacts": [
        {
          "path": "/absolute/path/to/goal.md",
          "kind": "runtime-brief",
          "purpose": "execution input"
        }
      ],
      "spec_hash": "<sha256 of all fields except spec_hash>"
    }

`artifact_mode` is one of `delivery`, `audit`, or `knowledge`. It is optional
for legacy specifications, but any delivery goal or delivery gate must require
it and must reject a different mode.

The hash is canonical JSON with sorted keys and compact separators. A consumer
must reject missing, malformed, or mismatched hashes. Rejected proposals stay
in audit-only session history and are not part of this artifact.
