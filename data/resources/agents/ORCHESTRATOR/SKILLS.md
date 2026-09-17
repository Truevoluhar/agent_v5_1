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

For archives or very large code/document collections:

* create an extraction/inspection task first,
* then create an inventory task that seeds one file task per extracted file,
* avoid asking a worker to handle hundreds of files inside one delegation.

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
