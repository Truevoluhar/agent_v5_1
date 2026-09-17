# SKILLS.md — Orchestrator Skills

## Skill: Task Decomposition

Create a durable task list from the user request.

Each task should include:

* a stable task key,
* a clear title,
* a precise description,
* a task type,
* a priority,
* dependency keys,
* acceptance criteria,
* the best suggested agent when obvious.

## Skill: Delegation

Choose the next ready task and the best available agent for it.

Delegations must be:

* bounded,
* actionable,
* specific about expected evidence,
* specific about expected artifacts when applicable.

## Skill: Review

When a worker reports back:

* inspect the summary,
* inspect the evidence,
* inspect the artifacts,
* decide whether to accept, rework, cancel, or ask the user,
* create follow-up tasks if new work is needed.

## Skill: Completion

Finish only when the SQLite task board shows no open work and the user goal is satisfied.
