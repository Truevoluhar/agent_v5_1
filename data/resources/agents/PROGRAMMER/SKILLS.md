# SKILLS.md — Programmer Skills

## Skill: Inspect Codebase

Read relevant files before making changes.

Look for:

* existing structure
* naming conventions
* similar implementations
* dependencies
* configuration
* tests

Do not edit until you understand the area being changed.

## Skill: Implement Feature

Add new functionality using the existing project style.

A good implementation should be:

* simple
* focused
* readable
* compatible with existing code
* easy to test

Avoid broad rewrites unless required.

## Skill: Fix Bug

Reproduce or understand the bug first.

Then:

* identify the likely cause
* make the smallest safe fix
* preserve existing behavior
* add or update tests if possible
* explain the cause and fix

## Skill: Refactor Code

Improve structure without changing behavior.

Use refactoring only when it helps the task.

Good refactors may include:

* removing duplication
* simplifying logic
* improving names
* extracting small functions
* isolating responsibilities

Do not refactor unrelated code.

## Skill: Edit Files Safely

Use file editing tools carefully.

Before writing:

* read the file
* know exactly what should change
* avoid overwriting unrelated content

After writing:

* inspect the result
* check formatting
* review the diff

## Skill: Run Checks

Run relevant checks when available.

Examples:

* unit tests
* linting
* type checking
* build commands
* simple smoke tests

If checks cannot be run, explain why.

## Skill: Report Result

Finish with a concise implementation report.

Mention:

* changed files
* main changes
* checks run
* failures or limitations
* suggested next step, if useful

## Skill: Build Draw.io Diagrams

When the request is to create or modify a draw.io artifact:

1. Call `read_drawio_reference` to load rules from `resources/file_resources/xml-reference.md`.
2. Produce full draw.io XML (not Mermaid, not SVG).
3. Call `upsert_drawio_diagram` with:
	- `action="create"` for new files,
	- `action="update"` for existing files,
	- `action="validate"` to validate an existing diagram without rewriting.
4. If validation fails, fix XML and call `upsert_drawio_diagram` again.

Always satisfy enforced constraints: well-formed XML, unique ids, no XML comments, required edge `mxGeometry`, no manual waypoint arrays, and `html=1` when labels contain HTML markup.
