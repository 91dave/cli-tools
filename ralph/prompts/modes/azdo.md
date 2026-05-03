# Mode: Azure DevOps

Tasks are managed as Azure DevOps work items.

You are working on work item {{1}}.

## Tools

Use the `cli-anything-azdo` CLI tool to interact with Azure DevOps.
Run `cli-anything-azdo --help` and `cli-anything-azdo [subcommand] --help` to learn usage.

If after retrying you still cannot access Azure DevOps (authentication failure, server unavailable, or the item does not exist), output `<status>ERROR: Cannot access Azure DevOps</status>` and exit immediately.

## Setup

1. Fetch work item {{1}} — read its title, description, and acceptance criteria. This is your plan.
2. Read all comments on {{1}} — these contain progress notes from previous iterations.
3. Fetch the child work items of {{1}} — these are your tasks.

## Reading Tasks

The child work items of {{1}} are your tasks. Review their titles, descriptions, and acceptance criteria.

## Updating Task State

- To mark a task as in progress: set the child item's state to "In Progress" (or "Doing").
- To mark a task as complete: set the child item's state to "Done" (or "Resolved").
  - ONLY do this if ALL success criteria are met.
- To create a new task: create a new child work item under {{1}}.

## Recording Progress

Add a comment to the parent work item {{1}} with a progress update:
- Prefix the comment with "[ralph]" for attribution.
- Summarise what was done, any issues encountered, and what remains.

If unable to update Azure DevOps on completion, output:
`<status>ERROR: Cannot update Azure DevOps for {{1}}</status>`

## Committing Work

Make a git commit for completed work. Include {{1}} in the conventional commit message as the backlog item reference.
