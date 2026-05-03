# Mode: Task Files

Tasks are managed as markdown files in the project directory: `{{project}}`

## Project Structure

- `PLAN.md` — The overall plan and goals. Read this first.
- `progress.md` — Append-only progress log. Add an entry after each action.
- `task-*.md` — Individual task files. Each defines a unit of work with success criteria.

## Reading Tasks

Review all `task-*.md` files in the project directory. Each file contains:
- A description of the work
- Success criteria that must ALL be met

## Updating Task State

- To mark a task as in progress: update the task file with a status indicator.
- To mark a task as complete: update the task file with a completion indicator.

## Creating Tasks

To create a new task, create a file `task-<short-name>.md` in the project directory with:

```markdown
# Task: <title>

Status: pending
Priority: <high|medium|low>

## Description

<What needs to be done and why>

## Success Criteria

- <Criterion 1>
- <Criterion 2>
```

- Use a short, descriptive kebab-case name (e.g. `task-fix-null-check.md`).
- Set priority to `high` for bugs and defects, `medium` for most work, `low` for nice-to-haves.
- Success criteria must be specific and verifiable.

## Recording Progress

Append to `progress.md` with a summary of what was done, any issues, and what remains.

## Committing Work

Make a git commit for completed work. Use conventional commit format.
Prefix the commit message body with `[ralph/{{agent}}]` for attribution.
