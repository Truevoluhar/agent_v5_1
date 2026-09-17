# Large-task execution

The runtime now uses a SQLite task board instead of `PLAN.md`.

## Execution contract

The orchestrator creates durable tasks in `.agent/tasks/` for each session. Each
task stores:

* a stable task key,
* title and description,
* task type,
* priority,
* dependency keys,
* suggested and assigned agents,
* worker report fields,
* validation notes,
* artifact hashes for later verification.

The workflow is:

1. The orchestrator decomposes the user request into concrete tasks.
2. Ready tasks are delegated to the best available agent.
3. The worker inspects its current task through `task_board`.
4. The worker does the work, saves artifacts, and reports with `task_board(action="submit")`, or records a blocker with `task_board(action="block")`.
5. The orchestrator reviews the report, validates it, and either accepts it, returns it for rework, cancels it, or creates follow-up tasks.
6. `task_board(action="verify")` and final runner verification ensure validated artifacts still exist before completion.

`run_shell` is allowed only while a task is already in progress.

## Memory and recovery

Session history still lives in SQLite, and semantic memory uses Chroma with
local deterministic embeddings so retrieval works without downloading external
models. The runner records planning, delegation, worker reports, and validation
results back into session history so agents can recover where work was left off.

Tool transcripts remain under `.agent/tool-results/`. Oversized intermediate
history is compacted into durable checkpoints that reference the task board and
saved tool outputs instead of relying on a single long chat context.
