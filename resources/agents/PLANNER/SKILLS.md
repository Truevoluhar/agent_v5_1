# PLANNER Agent Skills

## `inspect_project`

Inspect the workspace before planning or validation.

Check relevant:

* source files,
* documentation,
* manifests and dependencies,
* build and test scripts,
* configuration,
* version-control changes,
* existing `PLAN.md`,
* generated artifacts.

Do not modify files during inspection.

## `extract_requirements`

Convert the request into traceable requirements.

Each requirement should include:

* ID such as `REQ-001`,
* description,
* priority: `MUST`, `SHOULD`, or `COULD`,
* acceptance criteria,
* current status,
* linked plan steps.

## `create_or_update_plan`

Create or update `PLAN.md`.

The plan must include:

* objective and scope,
* assumptions,
* requirements,
* implementation approach,
* execution phases,
* observable steps,
* dependencies,
* risks and blockers,
* validation procedures,
* evidence,
* final acceptance checklist.

Preserve existing IDs and execution history.

## `decompose_work`

Break work into small, independently verifiable steps.

Each step must:

* have one main objective,
* produce an observable result,
* identify dependencies,
* define expected artifacts,
* include acceptance criteria,
* include a validation procedure.

Avoid large or vague steps.

## `track_status`

Maintain execution and validation status separately.

A step is fully complete only when:

* execution is `DONE`,
* validation is `PASSED` or `NOT_REQUIRED`.

Record the reason for blocked, failed, skipped, or cancelled work.

## `validate_artifacts`

Inspect files and outputs created by execution agents.

Check:

* correct path,
* non-empty content,
* required structure,
* valid syntax or schema,
* consistency with requirements,
* absence of unfinished placeholders.

## `validate_code`

When applicable, inspect changes and run:

* formatting checks,
* linting,
* type checking,
* unit tests,
* integration tests,
* build commands,
* runtime checks.

Record commands, results, and exit codes.

## `validate_plan_execution`

Compare the current project against every active plan step.

Identify:

* validated steps,
* implemented but unvalidated steps,
* failed steps,
* blocked steps,
* missing artifacts,
* unmet acceptance criteria,
* unplanned changes.

Update `PLAN.md` after validation.

## `collect_evidence`

Record objective proof such as:

* command output,
* exit code,
* test report,
* file path,
* diff,
* API response,
* log,
* screenshot,
* deployment URL.

Never invent evidence. Redact secrets.

## `manage_blockers_and_deviations`

For blockers, record:

* affected step,
* cause,
* impact,
* required resolution,
* status.

For deviations, record:

* planned approach,
* actual approach,
* reason,
* risk,
* remediation or approval.

Critical unresolved issues block completion.

## `create_remediation`

When validation fails, create a new step that includes:

* failure reference,
* corrective actions,
* acceptance criteria,
* validation procedure,
* dependency links.

Do not erase or hide the original failure.

## `close_plan`

Before closure, confirm:

* mandatory requirements are satisfied,
* required artifacts exist,
* validations pass,
* tests and runtime checks pass,
* critical blockers are resolved,
* limitations are documented.

Set the final result to:

* `COMPLETE`,
* `COMPLETE_WITH_LIMITATIONS`,
* or `INCOMPLETE`.

Always save the final state in `PLAN.md`.
