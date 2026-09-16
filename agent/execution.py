"""Shared control exceptions and execution instructions."""
class RunCancelled(Exception):
    pass


class BudgetExhausted(Exception):
    pass


EXECUTION_POLICY = '''
For large or multi-file tasks, use work_queue to inventory the complete requested
scope before processing it. Keep PLAN.md concise: objective, acceptance criteria,
strategy, and unresolved issues; keep per-item status in the durable queue.
Choose accurate file globs and record excluded/generated/binary files in the plan.
For a ZIP, inspect and safely extract it into its own directory before inventory.
Claim one task with next, read all its chunks until eof, produce its requested
artifact, verify its content, then complete with specific evidence and paths.
Use distinct output paths per source (e.g. docs/<source-path>/README.md).
For complex non-file work, add bounded subtasks with explicit acceptance criteria.
For Markdown or code writes through run_shell, use a quoted heredoc delimiter
(such as <<'EOF') so backticks and dollar signs remain literal. Read back the saved
file to verify its full content, including examples, before marking it complete.
Persist partial findings to workspace files before context fills. Tool transcripts
are recoverable under .agent/tool-results. Never treat a truncated read as a full
file inspection. Resume running work after interruptions; do not redo completed
items. Mark failures with reasons, diagnose them, and refresh only when appropriate.
Before finishing, verify queue coverage and artifacts and run relevant validation.
Existence and hashes prove coverage, not semantic correctness: review the results.
Never claim unprocessed work is complete. Report limitations and remaining work.
'''


from contextlib import contextmanager


@contextmanager
def workspace_lock(workspace):
    """Fail fast on concurrent writers; the OS releases the lock after a crash."""
    from agent.work_queue import workspace_file
    path = workspace_file(workspace, '.agent/execution.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        import os
        if os.name == 'nt':
            import msvcrt
            stream.write(b'0')
            stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError('Workspace already has an active run; retry after it finishes') from exc
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError('Workspace already has an active run; retry after it finishes') from exc
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)
