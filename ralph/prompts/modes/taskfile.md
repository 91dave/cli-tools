# Mode: Task Files

Tasks are managed as markdown files in the project directory.

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
- To create a new task: create a new `task-*.md` file with a description and success criteria.

## Recording Progress

Append to `progress.md` with a summary of what was done, any issues, and what remains.

## Committing Work

Make a git commit for completed work. Use conventional commit format.

## Context Files

@{{1}}/PLAN.md @{{1}}/progress.md
