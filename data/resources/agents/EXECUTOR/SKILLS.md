# Executor Skills

## Execute Validation

Use `work_queue(action='next')` to obtain exactly one test or verification task.
Inspect the relevant code and plan, run focused checks with `run_shell`, and save
any requested output under the workspace. Include command, exit code, result, and
limitations in `work_queue(action='complete')`. Use `fail` when the check cannot
be executed or does not pass.

## Evidence Rules

Treat command output, saved reports, and verified files as evidence. Redact
secrets. Do not rely on nonexistent tools such as `get_tasks`, `load_test`,
`test_endpoint`, or `save_test_result`; the available durable task interface is
`work_queue`.
