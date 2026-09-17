# Executor Skills

## Execute Validation

Use `task_board(action='current')` or `task_board(action='get')` to inspect
exactly one test or verification task. Inspect the relevant code and artifacts,
run focused checks with `run_shell`, and save any requested output under the
workspace. Include command, exit code, result, and limitations in
`task_board(action='submit')`. Use `task_board(action='block')` when the check
cannot be executed or does not pass.

## Evidence Rules

Treat command output, saved reports, and verified files as evidence. Redact
secrets. Do not rely on nonexistent tools such as `get_tasks`, `load_test`,
`test_endpoint`, or `save_test_result`; the available durable task interface is
`task_board`.
