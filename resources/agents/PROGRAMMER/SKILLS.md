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
