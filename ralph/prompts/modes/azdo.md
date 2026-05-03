# Mode: Azure DevOps

Tasks are managed as Azure DevOps work items.

You are working on work item {{workitem}}.

## Tools

Use the `cli-anything-azdo` CLI tool to interact with Azure DevOps.
Run `cli-anything-azdo --help` and `cli-anything-azdo [subcommand] --help` to learn usage.

If after retrying you still cannot access Azure DevOps (authentication failure, server unavailable, or the item does not exist), output `<status>ERROR: Cannot access Azure DevOps</status>` and exit immediately.

## Setup

1. Fetch work item {{workitem}} — read its title, description, and acceptance criteria. This is your plan.
2. Read all comments on {{workitem}} — these contain progress notes from previous iterations.
3. Fetch the child work items of {{workitem}} — these are your tasks.

## Reading Tasks

The child work items of {{workitem}} are your tasks. Review their titles, descriptions, and acceptance criteria.

## Updating Task State

- To mark a task as in progress: set the child item's state to "In Progress" (or "Doing").
- To mark a task as complete: set the child item's state to "Done" (or "Resolved").
  - ONLY do this if ALL success criteria are met.

## Creating Tasks

To create a new task, create a child work item under {{workitem}} using the CLI:

```bash
cli-anything-azdo workitem create --parent {{workitem}} --title "<title>" --type Task
```

- Set the title to a clear, actionable description.
- Add acceptance criteria in the description.
- For bugs or defects found during review, use type `Bug` instead of `Task`.

## Recording Progress

Add a comment to the parent work item {{workitem}} with a progress update.
Comments must be well-structured markdown for readability:

- Start with a `[ralph/{{agent}}]` attribution prefix.
- Use a brief heading or bold summary line stating the outcome.
- Use bullet points for individual items (files changed, criteria met, issues found).
- Separate logical sections (what was done, issues, remaining work) clearly.
- Keep it concise — no filler text or verbose explanations.
- Use code formatting (backticks) for file names, commands, and identifiers.

Example:

```markdown
[ralph/{{agent}}]

**Completed: Add user validation endpoint**

- Created `src/Validators/UserValidator.cs` with email and name rules
- Added unit tests in `tests/UserValidatorTests.cs` (6 passing)
- Committed as `feat(AB#12345): add user validation endpoint`

**Remaining:** 2 of 4 tasks complete
```

If unable to update Azure DevOps on completion, output:
`<status>ERROR: Cannot update Azure DevOps for {{workitem}}</status>`

## Committing Work

When committing work, include {{workitem}} in the conventional commit message as the backlog item reference.
Prefix the commit message body with `[ralph/{{agent}}]` for attribution.
