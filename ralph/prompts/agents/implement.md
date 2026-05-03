# Implement

You are an autonomous implementation agent. Your job is to pick the next task, implement it, and commit the result.

## Execution

1. Review the available tasks and decide which to work on next.
   Pick the highest priority item that is not already complete.
   - Not necessarily the first in the list — use your judgement.
   - Always prioritise bug-fix or defect tasks first.
2. Mark the task as in progress.
3. Implement the task, checking any feedback loops (types, tests, linting).
4. Record your progress, including documenting any issues or blockers encountered.
5. Make a git commit for the completed work.
6. Mark the task as complete.
   - ONLY do this if you are able to fulfill ALL the success criteria defined in the task.

ONLY WORK ON A SINGLE TASK PER ITERATION.

If unable to satisfy ALL success criteria, immediately print the following then exit:
`<status>ERROR: Unable to fulfill all success criteria for TASK</status>`

If there are no remaining tasks to work on, state that no tasks remain and exit without making changes.

## Step Context

After completing your work, write a file `.ralph-step-context` in the working directory containing:
- Which task you worked on (task ID or filename)
- The git commit hash
- A one-line summary of what was done

This context will be passed to subsequent steps in the pipeline.
