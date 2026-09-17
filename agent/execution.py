"""Shared control exceptions and execution instructions."""
class RunCancelled(Exception):
    pass


class BudgetExhausted(Exception):
    pass


EXECUTION_POLICY = '''
Use task_board as the durable source of truth for delegated work. Inspect the
current delegated task before making changes, keep the work scoped to that task,
and submit evidence back through task_board when the task is complete.
Before using run_shell, ensure a delegated task is already in progress. A shell
command without a running task is rejected. Finish or block the current task
before reporting progress so the next agent can resume from the durable ledger.
For Markdown or code writes through run_shell, use a quoted heredoc delimiter
(such as <<'EOF') so backticks and dollar signs remain literal. Read back the saved
file to verify its full content, including examples, before marking it complete.
Persist partial findings to workspace files before context fills. Tool transcripts
are recoverable under .agent/tool-results. Never treat a truncated read as a full
file inspection. Resume running work after interruptions; do not redo completed
items. Mark blockers honestly with reasons and concrete follow-up suggestions.
Before finishing, verify validated artifacts and run relevant checks when possible.
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
