# Large-task execution

The runtime now separates durable task coverage from model conversation history.
This addresses lost file coverage and context growth; it does not guarantee that
any model can solve every task, or establish parity with other agent products.

## Execution contract

For exhaustive file work, the agent inventories the requested directory with
`work_queue` before processing files. Inventory stores source paths and SHA-256
hashes in a session-specific SQLite database under `.agent/work/`. Repeating an
inventory does not duplicate existing sources. No file bodies enter chat during
inventory. Symlinks and `.agent`, `.git`, `node_modules`, `venv`, and `__pycache__`
paths are excluded; the agent must document exclusions and select the correct
root/glob. The inventory is a snapshot: newly added files require another inventory.

The workflow is:

1. Record the objective, scope, acceptance criteria, and exclusions in `PLAN.md`.
2. Call `work_queue` with `action="inventory"`, a root and glob, and the per-file
   instruction in `text`. Use `add` for general subtasks.
3. Call `next` to resume an interrupted task or claim a pending task.
4. For file tasks, call `read` until `eof` is true. Reads use bounded UTF-8 chunks
   and persist their byte offsets. Non-UTF-8 files need a separately planned
   conversion/inspection approach; a decoding failure does not advance the cursor.
5. Write a distinct artifact for each source, such as
   `docs/<original-source-path>/README.md`. Persist intermediate notes for large
   files, including relationships to other files as needed.
6. Verify the result and call `complete` with evidence in `text` and workspace
   artifact paths in `artifacts`. File tasks require a full read of the unchanged
   source and at least one nonempty artifact. For general tasks, record relevant
   tests/review evidence; artifact paths are optional.
7. Call `verify` before finishing. The runner independently repeats verification
   and rejects completion while unfinished tasks or changed/missing outputs remain.

The tool requires all schema fields; unused fields are `task_id=0`,
`text=""`, `root=""`, `pattern=""`, and `artifacts=[]`.
Use `fail` to record a reason, with up to three claim attempts. Use `refresh`
after diagnosing a failure or changing a source; it resets the item and its read
position. Completed artifacts are immutable for verification purposes: intentional
edits require refreshing and re-verifying the corresponding task.

## Context, continuation, and recovery

Worker instructions retain the active plan. Each tool result is archived under
`.agent/tool-results/`; oversized results point to their full disk copy. When
serialized continuation history exceeds the configured character budget, the
worker archives the transcript and starts a fresh request with the task directive,
queue state, and recent results. It does this at a completed tool-round boundary,
so it never sends orphaned function outputs. Recovery may require rereading
archived results and saved notes. This is a deterministic checkpoint, not an
LLM-generated semantic summary or exact token accounting.

`max_worker_iterations` controls batch size (default 100). Exhausting a worker
batch yields to the orchestrator; it does not end the whole run. `max_steps`
controls the total orchestrator budget. Exhausting that budget produces a failed,
resumable run rather than a false completion. To continue, submit a new run using
**the same session ID and workspace**, with a prompt such as “Continue the
unfinished work.” The original objective and queue survive. Use a new session for
an independent objective, particularly when processing the same sources again.
There is no automatic service restart/requeue after a process crash.

The runtime holds an OS workspace lock for each run so concurrent runs cannot
mutate its plan/queue/artifacts. Contending runs fail with an explicit retry
message; different workspaces can run independently. Background processes can
outlive a run and are not governed by this lock.

Shell commands honor `cwd`, write full output to `.agent/shell/`, and return
bounded previews. Foreground commands have a timeout (1–3600 seconds) and support
cancellation, including their process group on POSIX. Cancellation also interrupts
waiting for user input and is checked between model/tool calls. An in-flight model
HTTP request is still subject to the SDK's own timeout and retry behavior.

## Verification and remaining limits

Run `python -m pytest -q tests` in an environment with project dependencies.
`tests/test_work_queue.py` includes a deterministic 1,000-source coverage test:
exact inventory, full reads, unique outputs, reopening midway, and detecting a
removed artifact. Runtime tests cover premature completion, batch yielding,
context archival, preserved plan instructions, cancellation, and shell output.

These tests establish bookkeeping and execution behavior. They do **not** measure
README quality or prove that the model understood a file. Hashes and read offsets
cannot establish semantic correctness, and the runtime cannot infer exhaustive
scope if the model neglects to inventory it or chooses the wrong glob. Real model
evaluation should compare expected source/output coverage, factual accuracy,
cross-file relationships, test results, latency, and token cost on representative
10-, 100-, and 1,000-file projects, including interruption/recovery runs.

The next capability work should be driven by those measurements: stronger model
selection, dependency-aware scheduling, specialized validation, token-aware
semantic compaction, and durable service job recovery. Authentication, tool
sandboxing/approval, and multi-host coordination remain separate deployment work.
Disk logs need a retention policy for prolonged use. This release processes one
queue item at a time; it does not add concurrent worker execution.
