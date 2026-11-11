---
title: Software Release and Operations Loop
description: Explicit release, merge, deployment, operational observation, or incident authority.
kind: loop
scope: shared
loop_status: active
updated: {{DATE}}
---
# Software Release and Operations Loop

## Purpose and entry

Explicit release, merge, deployment, operational observation, or incident authority. Read the existing project context and the current task checkpoint. A missing material criterion returns that specific gap to planning; ordinary implementation choices stay within execution.

## Primary hat

[[Agents/hats/cto]]. A hat does not require a separate agent. Independent review requires a distinct reviewer when warranted; renaming the author's role is not independence.

## Iteration and feedback

Confirm the actual target, approved revision, required checks, environment access, and recovery plan. Apply the authorized release through normal tooling. Observe the changed behavior in that environment. Return application defects to execution; distinguish infrastructure and permission blockers. Iterate on acceptance failures within scope. After two failed repairs of one problem, change the approach under [[Agents/rules/task-completion]].

## Done and stopping points

The authorized release or observation result with revision, environment evidence, unresolved risk, and next owner. Stop at that boundary, report dependent blockers precisely, and continue independent authorized work. Reading this definition does not start another loop, invoke an agent, grant deployment authority, or schedule work.

Procedure: [[Agents/rules/software-development/release-operations]]. Up: [[Agents/loops/INDEX]].
