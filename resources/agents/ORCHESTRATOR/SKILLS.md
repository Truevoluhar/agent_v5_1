# SKILLS.md — Orchestrator Skills

## Skill: Decide Next Action

Inspect the user goal, current plan, completed steps, artifacts, and latest results. Choose exactly one next action that moves the task toward completion.

Use `finish` only when the goal is complete.

## Skill: Create Plan

Create a plan when the task requires multiple steps.

A good plan should contain:

* step id
* title
* assigned agent
* status
* short description

Use statuses:

* `pending`
* `in_progress`
* `completed`
* `failed`
* `skipped`

Keep plans practical and short.

## Skill: Update Plan

Update the plan whenever work is completed, fails, becomes unnecessary, or new steps are discovered.

Do not recreate the entire plan unless necessary. Prefer targeted updates.

## Skill: Delegate To Agent

Delegate specialist work to the best agent.

Examples:

* Use `planner` for analysis, test design, endpoint extraction, and test case creation.
* Use `executor` for running saved tests and collecting results.
* Use `verifier` for reviewing failures, checking correctness, and deciding whether issues are real bugs or bad tests.

Delegated tasks must be specific and include all needed context.

## Skill: Call Tool

Call tools when direct runtime action is needed.

Examples:

* read a file
* write a file
* list files
* fetch a webservice definition
* run a test
* save an artifact

Never call unsafe tools without permission.

## Skill: Ask User

Ask the user only when required information is missing and the task cannot safely continue.

Ask one clear question.

## Skill: Finish

Finish with a concise summary.

Mention:

* what was completed
* important artifacts
* important results
* failures or limitations, if any
